import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.common import OrmModel


class RiskCreate(BaseModel):
    risk_title: str
    risk_description: str | None = None
    business_impact_operational: str | None = None
    business_impact_financial: str | None = None
    business_impact_normative: str | None = None
    business_impact_reputational: str | None = None
    risk_category: str = "security"
    probability: int = Field(3, ge=1, le=5)
    impact: int = Field(3, ge=1, le=5)
    asset_id: uuid.UUID | None = None
    methodology: str = "iso_31000"
    priority: str | None = None
    finding_ids: list[uuid.UUID] = []


class RiskUpdate(BaseModel):
    risk_title: str | None = None
    risk_description: str | None = None
    business_impact_operational: str | None = None
    business_impact_financial: str | None = None
    business_impact_normative: str | None = None
    business_impact_reputational: str | None = None
    risk_category: str | None = None
    probability: int | None = Field(None, ge=1, le=5)
    impact: int | None = Field(None, ge=1, le=5)
    likelihood_rationale: str | None = None
    impact_rationale: str | None = None
    priority: str | None = None
    status: str | None = None


class RiskTreatmentCreate(BaseModel):
    treatment_type: str = Field(..., pattern="^(mitigate|avoid|transfer|accept)$")
    title: str
    description: str | None = None
    owner_name: str | None = None
    due_date: datetime | None = None
    priority: str = "medium_term"
    acceptance_justification: str | None = None
    expected_risk_reduction: float | None = None


class RiskTreatmentUpdate(BaseModel):
    treatment_type: str | None = Field(None, pattern="^(mitigate|avoid|transfer|accept)$")
    title: str | None = None
    description: str | None = None
    owner_name: str | None = None
    due_date: datetime | None = None
    priority: str | None = None
    status: str | None = None
    acceptance_justification: str | None = None
    expected_risk_reduction: float | None = None


class RiskTreatmentOut(OrmModel):
    id: uuid.UUID
    risk_id: uuid.UUID
    treatment_type: str
    title: str
    description: str | None
    owner_name: str | None
    due_date: datetime | None
    priority: str
    status: str
    acceptance_justification: str | None
    expected_risk_reduction: float | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RiskOut(OrmModel):
    id: uuid.UUID
    project_id: uuid.UUID
    asset_id: uuid.UUID | None
    business_process_id: uuid.UUID | None = None
    risk_engine_run_id: uuid.UUID | None = None
    risk_code: str | None
    risk_title: str
    risk_description: str | None
    business_impact_operational: str | None = None
    business_impact_financial: str | None = None
    business_impact_normative: str | None = None
    business_impact_reputational: str | None = None
    risk_category: str
    probability: int
    impact: int
    risk_score: float
    risk_level: str
    likelihood_rationale: str | None
    impact_rationale: str | None
    affected_cia: list | None
    methodology: str
    assessed_by: str
    priority: str | None
    status: str
    confirmed_at: datetime | None
    residual_score: float | None
    residual_level: str | None
    impact_operational: str | None = None
    impact_financial: str | None = None
    impact_normative: str | None = None
    impact_reputational: str | None = None
    created_at: datetime
    updated_at: datetime
    treatments: list[RiskTreatmentOut] = []
    finding_ids: list[uuid.UUID] = []


class RiskEngineRunCreate(BaseModel):
    scan_session_id: uuid.UUID
    ai_provider: str
    model_used: str | None = None
    finding_ids: list[uuid.UUID] | None = None
    prompt_template: str | None = None


class RiskEngineRunOut(OrmModel):
    id: uuid.UUID
    project_id: uuid.UUID
    scan_session_id: uuid.UUID
    ai_provider: str
    model_used: str
    status: str
    findings_input_count: int
    risks_generated_count: int
    tokens_used: int | None
    cost_usd: float | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime


class RiskMatrixData(BaseModel):
    matrix: list[list[int]]
    risks: list[dict]
    summary: dict
