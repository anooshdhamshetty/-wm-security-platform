"""
A tiny intentionally-flawed FastAPI app used ONLY as a safe local demo
target so the testing pipeline can be demonstrated end-to-end without
pointing it at a real/production system.

Run with:  uvicorn tests.mock_target_app:app --port 8080
Then set TARGET_BASE_URL=http://localhost:8080 for an assessment.
"""
from fastapi import FastAPI, Header
from typing import Optional

app = FastAPI(title="Mock Target App (intentionally vulnerable demo)")

FAKE_USERS = {"1": {"name": "alice"}, "2": {"name": "bob"}}


@app.get("/api/public/ping")
def ping():
    return {"status": "ok"}


@app.get("/api/users/{user_id}")
def get_user(user_id: str, authorization: Optional[str] = Header(None)):
    # Intentionally missing an ownership check -> IDOR demo finding
    if user_id in FAKE_USERS:
        return FAKE_USERS[user_id]
    return {"error": "not found"}


@app.get("/api/admin/stats")
def admin_stats(authorization: Optional[str] = Header(None)):
    # Intentionally missing auth enforcement -> authentication demo finding
    return {"total_users": len(FAKE_USERS)}


@app.get("/api/search")
def search(q: str = ""):
    # Deliberately returns a raw error-looking string for a quote character,
    # to demonstrate the input-validation evidence path (NOT a real DB).
    if "'" in q:
        return {"error": "sql syntax error near unexpected token"}
    return {"results": []}
