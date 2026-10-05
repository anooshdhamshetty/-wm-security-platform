from app.validation.validator import validate_finding


def test_validated_when_both_agree():
    ai = {"verdict": "potential_finding", "could_be_vulnerability": True, "confidence": "high"}
    assert validate_finding("potential_finding", ai) == "validated"


def test_false_positive_when_llm_disagrees():
    ai = {"verdict": "no_issue", "could_be_vulnerability": False, "confidence": "high"}
    assert validate_finding("potential_finding", ai) == "false_positive"


def test_potential_when_llm_inconclusive():
    ai = {"verdict": "inconclusive", "could_be_vulnerability": None, "confidence": "low"}
    assert validate_finding("potential_finding", ai) == "potential_finding"


def test_pass_result_is_false_positive():
    ai = {"verdict": "no_issue", "could_be_vulnerability": False, "confidence": "high"}
    assert validate_finding("pass", ai) == "false_positive"
