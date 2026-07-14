"""
Treatment plan router — F4.

  POST /risks/{risk_id}/treatment   ← ISO 31000: creates + calculates action_priority
  GET  /risks/{risk_id}/treatment   ← list ISO treatments (action_priority populated)
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.models.risk import RiskTreatment
from app.modules.tratamiento.plan.schemas import TreatmentCreateInput, TreatmentOut
from app.modules.tratamiento.plan.service import create_treatment

router = APIRouter(tags=["treatment"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/risks/{risk_id}/treatment",
    response_model=TreatmentOut,
    status_code=201,
)
async def add_iso_treatment(
    risk_id: uuid.UUID,
    body: TreatmentCreateInput,
    db: DB,
    current_user: CurrentUser,
):
    """Create a treatment plan for a risk.

    action_priority (1–4) is computed deterministically from Tabla 20
    (risk_level × effort) and stored on the record.
    """
    treatment = await create_treatment(db, risk_id, body)
    return TreatmentOut.model_validate(treatment)


@router.get(
    "/risks/{risk_id}/treatment",
    response_model=list[TreatmentOut],
)
async def list_iso_treatments(
    risk_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """List all treatments for a risk that have action_priority populated."""
    result = await db.execute(
        select(RiskTreatment)
        .where(
            RiskTreatment.risk_id == risk_id,
            RiskTreatment.action_priority.isnot(None),
        )
        .order_by(RiskTreatment.action_priority, RiskTreatment.created_at)
    )
    return [TreatmentOut.model_validate(t) for t in result.scalars().all()]
