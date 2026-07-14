import uuid
from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class Workspace(BaseModel):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    users: Mapped[list["User"]] = relationship("User", back_populates="workspace", lazy="noload")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="workspace", lazy="noload")
