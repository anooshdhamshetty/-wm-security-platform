from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class AssessmentCreate(BaseModel):
    name: str
    repo_url: str
    target_base_url: Optional[str] = None


class AssessmentOut(BaseModel):
    id: str
    name: str
    repo_url: str
    target_base_url: Optional[str]
    status: str
    stage: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EndpointOut(BaseModel):
    id: str
    path: str
    method: str
    source_file: Optional[str]
    source_line: Optional[int]
    handler_name: Optional[str]
    requires_auth: Optional[bool]
    parameters: List[Any] = []
    discovered_via: Optional[str]

    class Config:
        from_attributes = True


class TestExecutionOut(BaseModel):
    id: str
    test_id: str
    endpoint_path: str
    method: str
    status_code: Optional[int]
    duration_ms: Optional[float]
    result: str
    request: Dict[str, Any] = {}
    response: Dict[str, Any] = {}
    executed_at: datetime

    class Config:
        from_attributes = True


class FindingOut(BaseModel):
    id: str
    title: str
    category: str
    endpoint_path: Optional[str]
    method: Optional[str]
    status: str
    severity: Optional[str]
    cvss_score: Optional[float]
    cvss_vector: Optional[str]
    description: Optional[str]
    impact: Optional[str]
    evidence_summary: Optional[str]
    code_location: Optional[str]
    root_cause: Optional[str]
    remediation: Optional[str]
    verification: Optional[str]
    poc: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class LogOut(BaseModel):
    stage: str
    level: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
