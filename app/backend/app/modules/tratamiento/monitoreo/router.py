"""
Monitoring router — F4 §3.4.3.

  POST /projects/{project_id}/trigger-events   ← register event → auto-open ReviewCycle
  GET  /projects/{project_id}/trigger-events   ← list events
  GET  /projects/{project_id}/review-cycles    ← list review cycles
  GET  /projects/{project_id}/indicators       ← calculate 4 indicators (?period=YYYY-QN)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.models.risk import Risk, RiskTreatment
from app.modules.tratamiento.monitoreo.indicators import (
    IndicatorResult,
    calculate_indicators,
    current_period,
    parse_period_range,
)
from app.modules.tratamiento.monitoreo.models import ReviewCycle, RiskIndicator, TriggerEvent
from app.modules.tratamiento.monitoreo.schemas import (
    ReviewCycleOut,
    RiskIndicatorOut,
    TriggerEventCreate,
    TriggerEventOut,
)

router = APIRouter(tags=["monitoring"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ─── trigger events ──────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/trigger-events",
    response_model=ReviewCycleOut,
    status_code=201,
)
async def create_trigger_event(
    project_id: uuid.UUID,
    body: TriggerEventCreate,
    db: DB,
    current_user: CurrentUser,
):
    """Register a trigger event and automatically open a ReviewCycle."""
    detected = body.detected_at or datetime.now(tz=timezone.utc)

    event = TriggerEvent(
        project_id=project_id,
        event_type=body.event_type,
        description=body.description,
        detected_at=detected,
    )
    db.add(event)
    await db.flush()

    cycle = ReviewCycle(
        project_id=project_id,
        cycle_type="triggered",
        triggered_by=event.id,
        status="pending",
    )
    db.add(cycle)
    await db.flush()

    return ReviewCycleOut.model_validate(cycle)


@router.get(
    "/projects/{project_id}/trigger-events",
    response_model=list[TriggerEventOut],
)
async def list_trigger_events(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(TriggerEvent)
        .where(TriggerEvent.project_id == project_id)
        .order_by(TriggerEvent.detected_at.desc())
    )
    return [TriggerEventOut.model_validate(e) for e in result.scalars().all()]


# ─── review cycles ───────────────────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/review-cycles",
    response_model=list[ReviewCycleOut],
)
async def list_review_cycles(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(ReviewCycle)
        .where(ReviewCycle.project_id == project_id)
        .order_by(ReviewCycle.created_at.desc())
    )
    return [ReviewCycleOut.model_validate(c) for c in result.scalars().all()]


# ─── indicators ──────────────────────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/indicators",
    response_model=RiskIndicatorOut,
)
async def get_indicators(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    period: str = Query(default=None, description="Quarter: YYYY-QN, e.g. 2026-Q3"),
):
    """Calculate and cache the four §3.4.3 indicators for the given quarter."""
    if not period:
        period = current_period()

    start, end = parse_period_range(period)

    # 1. All open risks for the project
    risk_rows = await db.execute(
        select(Risk.risk_level, Risk.status).where(Risk.project_id == project_id)
    )
    open_risks = [{"risk_level": r, "status": s} for r, s in risk_rows.all()]

    # 2. Treatments whose due_date falls in the period
    treat_rows = await db.execute(
        select(RiskTreatment.status, RiskTreatment.due_date, RiskTreatment.completed_at)
        .join(Risk, RiskTreatment.risk_id == Risk.id)
        .where(
            Risk.project_id == project_id,
            RiskTreatment.due_date >= start,
            RiskTreatment.due_date <= end,
        )
    )
    period_treatments = [
        {"status": s, "due_date": d, "completed_at": c}
        for s, d, c in treat_rows.all()
    ]

    # 3. Trigger events in the period
    event_rows = await db.execute(
        select(TriggerEvent.event_type)
        .where(
            TriggerEvent.project_id == project_id,
            TriggerEvent.detected_at >= start,
            TriggerEvent.detected_at <= end,
        )
    )
    period_events = [{"event_type": et} for et, in event_rows.all()]

    result = calculate_indicators(
        period, open_risks, period_treatments, period_events, None
    )

    # Cache / upsert in risk_indicators
    existing = await db.execute(
        select(RiskIndicator).where(
            RiskIndicator.project_id == project_id,
            RiskIndicator.period == period,
        )
    )
    indicator_row = existing.scalar_one_or_none()
    if indicator_row is None:
        indicator_row = RiskIndicator(
            project_id=project_id,
            period=period,
            pending_critical_high=result.pending_critical_high,
            actions_on_time_pct=result.actions_on_time_pct,
            incidents_count=result.incidents_count,
            normative_status=result.normative_status,
        )
        db.add(indicator_row)
    else:
        indicator_row.pending_critical_high = result.pending_critical_high
        indicator_row.actions_on_time_pct   = result.actions_on_time_pct
        indicator_row.incidents_count        = result.incidents_count
        indicator_row.normative_status       = result.normative_status

    await db.flush()

    return RiskIndicatorOut(
        period=result.period,
        pending_critical_high=result.pending_critical_high,
        actions_on_time_pct=result.actions_on_time_pct,
        incidents_count=result.incidents_count,
        normative_status=result.normative_status,
    )
