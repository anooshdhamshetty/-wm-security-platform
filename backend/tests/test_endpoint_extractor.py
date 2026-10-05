from app.analyzers.repository_analyzer import RepoFileRef
from app.analyzers.endpoint_extractor import extract_endpoints


def test_extracts_express_routes():
    content = """
const app = require('express')();
app.get('/api/users/:id', function getUser(req, res) {
  res.json({});
});
app.post('/api/users', requireAuth, function createUser(req, res) {});
"""
    f = RepoFileRef(path="server.js", sha="x", size=len(content), category="backend", content=content)
    endpoints = extract_endpoints(f)
    assert any(e.method == "GET" and e.path == "/api/users/:id" for e in endpoints)
    assert any(e.method == "POST" and e.path == "/api/users" for e in endpoints)


def test_extracts_fastapi_routes():
    content = """
@app.get("/api/items/{item_id}")
def read_item(item_id: int):
    return {}

@router.post("/api/items")
def create_item(payload: dict):
    return {}
"""
    f = RepoFileRef(path="main.py", sha="x", size=len(content), category="backend", content=content)
    endpoints = extract_endpoints(f)
    assert any(e.method == "GET" and e.path == "/api/items/{item_id}" for e in endpoints)
    assert any(e.method == "POST" and e.path == "/api/items" for e in endpoints)


def test_detects_auth_hint():
    content = """
@app.get("/api/secret")
@login_required
def secret():
    return {}
"""
    f = RepoFileRef(path="main.py", sha="x", size=len(content), category="backend", content=content)
    endpoints = extract_endpoints(f)
    assert endpoints[0].requires_auth is True
