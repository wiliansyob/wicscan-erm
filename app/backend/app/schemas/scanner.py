import uuid
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class ScannerEngineBase(BaseModel):
    name: str = Field(..., max_length=255)
    engine_type: str = Field(..., max_length=50)
    category: str = Field(default="sast", max_length=50)
    url: str | HttpUrl = Field(...)
    is_active: bool = True


class ScannerEngineCreate(ScannerEngineBase):
    api_key: str | None = None
    workspace_id: uuid.UUID | None = None


class ScannerEngineUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    engine_type: str | None = Field(None, max_length=50)
    category: str | None = Field(None, max_length=50)
    url: str | HttpUrl | None = None
    api_key: str | None = None
    is_active: bool | None = None


class ScannerEngineOut(ScannerEngineBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
