import uuid
from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import OrmModel


class ScanSessionCreate(BaseModel):
    code_source_id: uuid.UUID | None = None
    asset_id: uuid.UUID | None = None
    scanners: list[str] = ["sonarqube"]
    scanner_configs: dict[str, dict] | None = None
    is_retest: bool = False
    baseline_session_id: uuid.UUID | None = None


class ScanSessionOut(OrmModel):
    id: uuid.UUID
    project_id: uuid.UUID
    code_source_id: uuid.UUID
    status: str
    is_retest: bool
    baseline_session_id: uuid.UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    scanners_requested: list | None
    total_findings_count: int
    new_findings_count: int
    resolved_findings_count: int
    error_message: str | None
    created_at: datetime


class ScanOut(OrmModel):
    id: uuid.UUID
    session_id: uuid.UUID
    scanner_type: str
    status: str
    findings_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
