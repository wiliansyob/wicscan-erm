"""
Risk register service — F3 deterministic assess.

assess_scenario() applies Tabla 16 + Tabla 17 + Tabla 18 to produce a Risk
record for the given scenario. No AI call; all scores are pure lookups.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk import Risk
from app.modules.escenarios.models import RiskScenario
from app.modules.assessment.scoring.impact import impact_level_from_dimensions
from app.modules.assessment.scoring.matrix import risk_level_from_matrix
from app.modules.assessment.scoring.probability import lookup_probability
from app.modules.analisis.schemas import AssessScenarioInput

# Numeric approximations kept for backward compat with existing risk queries
_PROB_INT: dict[str, int] = {
    "Muy Alta": 5, "Alta": 4, "Media": 3, "Baja": 2, "Muy Baja": 1,
}
_IMP_INT: dict[str, int] = {
    "Muy Alto": 5, "Alto": 4, "Medio": 3, "Bajo": 2, "Muy Bajo": 1,
}


async def assess_scenario(
    db: AsyncSession,
    scenario_id: uuid.UUID,
    data: AssessScenarioInput,
) -> Risk:
    """Deterministically score a risk scenario and upsert the Risk record.

    Probability, impact_level, and risk_level are computed exclusively from
    lookup tables — never from an LLM.
    """
    scenario = await db.get(RiskScenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Escenario no encontrado")

    # ── deterministic scoring ─────────────────────────────────────────────
    prob_level = lookup_probability(
        data.factor_access_vector,
        data.factor_complexity,
        data.factor_privileges,
        data.factor_exploit_evidence,
    )
    imp_level = impact_level_from_dimensions(
        data.impact_operational,
        data.impact_financial,
        data.impact_normative,
        data.impact_reputational,
    )
    risk_level = risk_level_from_matrix(prob_level, imp_level)

    # Numeric approximations (keep existing API contracts working)
    prob_int = _PROB_INT.get(prob_level, 3)
    imp_int  = _IMP_INT.get(imp_level, 3)

    # ── upsert Risk ──────────────────────────────────────────────────────
    existing = await db.execute(
        select(Risk).where(Risk.scenario_id == scenario_id)
    )
    risk = existing.scalars().first()

    if risk is None:
        # Generate RN-xxx code (project-scoped)
        count_res = await db.execute(
            select(func.count()).select_from(Risk).where(
                Risk.project_id == scenario.project_id,
                Risk.risk_code.like("RN-%"),
            )
        )
        n = (count_res.scalar() or 0) + 1
        risk_code = f"RN-{n:03d}"

        risk = Risk(
            project_id=scenario.project_id,
            scenario_id=scenario_id,
            risk_code=risk_code,
            risk_title=data.risk_title,
            methodology="iso_31000",
            assessed_by="manual",
            status="open",
            # non-null legacy columns
            probability=prob_int,
            impact=imp_int,
            risk_score=float(prob_int * imp_int),
            risk_level=risk_level,
        )
        db.add(risk)

    # Always overwrite scoring fields (idempotent re-assessment)
    risk.risk_title            = data.risk_title
    risk.risk_description      = data.risk_description
    risk.factor_access_vector  = data.factor_access_vector
    risk.factor_complexity     = data.factor_complexity
    risk.factor_privileges     = data.factor_privileges
    risk.factor_exploit_evidence = data.factor_exploit_evidence
    risk.prob_level            = prob_level
    risk.impact_operational    = data.impact_operational
    risk.impact_financial      = data.impact_financial
    risk.impact_normative      = data.impact_normative
    risk.impact_reputational   = data.impact_reputational
    risk.impact_level          = imp_level
    risk.risk_level            = risk_level
    risk.probability           = prob_int
    risk.impact                = imp_int
    risk.risk_score            = float(prob_int * imp_int)
    risk.likelihood_rationale  = data.likelihood_rationale
    risk.impact_rationale      = data.impact_rationale
    risk.assessed_by           = "manual"

    # Mark scenario as assessed
    scenario.status = "assessed"

    await db.flush()
    return risk
