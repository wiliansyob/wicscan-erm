from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class BusinessProcessIn(BaseModel):
    name: str
    owner_name: str | None = None
    criticality: str = "important"          # critical|important|support
    revenue_dependency: str = "<20"         # <20|20-50|>50
    has_manual_alternative: bool = False
    contractual_commitments: bool = False
    notes: str | None = None

    @field_validator("criticality")
    @classmethod
    def _valid_criticality(cls, v: str) -> str:
        if v not in ("critical", "important", "support"):
            raise ValueError("criticality must be critical|important|support")
        return v

    @field_validator("revenue_dependency")
    @classmethod
    def _valid_revenue_dep(cls, v: str) -> str:
        if v not in ("<20", "20-50", ">50"):
            raise ValueError("revenue_dependency must be <20|20-50|>50")
        return v


class BusinessProcessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    owner_name: str | None = None
    criticality: str
    revenue_dependency: str
    has_manual_alternative: bool = False
    contractual_commitments: bool = False
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, proc: Any) -> "BusinessProcessOut":
        manual_alt = proc.manual_alternative or "none"
        contractual = proc.contractual_commitment
        return cls(
            id=proc.id,
            project_id=proc.project_id,
            name=proc.name,
            owner_name=proc.owner,
            criticality=proc.criticality,
            revenue_dependency=proc.revenue_dependency,
            has_manual_alternative=manual_alt not in ("none", None),
            contractual_commitments=bool(contractual and contractual.get("exists")),
            created_at=proc.created_at,
            updated_at=proc.updated_at,
        )


class BiaCalculateIn(BaseModel):
    """
    Input parameters for the BIA calculator.
    All monetary values in €; time in hours.
    """
    # Direct costs
    num_staff_affected: int = 0
    avg_salary_hour: float = 0.0
    infra_cost_per_hour: float = 0.0
    contractual_penalty_per_hour: float = 0.0
    sla_at_risk_value: float = 0.0

    # Revenue loss
    hourly_revenue: float = 0.0
    # Explicit pct override (0.0–1.0). If omitted, derived from process.revenue_dependency band.
    revenue_dependency_pct: float | None = None

    # Sanctions
    sn_active: bool = False
    sanction_amount: float = 0.0

    # For threshold classification
    annual_revenue: float = 0.0

    # Manual continuity overrides (None → use criticality defaults)
    mtpd_hours: float | None = None
    rto_hours: float | None = None
    rpo_hours: float | None = None


class BiaEstimateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    process_id: uuid.UUID
    impact_2h: float | None
    impact_8h: float | None
    impact_24h: float | None
    sn_active: bool
    mtpd_hours: float | None
    rto_hours: float | None
    rpo_hours: float | None
    breakdown: Any | None
    created_at: datetime
    updated_at: datetime

    @property
    def impact_level_2h(self) -> str | None:
        return (self.breakdown or {}).get("2", {}).get("impact_level")

    @property
    def impact_level_8h(self) -> str | None:
        return (self.breakdown or {}).get("8", {}).get("impact_level")

    @property
    def impact_level_24h(self) -> str | None:
        return (self.breakdown or {}).get("24", {}).get("impact_level")


class AssetProcessLinkIn(BaseModel):
    asset_id: uuid.UUID
    weight: float = 1.0

    @field_validator("weight")
    @classmethod
    def _valid_weight(cls, v: float) -> float:
        if not (0.0 < v <= 1.0):
            raise ValueError("weight must be between 0 (exclusive) and 1 (inclusive)")
        return v


class AssetProcessLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    process_id: uuid.UUID
    asset_id: uuid.UUID
    weight: float
    asset_name: str | None = None
    asset_type: str | None = None
    asset_criticality: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, link: Any) -> "AssetProcessLinkOut":
        return cls(
            id=link.id,
            process_id=link.process_id,
            asset_id=link.asset_id,
            weight=link.weight,
            created_at=link.created_at,
            updated_at=link.updated_at,
        )


class BusinessProcessWithBiaOut(BusinessProcessOut):
    bia: BiaEstimateOut | None = None
    asset_links: list[AssetProcessLinkOut] = []
