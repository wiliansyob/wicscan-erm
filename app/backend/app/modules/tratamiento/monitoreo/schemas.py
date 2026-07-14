from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TriggerEventCreate(BaseModel):
    event_type: Literal[
        "new_critical_vuln",
        "new_system",
        "incident",
        "regulatory_change",
        "new_contract",
        "structural_change",
    ]
    description: str | None = None
    detected_at: datetime | None = None  # defaults to now if omitted


class TriggerEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    event_type: str
    description: str | None
    detected_at: datetime
    created_at: datetime


class ReviewCycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    cycle_type: str
    triggered_by: uuid.UUID | None
    performed_at: datetime | None
    status: str
    summary: dict | None
    created_at: datetime


class RiskIndicatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: str
    pending_critical_high: int
    actions_on_time_pct: float
    incidents_count: int
    normative_status: dict | None
