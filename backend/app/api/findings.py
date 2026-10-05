from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/assessments", tags=["findings"])


@router.get("/{assessment_id}/findings", response_model=list[schemas.FindingOut])
def get_findings(assessment_id: str, db: Session = Depends(get_db)):
    return (
        db.query(models.Finding)
        .filter(models.Finding.assessment_id == assessment_id)
        .order_by(models.Finding.created_at.desc())
        .all()
    )


@router.get("/{assessment_id}/findings/{finding_id}", response_model=schemas.FindingOut)
def get_finding(assessment_id: str, finding_id: str, db: Session = Depends(get_db)):
    f = db.query(models.Finding).filter(
        models.Finding.id == finding_id, models.Finding.assessment_id == assessment_id
    ).first()
    if not f:
        raise HTTPException(404, "Finding not found")
    return f


@router.get("/{assessment_id}/dashboard-summary")
def dashboard_summary(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(models.Assessment).get(assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    endpoints = db.query(models.Endpoint).filter(models.Endpoint.assessment_id == assessment_id).all()
    executions = db.query(models.TestExecution).filter(models.TestExecution.assessment_id == assessment_id).all()
    findings = db.query(models.Finding).filter(models.Finding.assessment_id == assessment_id).all()

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        if f.status == "validated" and f.severity in severity_counts:
            severity_counts[f.severity] += 1

    return {
        "assessment_id": assessment_id,
        "stage": assessment.stage,
        "status": assessment.status,
        "total_endpoints": len(endpoints),
        "endpoints_tested": len({e.endpoint_path for e in executions}),
        "tests_executed": len(executions),
        "potential_findings": len([f for f in findings if f.status == "potential_finding"]),
        "validated_vulnerabilities": len([f for f in findings if f.status == "validated"]),
        "false_positives": len([f for f in findings if f.status == "false_positive"]),
        "inconclusive": len([f for f in findings if f.status == "inconclusive"]),
        "severity_breakdown": severity_counts,
    }
