"""
Risk register router — F3.

  POST /scenarios/{scenario_id}/assess   ← deterministic scoring (Tabla 16-18)
  GET  /projects/{project_id}/risk-register  ← Tabla 19 — all RN-xxx risks
  GET  /risks/{risk_id}                  ← single risk detail
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.models.risk import Risk
from app.modules.analisis.schemas import AssessScenarioInput, RiskOut
from app.modules.analisis.service import assess_scenario

router = APIRouter(tags=["risk-register"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/scenarios/{scenario_id}/assess", response_model=RiskOut)
async def assess(
    scenario_id: uuid.UUID,
    body: AssessScenarioInput,
    db: DB,
    current_user: CurrentUser,
):
    """Score a risk scenario deterministically (Tabla 16 + 17 + 18).

    Probability, impact level, and risk level are computed exclusively from
    ISO 31000 lookup tables — no AI involved.
    """
    risk = await assess_scenario(db, scenario_id, body)
    return RiskOut.model_validate(risk)


@router.get(
    "/projects/{project_id}/risk-register",
    response_model=list[RiskOut],
)
async def list_risk_register(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Return all ISO 31000 risks (RN-xxx) for the project — Tabla 19."""
    result = await db.execute(
        select(Risk)
        .where(
            Risk.project_id == project_id,
            Risk.risk_code.like("RN-%"),
        )
        .order_by(Risk.risk_code)
    )
    return [RiskOut.model_validate(r) for r in result.scalars().all()]


@router.get("/risks/{risk_id}", response_model=RiskOut)
async def get_risk(
    risk_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    risk = await db.get(Risk, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Riesgo no encontrado")
    return RiskOut.model_validate(risk)
