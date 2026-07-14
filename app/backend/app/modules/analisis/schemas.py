from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ImpactLevel = Literal["Muy Alto", "Alto", "Medio", "Bajo", "Muy Bajo"]


class AssessScenarioInput(BaseModel):
    risk_title: str = Field(..., min_length=3, max_length=512)
    factor_access_vector:    Literal["internet", "red_interna", "acceso_fisico"]
    factor_complexity:       Literal["ninguna", "moderada", "alta"]
    factor_privileges:       Literal["ninguno", "basico", "privilegiado"]
    factor_exploit_evidence: Literal["activa", "publico", "documentada", "sin_precedente"]
    impact_operational:  ImpactLevel
    impact_financial:    ImpactLevel
    impact_normative:    ImpactLevel
    impact_reputational: ImpactLevel
    risk_description:       str | None = None
    likelihood_rationale:   str | None = None
    impact_rationale:       str | None = None


class RiskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    risk_code: str | None = None
    risk_title: str
    risk_description: str | None = None
    scenario_id: uuid.UUID | None = None
    business_process_id: uuid.UUID | None = None
    # ISO 31000 scoring
    probability: int = 3
    impact: int = 3
    risk_score: float = 0.0
    prob_level:          str | None = None
    impact_operational:  str | None = None
    impact_financial:    str | None = None
    impact_normative:    str | None = None
    impact_reputational: str | None = None
    impact_level:        str | None = None
    risk_level:          str = "medio"
    # rationale
    likelihood_rationale: str | None = None
    impact_rationale:     str | None = None
    # meta
    assessed_by: str = "ai"
    status:      str = "open"
    residual_level: str | None = None
    created_at: datetime
    updated_at: datetime
