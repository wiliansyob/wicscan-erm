import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class CodeSource(BaseModel):
    __tablename__ = "code_sources"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # github | zip
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    github_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    github_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zip_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    local_snapshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    # pending | cloning | ready | error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="code_sources")
    asset: Mapped["Asset | None"] = relationship("Asset", back_populates="code_sources")
    scan_sessions: Mapped[list["ScanSession"]] = relationship(
        "ScanSession", back_populates="code_source", lazy="noload"
    )
