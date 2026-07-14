from __future__ import annotations

import uuid

from sqlalchemy import String, Text, ForeignKey, DateTime, Float, Integer, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class TriggerEvent(BaseModel):
    __tablename__ = "trigger_events"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    # new_critical_vuln | new_system | incident | regulatory_change | new_contract | structural_change
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    review_cycle: Mapped["ReviewCycle | None"] = relationship(
        "ReviewCycle", back_populates="trigger", uselist=False, lazy="noload",
    )


class ReviewCycle(BaseModel):
    __tablename__ = "review_cycles"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    cycle_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # annual | biennial | triggered
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trigger_events.id", ondelete="SET NULL"), nullable=True,
    )
    performed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    # pending | in_progress | completed

    trigger: Mapped["TriggerEvent | None"] = relationship(
        "TriggerEvent", back_populates="review_cycle",
    )


class RiskIndicator(BaseModel):
    __tablename__ = "risk_indicators"
    __table_args__ = (
        UniqueConstraint("project_id", "period", name="uq_indicator_per_project_period"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    # "YYYY-QN", e.g. "2026-Q3"
    pending_critical_high: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actions_on_time_pct: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    incidents_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    normative_status: Mapped[dict | None] = mapped_column(JSON, nullable=True)
