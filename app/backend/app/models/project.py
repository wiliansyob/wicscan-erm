import uuid
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class Project(BaseModel):
    __tablename__ = "projects"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_appetite: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)
    # low | medium | high
    business_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    # active | archived
    scanner_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_provider_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="projects")
    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="project", lazy="selectin")
    code_sources: Mapped[list["CodeSource"]] = relationship("CodeSource", back_populates="project", lazy="noload")
