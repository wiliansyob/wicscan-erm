import uuid
from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import OrmModel


class CodeSourceCreate(BaseModel):
    source_type: str  # github | zip
    label: str | None = None
    asset_id: uuid.UUID | None = None
    github_url: str | None = None
    github_branch: str = "main"
    github_token: str | None = None


class CodeSourceOut(OrmModel):
    id: uuid.UUID
    project_id: uuid.UUID
    asset_id: uuid.UUID | None
    source_type: str
    label: str | None
    github_url: str | None
    github_branch: str
    github_token: str | None
    zip_filename: str | None
    local_snapshot_path: str | None
    snapshot_hash: str | None
    status: str
    error_message: str | None
    ready_at: datetime | None
    created_at: datetime
    updated_at: datetime
