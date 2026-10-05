from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app import models, schemas
from app.analyzers.endpoint_extractor import ExtractedEndpoint
from app.testing.test_planner import plan_tests_for_endpoint
from app.testing.httpx_runner import SafeHttpxRunner, ScopeViolationError
from app.evidence.evidence_engine import build_evidence
from app.ai.analyzer import analyze_evidence
from app.validation.validator import validate_finding
from app.scoring.cvss import score_finding
from app.config import get_settings

router = APIRouter(prefix="/api/assessments", tags=["testing"])


def _log(db: Session, assessment_id: str, stage: str, message: str, level: str = "info"):
    db.add(models.AssessmentLog(assessment_id=assessment_id, stage=stage, level=level, message=message))
    db.commit()


class RunTestsRequest(BaseModel):
    target_base_url: Optional[str] = None
    auth_token: Optional[str] = None


@router.post("/{assessment_id}/run-tests")
def run_tests(assessment_id: str, payload: RunTestsRequest, db: Session = Depends(get_db)):
    assessment = db.query(models.Assessment).get(assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    settings = get_settings()
    target = payload.target_base_url or assessment.target_base_url or settings.TARGET_BASE_URL
    endpoints_db = db.query(models.Endpoint).filter(models.Endpoint.assessment_id == assessment_id).all()
    if not endpoints_db:
        raise HTTPException(400, "No endpoints discovered. Run repository analysis first.")

    assessment.stage = "testing"
    assessment.target_base_url = target
    db.commit()
    _log(db, assessment_id, "testing", f"Starting authorized test execution against {target}")

    try:
        runner = SafeHttpxRunner(base_url=target, auth_token=payload.auth_token)
    except ScopeViolationError as e:
        _log(db, assessment_id, "testing", str(e), level="error")
        raise HTTPException(400, str(e))

    executed = 0
    findings_created = 0

    try:
        for ep_db in endpoints_db:
            ep = ExtractedEndpoint(
                path=ep_db.path, method=ep_db.method, source_file=ep_db.source_file or "unknown",
                source_line=ep_db.source_line or 0, handler_name=ep_db.handler_name,
                requires_auth=ep_db.requires_auth, parameters=ep_db.parameters or [],
            )
            planned_tests = plan_tests_for_endpoint(ep)

            for test in planned_tests:
                result = runner.run(test)
                executed += 1

                te = models.TestExecution(
                    assessment_id=assessment_id,
                    test_id=result.test_id,
                    endpoint_path=result.path,
                    method=result.method,
                    request=result.request,
                    response=result.response,
                    status_code=result.status_code,
                    duration_ms=result.duration_ms,
                    result=result.result,
                    error=result.error,
                )
                db.add(te)
                db.commit()
                db.refresh(te)

                code_location = f"{ep_db.source_file}:{ep_db.source_line}" if ep_db.source_file else None
                evidence = build_evidence(
                    test_category=test.category,
                    expected_behavior=test.expected_behavior,
                    status_code=result.status_code,
                    response_headers=(result.response or {}).get("headers", {}),
                    body_preview=(result.response or {}).get("body_preview", ""),
                    code_location=code_location,
                )
                db.add(models.Evidence(
                    test_execution_id=te.id,
                    summary=evidence["summary"],
                    expected_behavior=evidence["expected_behavior"],
                    actual_behavior=evidence["actual_behavior"],
                    security_headers=evidence["security_headers"],
                    related_code_location=evidence["related_code_location"],
                ))
                db.commit()

                if result.result == "potential_finding":
                    ai_result = analyze_evidence(
                        method=result.method, path=result.path, category=test.category,
                        description=test.description, expected_behavior=test.expected_behavior,
                        actual_behavior=evidence["actual_behavior"], status_code=result.status_code,
                        security_headers=evidence["security_headers"],
                        body_preview=(result.response or {}).get("body_preview", ""),
                        code_location=code_location,
                    )
                    final_status = validate_finding("potential_finding", ai_result)

                    score, vector, severity = score_finding(
                        category=test.category,
                        status_code=result.status_code or 0,
                        has_auth_bypass=(test.category in ("authentication", "authorization")),
                    )

                    finding = models.Finding(
                        assessment_id=assessment_id,
                        title=f"{test.category.replace('_', ' ').title()} issue on {result.method} {result.path}",
                        category=test.category,
                        endpoint_path=result.path,
                        method=result.method,
                        status=final_status,
                        severity=severity if final_status == "validated" else None,
                        cvss_score=score if final_status == "validated" else None,
                        cvss_vector=vector if final_status == "validated" else None,
                        description=test.description,
                        impact=ai_result.get("potential_impact"),
                        evidence_summary=evidence["summary"],
                        code_location=evidence["related_code_location"],
                        root_cause=ai_result.get("security_principle_violated"),
                        remediation=ai_result.get("recommended_fix"),
                        verification=ai_result.get("additional_validation_required"),
                        poc={
                            "request": result.request,
                            "response": {k: v for k, v in (result.response or {}).items() if k != "headers"},
                        },
                        ai_raw_analysis=ai_result,
                        test_execution_id=te.id,
                    )
                    db.add(finding)
                    db.commit()
                    findings_created += 1
    finally:
        runner.close()

    assessment.status = "tested"
    assessment.stage = "evidence"
    db.commit()
    _log(db, assessment_id, "testing", f"Executed {executed} test(s); {findings_created} finding(s) created for review.")

    return {"tests_executed": executed, "findings_created": findings_created}


@router.get("/{assessment_id}/test-executions", response_model=list[schemas.TestExecutionOut])
def get_test_executions(assessment_id: str, db: Session = Depends(get_db)):
    return (
        db.query(models.TestExecution)
        .filter(models.TestExecution.assessment_id == assessment_id)
        .order_by(models.TestExecution.executed_at.asc())
        .all()
    )


@router.get("/{assessment_id}/endpoints", response_model=list[schemas.EndpointOut])
def get_endpoints(assessment_id: str, db: Session = Depends(get_db)):
    return db.query(models.Endpoint).filter(models.Endpoint.assessment_id == assessment_id).all()
