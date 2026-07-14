"""
Treatment plan service — F4.

create_treatment() computes action_priority deterministically from Tabla 20
(risk_level × effort) and creates the RiskTreatment record.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk import Risk, RiskTreatment
from app.modules.tratamiento.plan.schemas import TreatmentCreateInput
from app.modules.treatment.prioritization.priority import action_priority_from_table


async def create_treatment(
    db: AsyncSession,
    risk_id: uuid.UUID,
    data: TreatmentCreateInput,
) -> RiskTreatment:
    """Create a RiskTreatment with auto-calculated action_priority (Tabla 20).

    action_priority is derived deterministically from the risk's risk_level
    and the supplied effort value — never from user input.
    """
    risk = await db.get(Risk, risk_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="Riesgo no encontrado")

    priority = action_priority_from_table(risk.risk_level or "Bajo", data.effort)

    treatment = RiskTreatment(
        risk_id=risk_id,
        treatment_type=data.treatment_type,
        title=data.title,
        description=data.description,
        owner_name=data.owner_name,
        due_date=data.due_date,
        effort=data.effort,
        action_priority=priority,
        verification=data.verification,
        acceptance_justification=data.acceptance_justification,
        residual_level=data.residual_level,
        status="planned",
    )
    db.add(treatment)
    await db.flush()
    return treatment
