from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.analyzers.repository_analyzer import RepositoryAnalyzer, GitHubAPIError
from app.analyzers.endpoint_extractor import extract_all
from app.analyzers.openapi_analyzer import extract_all_openapi
from app.mapping.application_mapper import build_application_map, graph_to_json

router = APIRouter(prefix="/api/assessments", tags=["analysis"])


def _log(db: Session, assessment_id: str, stage: str, message: str, level: str = "info"):
    db.add(models.AssessmentLog(assessment_id=assessment_id, stage=stage, level=level, message=message))
    db.commit()


@router.post("/{assessment_id}/analyze-repository")
def analyze_repository(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(models.Assessment).get(assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    assessment.stage = "repo_analysis"
    db.commit()
    _log(db, assessment_id, "repo_analysis", f"Starting GitHub analysis of {assessment.repo_url}")

    analyzer = RepositoryAnalyzer()
    try:
        result = analyzer.analyze(assessment.repo_url)
    except GitHubAPIError as e:
        _log(db, assessment_id, "repo_analysis", str(e), level="error")
        assessment.status = "error"
        db.commit()
        raise HTTPException(400, str(e))
    except ValueError as e:
        _log(db, assessment_id, "repo_analysis", str(e), level="error")
        raise HTTPException(400, str(e))

    # persist files
    db.query(models.RepoFile).filter(models.RepoFile.assessment_id == assessment_id).delete()
    for f in result.files:
        db.add(models.RepoFile(
            assessment_id=assessment_id, path=f.path, category=f.category,
            sha=f.sha, size=f.size,
        ))
    for err in result.errors:
        _log(db, assessment_id, "repo_analysis", err, level="warning")

    db.commit()
    _log(db, assessment_id, "repo_analysis",
         f"Retrieved {len(result.files)} relevant file(s) "
         f"({sum(1 for f in result.files if f.category == 'backend')} backend, "
         f"{sum(1 for f in result.files if f.category == 'frontend')} frontend, "
         f"{sum(1 for f in result.files if f.category == 'config')} config).")

    # --- endpoint extraction (regex + openapi) ---
    endpoints = extract_all(result.files) + extract_all_openapi(result.files)

    db.query(models.Endpoint).filter(models.Endpoint.assessment_id == assessment_id).delete()
    for ep in endpoints:
        db.add(models.Endpoint(
            assessment_id=assessment_id, path=ep.path, method=ep.method,
            source_file=ep.source_file, source_line=ep.source_line,
            handler_name=ep.handler_name, requires_auth=ep.requires_auth,
            parameters=ep.parameters, discovered_via=ep.discovered_via,
        ))
    db.commit()

    _log(db, assessment_id, "repo_analysis", f"Discovered {len(endpoints)} unique endpoint(s).")
    assessment.status = "repo_analyzed"
    db.commit()

    return {
        "files_analyzed": len(result.files),
        "endpoints_discovered": len(endpoints),
        "truncated": result.truncated,
        "errors": result.errors,
    }


@router.post("/{assessment_id}/build-application-map")
def build_app_map(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(models.Assessment).get(assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    files_db = db.query(models.RepoFile).filter(models.RepoFile.assessment_id == assessment_id).all()
    endpoints_db = db.query(models.Endpoint).filter(models.Endpoint.assessment_id == assessment_id).all()

    if not endpoints_db:
        raise HTTPException(400, "No endpoints discovered yet. Run repository analysis first.")

    # Rebuild lightweight dataclasses for the mapper (content isn't needed again here
    # except for the frontend-call heuristic, which we skip at this stage for simplicity
    # in the basic model -- endpoints/files/handlers are still fully connected).
    from app.analyzers.endpoint_extractor import ExtractedEndpoint
    from app.analyzers.repository_analyzer import RepoFileRef

    extracted = [
        ExtractedEndpoint(
            path=e.path, method=e.method, source_file=e.source_file or "unknown",
            source_line=e.source_line or 0, handler_name=e.handler_name,
            requires_auth=e.requires_auth, parameters=e.parameters or [],
            discovered_via=e.discovered_via or "regex",
        )
        for e in endpoints_db
    ]
    file_refs = [RepoFileRef(path=f.path, sha=f.sha or "", size=f.size or 0, category=f.category or "other") for f in files_db]

    graph = build_application_map(file_refs, extracted)
    assessment.stage = "app_mapping"
    assessment.status = "app_mapped"
    db.commit()
    _log(db, assessment_id, "app_mapping", f"Application map built: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges.")

    return graph_to_json(graph)


@router.get("/{assessment_id}/application-map")
def get_app_map(assessment_id: str, db: Session = Depends(get_db)):
    # Recomputed on read for the basic model (graph isn't persisted separately)
    return build_app_map(assessment_id, db)
