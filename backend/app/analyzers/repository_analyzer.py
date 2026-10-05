"""
Repository analyzer.

Uses the GitHub REST API (git trees + contents endpoints) to pull down only
the files that are relevant to a security assessment, without requiring a
local git clone. Relevance is decided by extension/path heuristics so that
large repos don't get fully downloaded.
"""
import base64
import re
import time
import zipfile
import io
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse

import requests

from app.config import get_settings

RELEVANT_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".java", ".rb", ".php",
    ".json", ".yaml", ".yml", ".env.example", ".proto",
}

IGNORED_DIR_PATTERNS = re.compile(
    r"(^|/)(node_modules|dist|build|\.git|coverage|__pycache__|venv|\.venv|vendor|test-?data)(/|$)"
)

CONFIG_FILENAMES = {
    "package.json", "tsconfig.json", "requirements.txt", "pyproject.toml",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml", ".env.example",
    "openapi.yaml", "openapi.json", "swagger.yaml", "swagger.json",
}

BACKEND_HINTS = re.compile(r"(^|/)(api|server|backend|routes?|controllers?|handlers?)(/|$)", re.I)
FRONTEND_HINTS = re.compile(r"(^|/)(src/components|src/pages|src/services|src/utils|src/shared|src/types|src/hooks|src/store|src/constants|src/models|src/shims|src/workers|workers|tests?|frontend|client|ui)(/|$)", re.I)


@dataclass
class RepoFileRef:
    path: str
    sha: str
    size: int
    category: str
    language: Optional[str] = None
    content: Optional[str] = None


@dataclass
class RepositoryAnalysisResult:
    owner: str
    repo: str
    default_branch: str
    files: List[RepoFileRef] = field(default_factory=list)
    truncated: bool = False
    errors: List[str] = field(default_factory=list)


class GitHubAPIError(Exception):
    pass


class RepositoryAnalyzer:
    def __init__(self, token: Optional[str] = None, max_files: int = 150, max_file_bytes: int = 200_000):
        settings = get_settings()
        self.token = token or settings.GITHUB_TOKEN
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        self.session = requests.Session()
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers.update(headers)

    @staticmethod
    def parse_repo_url(repo_url: str):
        """Accepts https://github.com/owner/repo(.git) or owner/repo."""
        repo_url = repo_url.strip()
        if repo_url.startswith("http"):
            parts = urlparse(repo_url).path.strip("/").split("/")
        else:
            parts = repo_url.strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Could not parse GitHub repository from '{repo_url}'")
        owner, repo = parts[0], parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo

    def _get(self, url: str, params: dict = None):
        max_retries = 3
        for attempt in range(max_retries):
            resp = self.session.get(url, params=params, timeout=20)
            
            is_rate_limit = (
                resp.status_code == 429 or
                (resp.status_code == 403 and ("rate limit" in resp.text.lower() or "abuse" in resp.text.lower()))
            )
            
            if is_rate_limit:
                if attempt < max_retries - 1:
                    sleep_time = int(resp.headers.get("Retry-After", (attempt + 1) * 5))
                    time.sleep(sleep_time)
                    continue
                else:
                    if "rate limit" in resp.text.lower() and not self.token:
                        raise GitHubAPIError("GitHub API rate limit exceeded. Provide a GITHUB_TOKEN to raise the limit.")
                    raise GitHubAPIError(f"GitHub API error {resp.status_code} for {url}: {resp.text[:300]}")

            if resp.status_code == 404:
                raise GitHubAPIError(f"GitHub resource not found: {url}")
            if not resp.ok:
                raise GitHubAPIError(f"GitHub API error {resp.status_code} for {url}: {resp.text[:300]}")
            
            return resp.json()

    def _categorize(self, path: str) -> str:
        lower = path.lower()
        name = lower.split("/")[-1]
        if name in CONFIG_FILENAMES or name.startswith(".env"):
            return "config"
        if name == "package-lock.json" or name == "poetry.lock":
            return "dependency"
        if BACKEND_HINTS.search(lower):
            return "backend"
        if FRONTEND_HINTS.search(lower):
            return "frontend"
        if lower.endswith((".tsx", ".jsx")):
            return "frontend"
        if lower.endswith((".ts", ".js", ".py", ".go", ".java", ".rb", ".php")):
            return "backend"
        return "other"

    def _is_relevant(self, path: str) -> bool:
        if IGNORED_DIR_PATTERNS.search(path):
            return False
        name = path.lower().split("/")[-1]
        if name in CONFIG_FILENAMES or name.startswith(".env"):
            return True
        ext = "." + name.split(".")[-1] if "." in name else ""
        return ext in RELEVANT_EXTENSIONS

    def analyze(self, repo_url: str, fetch_content: bool = True) -> RepositoryAnalysisResult:
        owner, repo = self.parse_repo_url(repo_url)
        repo_meta = self._get(f"https://api.github.com/repos/{owner}/{repo}")
        default_branch = repo_meta.get("default_branch", "main")
        size_kb = repo_meta.get("size", 0)

        result = RepositoryAnalysisResult(owner=owner, repo=repo, default_branch=default_branch)

        if size_kb < 300_000 and fetch_content:
            # Download zipball for repos under 100MB to avoid abuse rate limits
            zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{default_branch}"
            resp = self.session.get(zip_url, timeout=30)
            if resp.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                    candidates = []
                    for name in z.namelist():
                        if name.endswith('/'): continue
                        # Strip the root directory added by GitHub zipballs
                        path = "/".join(name.split("/")[1:])
                        if self._is_relevant(path):
                            candidates.append((name, path, z.getinfo(name).file_size))
                    
                    if len(candidates) > self.max_files:
                        candidates.sort(key=lambda i: self._categorize(i[1]) not in ("backend", "config"))
                        candidates = candidates[: self.max_files]
                        result.truncated = True
                    
                    for name, path, size in candidates:
                        ref = RepoFileRef(
                            path=path,
                            sha="", # no sha needed when fetching from zip
                            size=size,
                            category=self._categorize(path),
                        )
                        if size <= self.max_file_bytes:
                            try:
                                ref.content = z.read(name).decode("utf-8", errors="replace")
                            except Exception:
                                ref.content = ""
                        result.files.append(ref)
                return result

        # Fallback to Tree API for large repos or if fetch_content is False
        tree_data = self._get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}",
            params={"recursive": "1"},
        )

        result.truncated = bool(tree_data.get("truncated"))

        candidates = [
            item for item in tree_data.get("tree", [])
            if item.get("type") == "blob" and self._is_relevant(item["path"])
        ]

        if len(candidates) > self.max_files:
            candidates.sort(key=lambda i: self._categorize(i["path"]) not in ("backend", "config"))
            candidates = candidates[: self.max_files]

        for item in candidates:
            ref = RepoFileRef(
                path=item["path"],
                sha=item.get("sha", ""),
                size=item.get("size", 0),
                category=self._categorize(item["path"]),
            )
            if fetch_content and ref.size and ref.size <= self.max_file_bytes:
                try:
                    ref.content = self._fetch_file_content(owner, repo, item["sha"])
                    time.sleep(0.1)  # small delay to prevent abuse limits
                except GitHubAPIError as e:
                    result.errors.append(f"{ref.path}: {e}")
            result.files.append(ref)

        return result

    def _fetch_file_content(self, owner: str, repo: str, blob_sha: str) -> str:
        data = self._get(f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{blob_sha}")
        if data.get("encoding") == "base64":
            try:
                return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            except Exception:
                return ""
        return data.get("content", "")
