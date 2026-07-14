from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class RiskScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    scenario_code: str | None
    title: str | None = None
    consequence: str
    group_key: str
    asset_id: uuid.UUID | None
    business_process_id: uuid.UUID | None
    status: str

    # Probability (set by AI in /probabilidad)
    probability: int | None = None
    prob_level: str | None = None
    probability_rationale: str | None = None

    # Impact (set in /impacto)
    impact: int | None = None
    impact_level: str | None = None
    impact_rationale: str | None = None
    impact_operational: str | None = None
    impact_financial: str | None = None
    impact_normative: str | None = None
    impact_reputational: str | None = None

    # Computed display fields (populated by router, not stored in DB)
    finding_count: int | None = None
    business_process_name: str | None = None
    asset_name: str | None = None

    created_at: datetime
    updated_at: datetime


class ConsolidateBody(BaseModel):
    finding_ids: list[uuid.UUID] | None = None
    ai_provider: str | None = None
    model: str | None = None


class ConsolidateResult(BaseModel):
    findings_processed: int
    scenarios_created: int
    scenarios_updated: int
    scenarios: list[RiskScenarioOut]


class ScenarioProbabilityUpdate(BaseModel):
    probability: Annotated[int, Field(ge=1, le=5)]
    prob_level: str
    probability_rationale: str | None = None


class ScenarioImpactUpdate(BaseModel):
    business_process_id: uuid.UUID | None = None
    impact: Annotated[int, Field(ge=1, le=5)]
    impact_level: str
    impact_rationale: str | None = None
    impact_operational: str | None = None
    impact_financial: str | None = None
    impact_normative: str | None = None
    impact_reputational: str | None = None
