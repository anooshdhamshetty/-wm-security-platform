"""
Evidence engine.

Converts a raw ExecutionResult into a structured Evidence record, including
a best-effort link back to the source-code location of the endpoint it
tested (from the application map / endpoint table), so findings are never
disconnected from the code that produced them.
"""
from typing import Optional, Dict, Any

SECURITY_HEADER_NAMES = [
    "content-security-policy", "strict-transport-security", "x-content-type-options",
    "x-frame-options", "x-xss-protection", "referrer-policy", "permissions-policy",
    "server", "x-powered-by",
]


def build_evidence(
    test_category: str,
    expected_behavior: str,
    status_code: Optional[int],
    response_headers: Dict[str, Any],
    body_preview: str,
    code_location: Optional[str],
) -> dict:
    present_headers = {
        h: response_headers.get(h) or response_headers.get(h.title())
        for h in SECURITY_HEADER_NAMES
        if response_headers.get(h) or response_headers.get(h.title())
    }

    actual_behavior = f"HTTP {status_code}" if status_code is not None else "No response (network/error)"
    if body_preview:
        actual_behavior += f"; response body (truncated): {body_preview[:300]!r}"

    summary = f"[{test_category}] expected: {expected_behavior} | actual: {actual_behavior}"

    return {
        "summary": summary,
        "expected_behavior": expected_behavior,
        "actual_behavior": actual_behavior,
        "security_headers": present_headers,
        "related_code_location": code_location or "Code location could not be conclusively determined.",
    }
