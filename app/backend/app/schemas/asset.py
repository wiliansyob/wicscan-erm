import uuid
from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import OrmModel


class AssetCreate(BaseModel):
    name: str
    description: str | None = None
    asset_type: str
    criticality: str = "medium"
    technical_owner: str | None = None
    business_owner: str | None = None
    url: str | None = None
    ip_address: str | None = None
    tags: dict | None = None
    readme_content: str | None = None


class AssetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    asset_type: str | None = None
    criticality: str | None = None
    technical_owner: str | None = None
    business_owner: str | None = None
    url: str | None = None
    ip_address: str | None = None
    tags: dict | None = None
    is_active: bool | None = None
    readme_content: str | None = None


class AssetOut(OrmModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    asset_type: str
    criticality: str
    technical_owner: str | None
    business_owner: str | None
    url: str | None
    ip_address: str | None
    tags: dict | None
    is_active: bool
    readme_content: str | None
    created_at: datetime
    updated_at: datetime
