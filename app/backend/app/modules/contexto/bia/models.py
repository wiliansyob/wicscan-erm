from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class BusinessProcess(BaseModel):
    __tablename__ = "procesos_negocio"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    criticality: Mapped[str] = mapped_column(String(20), nullable=False, default="important")
    revenue_dependency: Mapped[str] = mapped_column(String(10), nullable=False, default="<20")
    manual_alternative: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    contractual_commitment: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class BiaEstimate(BaseModel):
    __tablename__ = "estimaciones_bia"

    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procesos_negocio.id", ondelete="CASCADE"), nullable=False,
    )
    impact_2h: Mapped[float | None] = mapped_column(Float, nullable=True)
    impact_8h: Mapped[float | None] = mapped_column(Float, nullable=True)
    impact_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    sn_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mtpd_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    rto_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpo_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AssetProcessLink(BaseModel):
    __tablename__ = "activo_proceso_links"
    __table_args__ = (
        UniqueConstraint("asset_id", "process_id", name="uq_activo_proceso_link"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procesos_negocio.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
