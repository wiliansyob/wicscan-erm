from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TreatmentCreateInput(BaseModel):
    treatment_type: Literal["mitigate", "avoid", "transfer", "accept"]
    title: str = Field(..., min_length=3, max_length=512)
    description: str | None = None
    owner_name: str | None = None
    due_date: datetime | None = None
    effort: Literal["low", "high"]
    verification: str | None = None
    acceptance_justification: str | None = None
    residual_level: str | None = None


class TreatmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    risk_id: uuid.UUID
    treatment_type: str
    title: str
    description: str | None
    owner_name: str | None
    due_date: datetime | None
    effort: str | None
    action_priority: int | None
    verification: str | None
    status: str
    residual_level: str | None
    acceptance_justification: str | None
    created_at: datetime
    updated_at: datetime
