import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, JSON, DateTime, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class ScanSession(BaseModel):
    __tablename__ = "scan_sessions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("code_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    # pending | running | completed | failed | cancelled
    is_retest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    baseline_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_sessions.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scanners_requested: Mapped[list | None] = mapped_column(JSON, nullable=True)
    total_findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved_findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    code_source: Mapped["CodeSource"] = relationship("CodeSource", back_populates="scan_sessions")
    scans: Mapped[list["Scan"]] = relationship("Scan", back_populates="session", lazy="noload")


class Scan(BaseModel):
    __tablename__ = "scans"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scanner_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # sonarqube | semgrep | trivy
    scanner_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    # pending | running | completed | failed | cancelled
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    external_scan_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    session: Mapped["ScanSession"] = relationship("ScanSession", back_populates="scans")
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="scan", lazy="noload")


class RetestComparison(BaseModel):
    __tablename__ = "retest_comparisons"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    baseline_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_sessions.id", ondelete="CASCADE"), nullable=False
    )
    retest_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_sessions.id", ondelete="CASCADE"), nullable=False
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    persisted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    regression_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
