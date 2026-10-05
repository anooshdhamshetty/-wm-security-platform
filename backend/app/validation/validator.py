"""
Vulnerability validator.

Combines the deterministic test classification, the structured evidence,
and the LLM's reasoning output to decide a final finding status:

    validated          -> deterministic classifier flagged it AND the LLM
                           agrees it could be a vulnerability with
                           medium/high confidence
    potential_finding   -> only one of the two signals agrees, or LLM is
                           unavailable/inconclusive but the deterministic
                           signal fired
    false_positive      -> deterministic classifier flagged it but the LLM
                           (with medium/high confidence) says it is expected
                           behavior
    inconclusive        -> insufficient evidence either way
"""
from typing import Dict, Any


def validate_finding(deterministic_result: str, ai_analysis: Dict[str, Any]) -> str:
    verdict = ai_analysis.get("verdict")
    confidence = ai_analysis.get("confidence", "low")
    could_be_vuln = ai_analysis.get("could_be_vulnerability")

    if deterministic_result != "potential_finding":
        return "false_positive" if deterministic_result == "pass" else "inconclusive"

    # deterministic_result == "potential_finding" from here on
    if verdict == "inconclusive" or could_be_vuln is None:
        return "potential_finding"

    if could_be_vuln is True and confidence in ("medium", "high"):
        return "validated"

    if could_be_vuln is False and confidence in ("medium", "high"):
        return "false_positive"

    return "potential_finding"
