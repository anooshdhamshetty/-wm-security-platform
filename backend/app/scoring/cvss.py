"""
CVSS v3.1 base score calculator.

Implements the official CVSS v3.1 base score formula (FIRST.org) so the
platform computes severity deterministically from a vector, rather than
letting the LLM assign an arbitrary number. A rule-based mapper proposes a
vector from the finding category + evidence; a human/evaluator can override
the vector before the score is finalized.
"""
from dataclasses import dataclass

WEIGHTS = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
    "AC": {"L": 0.77, "H": 0.44},
    "PR_U": {"N": 0.85, "L": 0.62, "H": 0.27},       # when Scope = Unchanged
    "PR_C": {"N": 0.85, "L": 0.68, "H": 0.5},        # when Scope = Changed
    "UI": {"N": 0.85, "R": 0.62},
    "C": {"H": 0.56, "L": 0.22, "N": 0.0},
    "I": {"H": 0.56, "L": 0.22, "N": 0.0},
    "A": {"H": 0.56, "L": 0.22, "N": 0.0},
}


@dataclass
class CVSSVector:
    AV: str = "N"   # Attack Vector: N/A/L/P
    AC: str = "L"   # Attack Complexity: L/H
    PR: str = "N"   # Privileges Required: N/L/H
    UI: str = "N"   # User Interaction: N/R
    S: str = "U"    # Scope: U/C
    C: str = "N"    # Confidentiality: N/L/H
    I: str = "N"    # Integrity: N/L/H
    A: str = "N"    # Availability: N/L/H

    def to_vector_string(self) -> str:
        return f"CVSS:3.1/AV:{self.AV}/AC:{self.AC}/PR:{self.PR}/UI:{self.UI}/S:{self.S}/C:{self.C}/I:{self.I}/A:{self.A}"


def _roundup(value: float) -> float:
    int_val = round(value * 100000)
    if int_val % 10000 == 0:
        return int_val / 100000
    return (int_val // 10000 + 1) / 10.0


def calculate_base_score(v: CVSSVector) -> float:
    pr_table = WEIGHTS["PR_C"] if v.S == "C" else WEIGHTS["PR_U"]
    iss = 1 - ((1 - WEIGHTS["C"][v.C]) * (1 - WEIGHTS["I"][v.I]) * (1 - WEIGHTS["A"][v.A]))

    if v.S == "U":
        impact = 6.42 * iss
    else:
        impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)

    exploitability = 8.22 * WEIGHTS["AV"][v.AV] * WEIGHTS["AC"][v.AC] * pr_table[v.PR] * WEIGHTS["UI"][v.UI]

    if impact <= 0:
        return 0.0

    if v.S == "U":
        base = _roundup(min(impact + exploitability, 10))
    else:
        base = _roundup(min(1.08 * (impact + exploitability), 10))

    return round(base, 1)


def severity_label(score: float) -> str:
    if score == 0:
        return "info"
    if score < 4.0:
        return "low"
    if score < 7.0:
        return "medium"
    if score < 9.0:
        return "high"
    return "critical"


def propose_vector(category: str, status_code: int, has_auth_bypass: bool) -> CVSSVector:
    """Deterministic, rule-based starting vector per finding category.
    This is a conservative default intended to be reviewed/adjusted, not an
    automatic final answer."""
    if category == "authentication" or (category == "authorization" and has_auth_bypass):
        return CVSSVector(AV="N", AC="L", PR="N", UI="N", S="U", C="H", I="H", A="N")
    if category == "authorization":
        return CVSSVector(AV="N", AC="L", PR="L", UI="N", S="U", C="H", I="L", A="N")
    if category == "input_validation":
        return CVSSVector(AV="N", AC="L", PR="L", UI="N", S="U", C="L", I="L", A="N")
    if category == "api_security":
        return CVSSVector(AV="N", AC="L", PR="L", UI="N", S="U", C="L", I="N", A="N")
    if category == "security_configuration":
        return CVSSVector(AV="N", AC="H", PR="N", UI="N", S="U", C="L", I="N", A="N")
    return CVSSVector(AV="N", AC="H", PR="L", UI="N", S="U", C="L", I="N", A="N")


def score_finding(category: str, status_code: int = 200, has_auth_bypass: bool = False):
    vector = propose_vector(category, status_code, has_auth_bypass)
    score = calculate_base_score(vector)
    return score, vector.to_vector_string(), severity_label(score)
