import uuid
from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import OrmModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    risk_appetite: str = "medium"
    business_context: str | None = None
    scanner_config: dict | None = None
    ai_provider_config: dict | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    risk_appetite: str | None = None
    business_context: str | None = None
    scanner_config: dict | None = None
    ai_provider_config: dict | None = None
    status: str | None = None


class ProjectOut(OrmModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    risk_appetite: str
    business_context: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    asset_count: int = 0
    open_risk_count: int = 0
    critical_risk_count: int = 0
