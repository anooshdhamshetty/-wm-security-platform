"""
Core database schema.

Simplified relative to a full production schema (see README) but covers
the full lifecycle: Assessment -> Repository -> Endpoints -> TestExecutions
-> Evidence -> Findings -> Report.
"""
import uuid
import datetime as dt

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id():
    return str(uuid.uuid4())


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    repo_url = Column(String, nullable=False)
    target_base_url = Column(String, nullable=True)
    status = Column(String, default="created")
    # created -> repo_analysis -> app_mapping -> test_planning ->
    # testing -> evidence -> ai_analysis -> validation -> risk ->
    # remediation -> report -> completed
    stage = Column(String, default="created")
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    endpoints = relationship("Endpoint", back_populates="assessment", cascade="all, delete-orphan")
    test_executions = relationship("TestExecution", back_populates="assessment", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="assessment", cascade="all, delete-orphan")
    files = relationship("RepoFile", back_populates="assessment", cascade="all, delete-orphan")
    logs = relationship("AssessmentLog", back_populates="assessment", cascade="all, delete-orphan")


class RepoFile(Base):
    __tablename__ = "repo_files"

    id = Column(String, primary_key=True, default=gen_id)
    assessment_id = Column(String, ForeignKey("assessments.id"))
    path = Column(String, nullable=False)
    language = Column(String, nullable=True)
    category = Column(String, nullable=True)  # frontend, backend, config, dependency, other
    sha = Column(String, nullable=True)
    size = Column(Integer, nullable=True)

    assessment = relationship("Assessment", back_populates="files")


class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(String, primary_key=True, default=gen_id)
    assessment_id = Column(String, ForeignKey("assessments.id"))
    path = Column(String, nullable=False)
    method = Column(String, nullable=False)
    source_file = Column(String, nullable=True)
    source_line = Column(Integer, nullable=True)
    handler_name = Column(String, nullable=True)
    requires_auth = Column(Boolean, default=None, nullable=True)  # None = unknown
    parameters = Column(JSON, default=list)
    request_body_schema = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    discovered_via = Column(String, nullable=True)  # "regex", "openapi"

    assessment = relationship("Assessment", back_populates="endpoints")
    test_cases = relationship("TestCase", back_populates="endpoint", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(String, primary_key=True, default=gen_id)
    endpoint_id = Column(String, ForeignKey("endpoints.id"))
    test_id = Column(String, nullable=False)   # e.g. AUTH-001
    category = Column(String, nullable=False)  # authentication, authorization, input_validation, ...
    description = Column(Text, nullable=True)
    request_template = Column(JSON, default=dict)
    expected_behavior = Column(Text, nullable=True)

    endpoint = relationship("Endpoint", back_populates="test_cases")


class TestExecution(Base):
    __tablename__ = "test_executions"

    id = Column(String, primary_key=True, default=gen_id)
    assessment_id = Column(String, ForeignKey("assessments.id"))
    test_case_id = Column(String, ForeignKey("test_cases.id"), nullable=True)
    test_id = Column(String, nullable=False)
    endpoint_path = Column(String, nullable=False)
    method = Column(String, nullable=False)
    request = Column(JSON, default=dict)
    response = Column(JSON, default=dict)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Float, nullable=True)
    result = Column(String, default="error")  # pass, fail, potential_finding, error
    error = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=dt.datetime.utcnow)

    assessment = relationship("Assessment", back_populates="test_executions")
    evidence = relationship("Evidence", back_populates="test_execution", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=gen_id)
    test_execution_id = Column(String, ForeignKey("test_executions.id"))
    summary = Column(Text, nullable=False)
    expected_behavior = Column(Text, nullable=True)
    actual_behavior = Column(Text, nullable=True)
    security_headers = Column(JSON, default=dict)
    related_code_location = Column(String, nullable=True)

    test_execution = relationship("TestExecution", back_populates="evidence")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=gen_id)
    assessment_id = Column(String, ForeignKey("assessments.id"))
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    endpoint_path = Column(String, nullable=True)
    method = Column(String, nullable=True)
    status = Column(String, default="potential_finding")
    # potential_finding, validated, false_positive, inconclusive
    severity = Column(String, nullable=True)   # critical/high/medium/low/info
    cvss_score = Column(Float, nullable=True)
    cvss_vector = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    impact = Column(Text, nullable=True)
    evidence_summary = Column(Text, nullable=True)
    code_location = Column(String, nullable=True)  # file:line or "could not be determined"
    root_cause = Column(Text, nullable=True)
    remediation = Column(Text, nullable=True)
    verification = Column(Text, nullable=True)
    poc = Column(JSON, default=dict)
    ai_raw_analysis = Column(JSON, default=dict)
    test_execution_id = Column(String, ForeignKey("test_executions.id"), nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    assessment = relationship("Assessment", back_populates="findings")


class AssessmentLog(Base):
    __tablename__ = "assessment_logs"

    id = Column(String, primary_key=True, default=gen_id)
    assessment_id = Column(String, ForeignKey("assessments.id"))
    stage = Column(String, nullable=False)
    level = Column(String, default="info")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    assessment = relationship("Assessment", back_populates="logs")
