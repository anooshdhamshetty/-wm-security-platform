"""
Security assessment report generator.

Produces a Markdown report (exportable to PDF client-side or via pandoc)
covering the sections required by the problem statement. Pulls only from
data actually stored in the database -- never invents findings.
"""
from datetime import datetime
from typing import List

from app.models import Assessment, Endpoint, Finding, TestExecution


def generate_report_markdown(
    assessment: Assessment,
    endpoints: List[Endpoint],
    test_executions: List[TestExecution],
    findings: List[Finding],
) -> str:
    validated = [f for f in findings if f.status == "validated"]
    potential = [f for f in findings if f.status == "potential_finding"]
    inconclusive = [f for f in findings if f.status == "inconclusive"]

    by_sev = {"critical": [], "high": [], "medium": [], "low": [], "info": []}
    for f in validated:
        by_sev.setdefault(f.severity or "info", []).append(f)

    lines = []
    lines.append(f"# Security Assessment Report: {assessment.name}")
    lines.append(f"\n**Repository:** {assessment.repo_url}")
    lines.append(f"**Target:** {assessment.target_base_url or 'N/A'}")
    lines.append(f"**Assessment ID:** {assessment.id}")
    lines.append(f"**Generated:** {datetime.utcnow().isoformat()}Z\n")

    lines.append("## 1. Executive Summary")
    lines.append(
        f"This assessment analyzed {len(endpoints)} discovered endpoint(s), executed "
        f"{len(test_executions)} authorized test case(s), and produced {len(findings)} finding(s) "
        f"({len(validated)} validated, {len(potential)} potential, {len(inconclusive)} inconclusive).\n"
    )

    lines.append("## 2. Assessment Scope")
    lines.append(
        f"Testing was restricted to the explicitly authorized target `{assessment.target_base_url}` "
        f"and the source repository `{assessment.repo_url}`. Destructive test cases were excluded by design.\n"
    )

    lines.append("## 3. Methodology")
    lines.append(
        "1. Repository analysis via the GitHub API (no local clone required)\n"
        "2. Deterministic endpoint extraction (regex/pattern-based + OpenAPI parsing)\n"
        "3. Application map construction (NetworkX)\n"
        "4. Rule-based, endpoint-specific security test planning\n"
        "5. Safe, scope-restricted runtime testing via httpx\n"
        "6. Structured evidence capture for every executed test\n"
        "7. LLM-based reasoning over evidence (correlation & explanation only)\n"
        "8. Deterministic validation combining classifier + LLM verdict\n"
        "9. CVSS v3.1 base scoring\n"
        "10. Remediation guidance generation\n"
    )

    lines.append("## 4. Application Overview")
    lines.append(f"{len(endpoints)} endpoint(s) were discovered across the analyzed repository files.\n")

    lines.append("## 5. Endpoint Coverage")
    lines.append("| Method | Path | Auth Required | Discovered Via |")
    lines.append("|---|---|---|---|")
    for ep in endpoints:
        auth = "Yes" if ep.requires_auth else ("No" if ep.requires_auth is False else "Unknown")
        lines.append(f"| {ep.method} | {ep.path} | {auth} | {ep.discovered_via} |")
    lines.append("")

    lines.append("## 6. Test Coverage")
    lines.append(f"{len(test_executions)} test execution(s) across all endpoints.\n")
    result_counts = {}
    for t in test_executions:
        result_counts[t.result] = result_counts.get(t.result, 0) + 1
    for k, v in result_counts.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    lines.append("## 7. Vulnerability Summary")
    lines.append("| Severity | Count |")
    lines.append("|---|---|")
    for sev in ("critical", "high", "medium", "low", "info"):
        lines.append(f"| {sev.capitalize()} | {len(by_sev.get(sev, []))} |")
    lines.append("")

    lines.append("## 8. Detailed Findings\n")
    if not findings:
        lines.append("No findings were produced by this assessment run.\n")
    for f in findings:
        lines.append(f"### {f.title}  \n*Status: **{f.status}** | Severity: {f.severity or 'N/A'} "
                     f"| CVSS: {f.cvss_score or 'N/A'} ({f.cvss_vector or 'N/A'})*\n")
        lines.append(f"**Endpoint:** {f.method} {f.endpoint_path}\n")
        lines.append(f"**Description:** {f.description or 'N/A'}\n")
        lines.append(f"**Evidence:** {f.evidence_summary or 'N/A'}\n")
        lines.append(f"**Impact:** {f.impact or 'N/A'}\n")
        lines.append(f"**Affected Code:** {f.code_location or 'Code location could not be conclusively determined.'}\n")
        lines.append(f"**Root Cause:** {f.root_cause or 'N/A'}\n")
        lines.append(f"**Remediation:** {f.remediation or 'N/A'}\n")
        lines.append(f"**Verification:** {f.verification or 'N/A'}\n")
        if f.poc:
            lines.append(f"**Controlled PoC:**\n```json\n{f.poc}\n```\n")
        lines.append("---\n")

    lines.append("## 19. Limitations")
    lines.append(
        "- Endpoint discovery is pattern-based and may miss dynamically constructed routes.\n"
        "- Testing is restricted to safe, non-destructive probes; some vulnerability classes "
        "(e.g. stored XSS requiring a full browser render, complex business-logic flaws) require "
        "manual follow-up.\n"
        "- LLM analysis is a reasoning aid and is validated against deterministic evidence before "
        "a finding is marked 'validated'.\n"
    )

    lines.append("## 20. Conclusion")
    lines.append(
        "This report reflects only what was directly observed during authorized, scope-restricted "
        "testing of the target application and repository. Findings marked 'potential' or "
        "'inconclusive' require manual follow-up before remediation prioritization.\n"
    )

    lines.append("\n---\n*Generated for authorized security assessment purposes only.*")

    return "\n".join(lines)
