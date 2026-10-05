from app.ai.analyzer import analyze_evidence


def test_groq_fallback_when_no_key(monkeypatch):
    """With no GROQ_API_KEY set, analyze_evidence must degrade gracefully to
    an 'inconclusive' result instead of raising or silently skipping."""
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()

    result = analyze_evidence(
        method="GET", path="/api/test", category="authentication",
        description="test", expected_behavior="401", actual_behavior="HTTP 200",
        status_code=200, security_headers={}, body_preview="", code_location=None,
    )
    assert result["verdict"] == "inconclusive"
    assert "GROQ_API_KEY" in result["supporting_evidence"]


def test_anthropic_fallback_when_no_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()

    result = analyze_evidence(
        method="GET", path="/api/test", category="authentication",
        description="test", expected_behavior="401", actual_behavior="HTTP 200",
        status_code=200, security_headers={}, body_preview="", code_location=None,
    )
    assert result["verdict"] == "inconclusive"
    assert "ANTHROPIC_API_KEY" in result["supporting_evidence"]
