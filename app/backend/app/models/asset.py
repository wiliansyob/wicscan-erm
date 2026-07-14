import uuid
from sqlalchemy import String, Text, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class Asset(BaseModel):
    __tablename__ = "assets"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # api | webapp | repository | database | microservice | infrastructure
    criticality: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)
    # critical | high | medium | low
    technical_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    readme_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="assets")
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="asset", lazy="noload")
    risks: Mapped[list["Risk"]] = relationship("Risk", back_populates="asset", lazy="noload")
    code_sources: Mapped[list["CodeSource"]] = relationship("CodeSource", back_populates="asset", lazy="noload")
