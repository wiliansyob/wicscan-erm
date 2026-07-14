"""
Admin catalog models — versioned questionnaire definitions.

These tables are managed EXCLUSIVELY by Alembic (not by create_tables.py).
The immutability invariant is enforced at the service layer (versioning.py):
published definitions can never be mutated; only drafts are editable.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class QuestionnaireDefinition(BaseModel):
    __tablename__ = "questionnaire_definitions"

    # version is null while draft; assigned on publish
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class QuestionDefinition(BaseModel):
    __tablename__ = "question_definitions"

    definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questionnaire_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    block: Mapped[str] = mapped_column(String(2), nullable=False)      # A|B|C|D
    question_id: Mapped[str] = mapped_column(String(20), nullable=False)  # "A1","B2a"…
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # single_choice | multi_choice | range | free_text
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # list of option strings
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Normative / BIA field(s) this question directly feeds (list of field names)
    feeds: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("definition_id", "question_id", name="uq_question_in_definition"),
    )


class QuestionDependency(BaseModel):
    __tablename__ = "question_dependencies"

    definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questionnaire_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_question_id: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_value: Mapped[str] = mapped_column(String(100), nullable=False)
    # child_question_id: the question that becomes visible; null if dep only carries an effect
    child_question_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Declarative side-effect, e.g. {"normative": {"ens_applies": true}}
    effect: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DefinitionChangeLog(BaseModel):
    """Immutable audit trail for every action on a questionnaire definition."""

    __tablename__ = "definition_change_log"

    definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questionnaire_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # create | update_question | delete_question | add_dep | remove_dep | publish | archive | clone
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    diff: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # created_at (from BaseModel TimestampMixin) serves as the action timestamp
