"""
Runtime test execution using httpx.

Enforces the platform's safety constraints before sending a single request:
  - target host must be in ALLOWED_TARGET_HOSTS
  - only methods/payloads produced by the test planner (no ad-hoc exploit code)
  - per-assessment request cap
  - client-side rate limiting
  - no destructive methods beyond what a test explicitly declares, and the
    planner never declares DELETE/PUT with real mutation payloads
"""
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin

import httpx

from app.config import get_settings
from app.testing.test_planner import PlannedTestCase


class ScopeViolationError(Exception):
    pass


@dataclass
class ExecutionResult:
    test_id: str
    method: str
    path: str
    request: Dict[str, Any]
    response: Dict[str, Any]
    status_code: Optional[int]
    duration_ms: Optional[float]
    result: str  # pass, fail, potential_finding, error
    error: Optional[str] = None


class SafeHttpxRunner:
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        settings = get_settings()
        self.settings = settings
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self._request_count = 0

        if not self.base_url.startswith("http://") and not self.base_url.startswith("https://"):
            self.base_url = "https://" + self.base_url

        host = urlparse(self.base_url).hostname or ""
        if not any(host == allowed or host.endswith("." + allowed) for allowed in settings.ALLOWED_TARGET_HOSTS):
            raise ScopeViolationError(
                f"Target host '{host}' is not in ALLOWED_TARGET_HOSTS ({settings.ALLOWED_TARGET_HOSTS}). "
                f"Refusing to test out-of-scope targets."
            )

        self.client = httpx.Client(timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=False)

    def close(self):
        self.client.close()

    def _rate_limit(self):
        delay = 1.0 / max(self.settings.REQUEST_RATE_LIMIT_PER_SEC, 0.1)
        time.sleep(delay)

    def run(self, test: PlannedTestCase) -> ExecutionResult:
        if self._request_count >= self.settings.MAX_REQUESTS_PER_ASSESSMENT:
            return ExecutionResult(
                test_id=test.test_id, method=test.method, path=test.path,
                request={}, response={}, status_code=None, duration_ms=None,
                result="error", error="MAX_REQUESTS_PER_ASSESSMENT limit reached; test skipped.",
            )

        url = urljoin(self.base_url + "/", test.path.lstrip("/"))
        headers = dict(test.headers)
        if test.use_auth_token and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        request_record = {
            "url": url,
            "method": test.method,
            "headers": {k: v for k, v in headers.items() if k.lower() != "authorization"},
            "query_params": test.query_params,
            "body": test.body,
        }

        self._rate_limit()
        self._request_count += 1
        start = time.perf_counter()
        try:
            resp = self.client.request(
                test.method,
                url,
                headers=headers,
                params=test.query_params or None,
                json=test.body,
            )
        except httpx.RequestError as e:
            return ExecutionResult(
                test_id=test.test_id, method=test.method, path=test.path,
                request=request_record, response={}, status_code=None,
                duration_ms=(time.perf_counter() - start) * 1000,
                result="error", error=str(e),
            )

        duration_ms = (time.perf_counter() - start) * 1000
        body_preview = resp.text[:2000]

        response_record = {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body_preview": body_preview,
        }

        result = self._classify(test, resp, body_preview)

        return ExecutionResult(
            test_id=test.test_id, method=test.method, path=test.path,
            request=request_record, response=response_record,
            status_code=resp.status_code, duration_ms=duration_ms, result=result,
        )

    @staticmethod
    def _classify(test: PlannedTestCase, resp: httpx.Response, body_preview: str) -> str:
        """Deterministic PASS/FAIL/POTENTIAL_FINDING classification.

        This is intentionally conservative: it flags things for the evidence
        engine / LLM analysis layer to review rather than declaring a
        vulnerability outright.
        """
        status = resp.status_code

        if test.category == "authentication":
            if status in (401, 403):
                return "pass"
            if 200 <= status < 300:
                return "potential_finding"
            return "fail"

        if test.category == "authorization":
            if status in (401, 403, 404):
                return "pass"
            if 200 <= status < 300:
                return "potential_finding"
            return "fail"

        if test.category == "input_validation":
            sql_error_markers = ("sql syntax", "sqlstate", "sqlite3.", "psycopg2", "ORA-0", "odbc driver")
            if status == 500 or any(m in body_preview.lower() for m in sql_error_markers):
                return "potential_finding"
            if 400 <= status < 500:
                return "pass"
            return "fail"

        if test.category == "api_security":
            if status in (404, 405):
                return "pass"
            if 200 <= status < 300:
                return "potential_finding"
            return "fail"

        if test.category == "security_configuration":
            # never a hard fail on its own; evidence engine records header presence
            return "pass"

        return "fail"
