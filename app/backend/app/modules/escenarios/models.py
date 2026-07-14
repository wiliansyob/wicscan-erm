from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class RiskScenario(BaseModel):
    __tablename__ = "escenarios"
    __table_args__ = (
        UniqueConstraint("project_id", "group_key", name="uq_escenario_per_project_group"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    scenario_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    consequence: Mapped[str] = mapped_column(String(512), nullable=False)
    group_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True,
    )
    business_process_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procesos_negocio.id", ondelete="SET NULL"), nullable=True,
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    probability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prob_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    probability_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    impact: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    impact_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_operational: Mapped[str | None] = mapped_column(String(20), nullable=True)
    impact_financial: Mapped[str | None] = mapped_column(String(20), nullable=True)
    impact_normative: Mapped[str | None] = mapped_column(String(20), nullable=True)
    impact_reputational: Mapped[str | None] = mapped_column(String(20), nullable=True)

    finding_links: Mapped[list["ScenarioFindingLink"]] = relationship(
        "ScenarioFindingLink", back_populates="scenario",
        cascade="all, delete-orphan", passive_deletes=True, lazy="noload",
    )
    risk: Mapped["Risk | None"] = relationship(  # type: ignore[name-defined]
        "Risk", back_populates="scenario", uselist=False, lazy="noload",
    )


class ScenarioFindingLink(Base):
    __tablename__ = "escenario_hallazgos"

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("escenarios.id", ondelete="CASCADE"), primary_key=True,
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )

    scenario: Mapped["RiskScenario"] = relationship("RiskScenario", back_populates="finding_links")
