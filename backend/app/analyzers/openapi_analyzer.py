"""
OpenAPI analyzer.

Parses an OpenAPI 3.x (JSON or YAML) spec found in the repository and
normalizes it into the same ExtractedEndpoint shape used by the regex-based
extractor, so both sources feed the application mapper consistently.
"""
import json
from typing import List, Optional

import yaml

from app.analyzers.endpoint_extractor import ExtractedEndpoint
from app.analyzers.repository_analyzer import RepoFileRef

OPENAPI_FILENAME_HINTS = ("openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.json")


def find_openapi_files(files: List[RepoFileRef]) -> List[RepoFileRef]:
    return [f for f in files if f.path.lower().split("/")[-1] in OPENAPI_FILENAME_HINTS and f.content]


def _load_spec(file_ref: RepoFileRef) -> Optional[dict]:
    try:
        if file_ref.path.endswith(".json"):
            return json.loads(file_ref.content)
        return yaml.safe_load(file_ref.content)
    except Exception:
        return None


def extract_from_openapi(file_ref: RepoFileRef) -> List[ExtractedEndpoint]:
    spec = _load_spec(file_ref)
    if not spec or "paths" not in spec:
        return []

    global_security = spec.get("security")
    endpoints: List[ExtractedEndpoint] = []

    for path, methods in spec["paths"].items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            if not isinstance(operation, dict):
                continue
            params = []
            for p in operation.get("parameters", []):
                if isinstance(p, dict) and "name" in p:
                    params.append(p["name"])
            security = operation.get("security", global_security)
            requires_auth = bool(security) if security is not None else None

            endpoints.append(ExtractedEndpoint(
                path=path,
                method=method.upper(),
                source_file=file_ref.path,
                source_line=1,
                handler_name=operation.get("operationId"),
                requires_auth=requires_auth,
                parameters=params,
                discovered_via="openapi",
            ))

    return endpoints


def extract_all_openapi(files: List[RepoFileRef]) -> List[ExtractedEndpoint]:
    endpoints = []
    for f in find_openapi_files(files):
        endpoints.extend(extract_from_openapi(f))
    return endpoints
