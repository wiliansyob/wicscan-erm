import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, JSON, DateTime, Float, Integer, Table, Column, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseModel

# Ensure RiskScenario is registered before Risk
from app.modules.escenarios.models import RiskScenario  # noqa: F401

# Many-to-many: Risk <-> Finding
risk_finding_links = Table(
    "risk_finding_links",
    Base.metadata,
    Column("risk_id", UUID(as_uuid=True), ForeignKey("riesgos.id", ondelete="CASCADE"), primary_key=True),
    Column("finding_id", UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True),
    Column("is_primary", Boolean, default=False),
)


class Risk(BaseModel):
    __tablename__ = "riesgos"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    business_process_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procesos_negocio.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("escenarios.id", ondelete="SET NULL"), nullable=True, index=True
    )

    risk_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    risk_title: Mapped[str] = mapped_column(String(512), nullable=False)
    risk_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_impact_operational: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_impact_financial: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_impact_normative: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_impact_reputational: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_category: Mapped[str] = mapped_column(String(50), default="security", nullable=False)

    probability: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    impact: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    likelihood_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_cia: Mapped[list | None] = mapped_column(JSON, nullable=True)

    methodology: Mapped[str] = mapped_column(String(50), default="iso_31000", nullable=False)
    assessed_by: Mapped[str] = mapped_column(String(50), default="ai", nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False, index=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    residual_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_level: Mapped[str | None] = mapped_column(String(50), nullable=True)

    prob_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    impact_operational: Mapped[str | None] = mapped_column(String(20), nullable=True)
    impact_financial: Mapped[str | None] = mapped_column(String(20), nullable=True)
    impact_normative: Mapped[str | None] = mapped_column(String(20), nullable=True)
    impact_reputational: Mapped[str | None] = mapped_column(String(20), nullable=True)
    impact_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    asset: Mapped["Asset | None"] = relationship("Asset", back_populates="risks")  # type: ignore[name-defined]
    scenario: Mapped["RiskScenario | None"] = relationship(
        "RiskScenario", back_populates="risk", lazy="noload"
    )
    treatments: Mapped[list["RiskTreatment"]] = relationship(
        "RiskTreatment", back_populates="risk", lazy="selectin",
        cascade="all, delete-orphan", passive_deletes=True
    )
    findings: Mapped[list["Finding"]] = relationship(  # type: ignore[name-defined]
        "Finding", secondary="risk_finding_links", lazy="noload"
    )

    @property
    def finding_ids(self) -> list[uuid.UUID]:
        return [f.id for f in self.findings] if self.findings else []


class RiskTreatment(BaseModel):
    __tablename__ = "tratamientos"

    risk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("riesgos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    treatment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str] = mapped_column(String(50), default="medium_term", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="planned", nullable=False, index=True)
    acceptance_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_risk_reduction: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effort: Mapped[str | None] = mapped_column(String(10), nullable=True)
    action_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verification: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk: Mapped["Risk"] = relationship("Risk", back_populates="treatments")
