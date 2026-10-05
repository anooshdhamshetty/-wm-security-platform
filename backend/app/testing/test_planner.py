"""
Security test planner.

Generates endpoint-specific, deterministic (non-LLM) test cases based on the
endpoint's actual method, parameters, and known auth requirement. Tests are
intentionally SAFE: no payloads that write/delete data, no destructive
fuzzing. This is a basic model's test catalogue, not an exhaustive one -- see
README for how to extend it (e.g. with Schemathesis-generated cases).
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import itertools

from app.analyzers.endpoint_extractor import ExtractedEndpoint

_counter = itertools.count(1)


@dataclass
class PlannedTestCase:
    test_id: str
    category: str
    description: str
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    body: Optional[dict] = None
    expected_behavior: str = ""
    use_auth_token: bool = False


def _next_id(prefix: str) -> str:
    return f"{prefix}-{next(_counter):03d}"


def plan_tests_for_endpoint(ep: ExtractedEndpoint) -> List[PlannedTestCase]:
    tests: List[PlannedTestCase] = []

    # --- Authentication: can the endpoint be reached without credentials? ---
    if ep.requires_auth:
        tests.append(PlannedTestCase(
            test_id=_next_id("AUTH"),
            category="authentication",
            description=f"Access {ep.method} {ep.path} without an Authorization header",
            method=ep.method,
            path=ep.path,
            expected_behavior="401 Unauthorized (endpoint is marked as requiring auth)",
            use_auth_token=False,
        ))
        tests.append(PlannedTestCase(
            test_id=_next_id("AUTH"),
            category="authentication",
            description=f"Access {ep.method} {ep.path} with an invalid/garbage token",
            method=ep.method,
            path=ep.path,
            headers={"Authorization": "Bearer invalid.token.value"},
            expected_behavior="401 Unauthorized",
            use_auth_token=False,
        ))

    # --- Authorization / IDOR: numeric/path-id params with a valid token ---
    id_like_params = [p for p in ep.parameters if p.lower() in ("id", "userid", "user_id", "accountid", "account_id")]
    if id_like_params and ep.requires_auth:
        tests.append(PlannedTestCase(
            test_id=_next_id("AUTHZ"),
            category="authorization",
            description=f"Access {ep.method} {ep.path} for an object/user ID belonging to a different "
                        f"authenticated test account (IDOR check)",
            method=ep.method,
            path=ep.path,
            expected_behavior="403 Forbidden or scoped to the authenticated user's own resources",
            use_auth_token=True,
        ))

    # --- Input validation: inject a boundary/malformed value into each query param ---
    for param in ep.parameters[:3]:
        tests.append(PlannedTestCase(
            test_id=_next_id("INPUT"),
            category="input_validation",
            description=f"Submit an oversized/malformed value for parameter '{param}' on {ep.method} {ep.path}",
            method=ep.method,
            path=ep.path,
            query_params={param: "A" * 5000},
            expected_behavior="4xx with a controlled validation error, not a 500 stack trace",
            use_auth_token=bool(ep.requires_auth),
        ))
        tests.append(PlannedTestCase(
            test_id=_next_id("INPUT"),
            category="input_validation",
            description=f"Submit a non-destructive SQL-metacharacter probe for parameter '{param}' "
                        f"(detection only, read-only payload)",
            method=ep.method,
            path=ep.path,
            query_params={param: "test' OR '1'='1"},
            expected_behavior="Input is rejected or safely escaped; no SQL error leaked in response",
            use_auth_token=bool(ep.requires_auth),
        ))

    # --- Method tampering ---
    other_methods = [m for m in ("GET", "POST", "PUT", "DELETE", "OPTIONS") if m != ep.method.upper()]
    tests.append(PlannedTestCase(
        test_id=_next_id("API"),
        category="api_security",
        description=f"Call {ep.path} with method {other_methods[0]} instead of the expected {ep.method}",
        method=other_methods[0],
        path=ep.path,
        expected_behavior="404/405, not an unintended successful action",
        use_auth_token=bool(ep.requires_auth),
    ))

    # --- Security headers / configuration (every endpoint) ---
    tests.append(PlannedTestCase(
        test_id=_next_id("CFG"),
        category="security_configuration",
        description=f"Inspect security-relevant response headers for {ep.method} {ep.path}",
        method=ep.method,
        path=ep.path,
        expected_behavior="Presence of CSP/HSTS/X-Content-Type-Options/X-Frame-Options where applicable; "
                          "no verbose server/framework version banner",
        use_auth_token=bool(ep.requires_auth),
    ))

    return tests


def plan_tests(endpoints: List[ExtractedEndpoint]) -> Dict[str, List[PlannedTestCase]]:
    plan: Dict[str, List[PlannedTestCase]] = {}
    for ep in endpoints:
        key = f"{ep.method}::{ep.path}"
        plan[key] = plan_tests_for_endpoint(ep)
    return plan
