from app.scoring.cvss import calculate_base_score, CVSSVector, severity_label, score_finding


def test_known_vector_score():
    # CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H -> 9.8 (well-known reference vector)
    v = CVSSVector(AV="N", AC="L", PR="N", UI="N", S="U", C="H", I="H", A="H")
    score = calculate_base_score(v)
    assert score == 9.8


def test_severity_labels():
    assert severity_label(0.0) == "info"
    assert severity_label(3.9) == "low"
    assert severity_label(6.9) == "medium"
    assert severity_label(8.9) == "high"
    assert severity_label(9.5) == "critical"


def test_score_finding_authentication():
    score, vector, severity = score_finding("authentication", 200, has_auth_bypass=True)
    assert score > 7.0
    assert severity in ("high", "critical")
