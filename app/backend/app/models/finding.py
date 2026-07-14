import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, JSON, DateTime, Float, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class Finding(BaseModel):
    __tablename__ = "findings"

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True
    )

    scanner: Mapped[str] = mapped_column(String(50), nullable=False)
    scanner_rule_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    finding_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # vulnerability | code_smell | bug | security_hotspot
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    cwe: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    owasp_category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # critical | high | medium | low | info

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)

    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    component: Mapped[str | None] = mapped_column(String(512), nullable=True)

    effort: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False, index=True)
    # open | confirmed | false_positive | resolved | accepted | wont_fix
    status_changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_deduplicated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="SET NULL"), nullable=True
    )
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    finding_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    scan: Mapped["Scan"] = relationship("Scan", back_populates="findings")
    asset: Mapped["Asset | None"] = relationship("Asset", back_populates="findings")
