import uuid
from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import OrmModel


class FindingOut(OrmModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    asset_id: uuid.UUID | None
    scanner: str
    finding_type: str
    category: str
    cwe: str | None
    owasp_category: str | None
    cvss_score: float | None
    severity: str
    title: str
    description: str | None
    remediation_guidance: str | None
    file_path: str | None
    line_start: int | None
    line_end: int | None
    component: str | None
    confidence: float
    status: str
    fingerprint: str | None
    finding_code: str | None
    first_detected_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None
    created_at: datetime


class FindingStatusUpdate(BaseModel):
    status: str
    reason: str | None = None


class FindingManualCreate(BaseModel):
    asset_id: uuid.UUID
    title: str
    description: str | None = None
    remediation_guidance: str | None = None
    severity: str
    category: str
    finding_type: str = "vulnerability"
    cwe: str | None = None
    owasp_category: str | None = None
    cvss_score: float | None = None
    file_path: str | None = None
    line_start: int | None = None
    source: str | None = None


class FindingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    remediation_guidance: str | None = None
    severity: str | None = None
    category: str | None = None
    finding_type: str | None = None
    cwe: str | None = None
    owasp_category: str | None = None
    cvss_score: float | None = None
    file_path: str | None = None
    line_start: int | None = None
    scanner: str | None = None
    status: str | None = None
    status_reason: str | None = None
    asset_id: uuid.UUID | None = None
