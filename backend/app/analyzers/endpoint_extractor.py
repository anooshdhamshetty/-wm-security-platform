"""
Endpoint extractor.

This is a deterministic, regex/pattern-based extractor that identifies HTTP
route definitions in common backend frameworks (Express/Node, FastAPI/Flask,
Django REST, Spring). It is intentionally NOT an LLM step -- route discovery
must be reproducible and traceable to an exact file/line.

This is a "basic model" implementation: it covers the common decorator /
router-call patterns per framework. It will not catch dynamically
constructed routes, which is noted as a limitation in the README.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.analyzers.repository_analyzer import RepoFileRef

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}

# Express / Node:  app.get('/path', handler)  router.post("/path", ...)
EXPRESS_PATTERN = re.compile(
    r"""\b(?:app|router)\.(get|post|put|patch|delete|options|head)\s*\(\s*
        ['"`]([^'"`]+)['"`]""",
    re.VERBOSE | re.IGNORECASE,
)

# FastAPI / Flask:  @app.get("/path")  @router.post('/path')
PY_DECORATOR_PATTERN = re.compile(
    r"""@(?:app|router)\.(get|post|put|patch|delete|options|head)\s*\(\s*
        ['"]([^'"]+)['"]""",
    re.VERBOSE | re.IGNORECASE,
)

# Flask alternative: @app.route("/path", methods=["POST"])
FLASK_ROUTE_PATTERN = re.compile(
    r"""@(?:app|bp)\.route\s*\(\s*['"]([^'"]+)['"](?:[^)]*methods\s*=\s*\[([^\]]*)\])?""",
    re.VERBOSE | re.IGNORECASE,
)

# Spring: @GetMapping("/path")  @PostMapping(value="/path")
SPRING_PATTERN = re.compile(
    r"""@(Get|Post|Put|Patch|Delete)Mapping\s*\(\s*(?:value\s*=\s*)?["']([^"']+)["']""",
)

# Cloudflare Workers / Edge functions
EDGE_WORKER_PATTERN = re.compile(
    r"""(?:export\s+default\s+\{\s*(?:async\s+)?fetch|addEventListener\s*\(\s*['"]fetch['"])\s*""",
    re.VERBOSE | re.IGNORECASE,
)

# Vercel Serverless / Next.js Pages API: export default function handler(...)
VERCEL_HANDLER_PATTERN = re.compile(
    r"""export\s+default\s+(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(""",
    re.VERBOSE,
)

# Next.js App Router: export async function GET(...)
NEXTJS_APP_PATTERN = re.compile(
    r"""export\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s*\(""",
    re.VERBOSE,
)

FUNCTION_NAME_PATTERN = re.compile(
    r"""(?:async\s+)?(?:def|function)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("""
)

AUTH_HINTS = re.compile(
    r"(requireAuth|isAuthenticated|@login_required|Depends\(get_current_user\)|authMiddleware|verifyToken|jwt_required|permission_classes|@PreAuthorize)",
    re.IGNORECASE,
)


@dataclass
class ExtractedEndpoint:
    path: str
    method: str
    source_file: str
    source_line: int
    handler_name: Optional[str] = None
    requires_auth: Optional[bool] = None
    parameters: List[str] = field(default_factory=list)
    discovered_via: str = "regex"


def _nearest_function_name(lines: List[str], line_idx: int) -> Optional[str]:
    """Look a few lines below the route declaration for a handler/function name."""
    for i in range(line_idx, min(line_idx + 4, len(lines))):
        m = FUNCTION_NAME_PATTERN.search(lines[i])
        if m:
            return m.group(1)
    return None


def _path_params(path: str) -> List[str]:
    params = re.findall(r"[:{]([A-Za-z_][A-Za-z0-9_]*)\}?", path)
    return params


def _auth_nearby(lines: List[str], line_idx: int, window: int = 6) -> Optional[bool]:
    start = max(0, line_idx - window)
    end = min(len(lines), line_idx + window)
    snippet = "\n".join(lines[start:end])
    if AUTH_HINTS.search(snippet):
        return True
    return None


def extract_endpoints(file_ref: RepoFileRef) -> List[ExtractedEndpoint]:
    if not file_ref.content:
        return []

    lines = file_ref.content.splitlines()
    found: List[ExtractedEndpoint] = []

    for idx, line in enumerate(lines):
        for m in EXPRESS_PATTERN.finditer(line):
            method, path = m.group(1).upper(), m.group(2)
            found.append(ExtractedEndpoint(
                path=path, method=method, source_file=file_ref.path, source_line=idx + 1,
                handler_name=_nearest_function_name(lines, idx),
                requires_auth=_auth_nearby(lines, idx),
                parameters=_path_params(path),
            ))
        for m in PY_DECORATOR_PATTERN.finditer(line):
            method, path = m.group(1).upper(), m.group(2)
            found.append(ExtractedEndpoint(
                path=path, method=method, source_file=file_ref.path, source_line=idx + 1,
                handler_name=_nearest_function_name(lines, idx + 1),
                requires_auth=_auth_nearby(lines, idx),
                parameters=_path_params(path),
            ))
        for m in FLASK_ROUTE_PATTERN.finditer(line):
            path = m.group(1)
            methods_raw = m.group(2)
            methods = ["GET"]
            if methods_raw:
                methods = [x.strip(" '\"").upper() for x in methods_raw.split(",")]
            for method in methods:
                if method.lower() not in HTTP_METHODS:
                    continue
                found.append(ExtractedEndpoint(
                    path=path, method=method, source_file=file_ref.path, source_line=idx + 1,
                    handler_name=_nearest_function_name(lines, idx + 1),
                    requires_auth=_auth_nearby(lines, idx),
                    parameters=_path_params(path),
                ))
        for m in SPRING_PATTERN.finditer(line):
            method, path = m.group(1).upper(), m.group(2)
            found.append(ExtractedEndpoint(
                path=path, method=method, source_file=file_ref.path, source_line=idx + 1,
                handler_name=_nearest_function_name(lines, idx),
                requires_auth=_auth_nearby(lines, idx),
                parameters=_path_params(path),
            ))
        for m in EDGE_WORKER_PATTERN.finditer(line):
            found.append(ExtractedEndpoint(
                path="/*", method="ANY", source_file=file_ref.path, source_line=idx + 1,
                handler_name="fetch",
                requires_auth=_auth_nearby(lines, idx),
                parameters=[],
                discovered_via="edge_worker",
            ))
        for m in VERCEL_HANDLER_PATTERN.finditer(line):
            handler_name = m.group(1)
            # Derive path from filename, e.g. api/foo.ts -> /api/foo
            derived_path = "/" + file_ref.path.rsplit(".", 1)[0]
            if derived_path.endswith("/index") or derived_path.endswith("/route"):
                derived_path = derived_path.rsplit("/", 1)[0] or "/"
            found.append(ExtractedEndpoint(
                path=derived_path, method="ANY", source_file=file_ref.path, source_line=idx + 1,
                handler_name=handler_name,
                requires_auth=_auth_nearby(lines, idx),
                parameters=[],
                discovered_via="vercel_handler",
            ))
        for m in NEXTJS_APP_PATTERN.finditer(line):
            method = m.group(1).upper()
            derived_path = "/" + file_ref.path.rsplit(".", 1)[0]
            if derived_path.endswith("/route") or derived_path.endswith("/index"):
                derived_path = derived_path.rsplit("/", 1)[0] or "/"
            found.append(ExtractedEndpoint(
                path=derived_path, method=method, source_file=file_ref.path, source_line=idx + 1,
                handler_name=method,
                requires_auth=_auth_nearby(lines, idx),
                parameters=[],
                discovered_via="nextjs_app_router",
            ))

    return found


def extract_all(files: List[RepoFileRef]) -> List[ExtractedEndpoint]:
    endpoints: List[ExtractedEndpoint] = []
    for f in files:
        if f.category != "backend":
            continue
        endpoints.extend(extract_endpoints(f))
    # Deduplicate identical (method, path) pairs, keeping the first occurrence
    seen = set()
    deduped = []
    for ep in endpoints:
        key = (ep.method, ep.path)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ep)
    return deduped
