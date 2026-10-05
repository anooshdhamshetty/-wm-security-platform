from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/assessments", tags=["assessments"])


def _log(db: Session, assessment_id: str, stage: str, message: str, level: str = "info"):
    db.add(models.AssessmentLog(assessment_id=assessment_id, stage=stage, level=level, message=message))
    db.commit()


@router.post("", response_model=schemas.AssessmentOut)
def create_assessment(payload: schemas.AssessmentCreate, db: Session = Depends(get_db)):
    assessment = models.Assessment(
        name=payload.name,
        repo_url=payload.repo_url,
        target_base_url=payload.target_base_url,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    _log(db, assessment.id, "created", f"Assessment '{assessment.name}' created.")
    return assessment


@router.get("", response_model=list[schemas.AssessmentOut])
def list_assessments(db: Session = Depends(get_db)):
    return db.query(models.Assessment).order_by(models.Assessment.created_at.desc()).all()


@router.get("/{assessment_id}", response_model=schemas.AssessmentOut)
def get_assessment(assessment_id: str, db: Session = Depends(get_db)):
    a = db.query(models.Assessment).get(assessment_id)
    if not a:
        raise HTTPException(404, "Assessment not found")
    return a


@router.get("/{assessment_id}/logs", response_model=list[schemas.LogOut])
def get_logs(assessment_id: str, db: Session = Depends(get_db)):
    return (
        db.query(models.AssessmentLog)
        .filter(models.AssessmentLog.assessment_id == assessment_id)
        .order_by(models.AssessmentLog.created_at.asc())
        .all()
    )
