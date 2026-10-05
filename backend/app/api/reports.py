from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.reports.report_generator import generate_report_markdown

router = APIRouter(prefix="/api/assessments", tags=["reports"])


@router.get("/{assessment_id}/report", response_class=PlainTextResponse)
def get_report(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(models.Assessment).get(assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    endpoints = db.query(models.Endpoint).filter(models.Endpoint.assessment_id == assessment_id).all()
    executions = db.query(models.TestExecution).filter(models.TestExecution.assessment_id == assessment_id).all()
    findings = db.query(models.Finding).filter(models.Finding.assessment_id == assessment_id).all()

    markdown = generate_report_markdown(assessment, endpoints, executions, findings)

    assessment.stage = "completed"
    assessment.status = "report_generated"
    db.commit()

    return markdown
