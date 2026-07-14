"""
Questionnaire definition lifecycle (copy-on-publish).

Lifecycle:
  create_draft()  →  draft
  add/edit questions & deps on the draft
  publish()       →  published (immutable, version assigned)
  archive()       →  archived

  To revise: clone_latest_published() → new draft → edit → publish → new version

Invariant: answered questionnaires always point to the definition_id they
were created with. Publishing a new version never touches existing answers.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.catalog.models import (
    DefinitionChangeLog,
    QuestionDefinition,
    QuestionDependency,
    QuestionnaireDefinition,
)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _log(
    db: AsyncSession,
    definition_id: uuid.UUID,
    user_id: uuid.UUID | None,
    action: str,
    diff: dict | None = None,
) -> None:
    entry = DefinitionChangeLog(
        definition_id=definition_id,
        user_id=user_id,
        action=action,
        diff=diff or {},
    )
    db.add(entry)


async def _get_definition_or_raise(db: AsyncSession, definition_id: uuid.UUID) -> QuestionnaireDefinition:
    defn = await db.get(QuestionnaireDefinition, definition_id)
    if defn is None:
        raise ValueError(f"QuestionnaireDefinition {definition_id} not found")
    return defn


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


async def create_draft(
    db: AsyncSession,
    notes: str | None = None,
    user_id: uuid.UUID | None = None,
) -> QuestionnaireDefinition:
    """Create a new empty draft."""
    defn = QuestionnaireDefinition(status="draft", notes=notes)
    db.add(defn)
    await db.flush()
    _log(db, defn.id, user_id, "create")
    return defn


async def clone_latest_published(
    db: AsyncSession,
    user_id: uuid.UUID | None = None,
) -> QuestionnaireDefinition:
    """Clone the latest published definition into a new draft."""
    result = await db.execute(
        select(QuestionnaireDefinition)
        .where(QuestionnaireDefinition.status == "published")
        .order_by(QuestionnaireDefinition.version.desc())
        .limit(1)
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise ValueError("No published definition found to clone")

    new_defn = QuestionnaireDefinition(
        status="draft",
        notes=f"Clonado de v{source.version}",
    )
    db.add(new_defn)
    await db.flush()

    q_result = await db.execute(
        select(QuestionDefinition).where(QuestionDefinition.definition_id == source.id)
    )
    for q in q_result.scalars().all():
        db.add(QuestionDefinition(
            definition_id=new_defn.id,
            block=q.block,
            question_id=q.question_id,
            text=q.text,
            type=q.type,
            options=q.options,
            order=q.order,
            feeds=q.feeds,
        ))

    d_result = await db.execute(
        select(QuestionDependency).where(QuestionDependency.definition_id == source.id)
    )
    for d in d_result.scalars().all():
        db.add(QuestionDependency(
            definition_id=new_defn.id,
            parent_question_id=d.parent_question_id,
            trigger_value=d.trigger_value,
            child_question_id=d.child_question_id,
            effect=d.effect,
        ))

    await db.flush()
    _log(db, new_defn.id, user_id, "clone", {"source_id": str(source.id), "source_version": source.version})
    return new_defn


async def publish(
    db: AsyncSession,
    definition_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> QuestionnaireDefinition:
    """
    Validate and publish a draft.
    Raises ValueError if not a draft or tree is invalid.
    """
    from app.modules.admin.catalog.validation import validate_definition

    defn = await _get_definition_or_raise(db, definition_id)
    if defn.status != "draft":
        raise ValueError(f"Solo se pueden publicar borradores. Estado actual: {defn.status}")

    errors = await validate_definition(db, definition_id)
    if errors:
        raise ValueError("Árbol de preguntas inválido: " + "; ".join(errors))

    result = await db.execute(
        select(func.max(QuestionnaireDefinition.version))
        .where(QuestionnaireDefinition.status == "published")
    )
    max_version = result.scalar() or 0

    defn.status = "published"
    defn.version = max_version + 1
    defn.published_at = datetime.now(timezone.utc)
    await db.flush()
    _log(db, defn.id, user_id, "publish", {"version": defn.version})
    return defn


async def archive(
    db: AsyncSession,
    definition_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> QuestionnaireDefinition:
    """Archive a published definition (cannot be used for new questionnaires)."""
    defn = await _get_definition_or_raise(db, definition_id)
    if defn.status not in ("published",):
        raise ValueError(f"Solo se pueden archivar definiciones publicadas. Estado actual: {defn.status}")

    defn.status = "archived"
    await db.flush()
    _log(db, defn.id, user_id, "archive")
    return defn


async def upsert_question(
    db: AsyncSession,
    definition_id: uuid.UUID,
    question_id: str,
    block: str,
    text: str,
    q_type: str,
    options: list | None,
    order: int,
    feeds: list | None,
    user_id: uuid.UUID | None = None,
) -> QuestionDefinition:
    """Add or update a question on a draft. Raises if definition is not a draft."""
    defn = await _get_definition_or_raise(db, definition_id)
    if defn.status != "draft":
        raise ValueError("Solo se pueden editar borradores")

    from sqlalchemy import and_
    result = await db.execute(
        select(QuestionDefinition).where(
            and_(
                QuestionDefinition.definition_id == definition_id,
                QuestionDefinition.question_id == question_id,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.block = block
        existing.text = text
        existing.type = q_type
        existing.options = options
        existing.order = order
        existing.feeds = feeds
        q = existing
        action = "update_question"
    else:
        q = QuestionDefinition(
            definition_id=definition_id,
            block=block,
            question_id=question_id,
            text=text,
            type=q_type,
            options=options,
            order=order,
            feeds=feeds,
        )
        db.add(q)
        action = "add_question"

    await db.flush()
    _log(db, definition_id, user_id, action, {"question_id": question_id})
    return q


async def delete_question(
    db: AsyncSession,
    definition_id: uuid.UUID,
    question_id: str,
    user_id: uuid.UUID | None = None,
) -> None:
    """Remove a question (and any dependencies referencing it) from a draft."""
    defn = await _get_definition_or_raise(db, definition_id)
    if defn.status != "draft":
        raise ValueError("Solo se pueden editar borradores")

    from sqlalchemy import and_, or_
    result = await db.execute(
        select(QuestionDefinition).where(
            and_(
                QuestionDefinition.definition_id == definition_id,
                QuestionDefinition.question_id == question_id,
            )
        )
    )
    q = result.scalar_one_or_none()
    if q:
        await db.delete(q)

    # Cascade: remove deps that reference this question
    dep_result = await db.execute(
        select(QuestionDependency).where(
            and_(
                QuestionDependency.definition_id == definition_id,
                or_(
                    QuestionDependency.parent_question_id == question_id,
                    QuestionDependency.child_question_id == question_id,
                ),
            )
        )
    )
    for dep in dep_result.scalars().all():
        await db.delete(dep)

    await db.flush()
    _log(db, definition_id, user_id, "delete_question", {"question_id": question_id})


async def add_dependency(
    db: AsyncSession,
    definition_id: uuid.UUID,
    parent_question_id: str,
    trigger_value: str,
    child_question_id: str | None,
    effect: dict | None,
    user_id: uuid.UUID | None = None,
) -> QuestionDependency:
    defn = await _get_definition_or_raise(db, definition_id)
    if defn.status != "draft":
        raise ValueError("Solo se pueden editar borradores")

    dep = QuestionDependency(
        definition_id=definition_id,
        parent_question_id=parent_question_id,
        trigger_value=trigger_value,
        child_question_id=child_question_id,
        effect=effect,
    )
    db.add(dep)
    await db.flush()
    _log(db, definition_id, user_id, "add_dep", {
        "parent": parent_question_id, "trigger": trigger_value, "child": child_question_id,
    })
    return dep


async def remove_dependency(
    db: AsyncSession,
    definition_id: uuid.UUID,
    dep_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> None:
    defn = await _get_definition_or_raise(db, definition_id)
    if defn.status != "draft":
        raise ValueError("Solo se pueden editar borradores")

    dep = await db.get(QuestionDependency, dep_id)
    if dep and dep.definition_id == definition_id:
        await db.delete(dep)
        await db.flush()
        _log(db, definition_id, user_id, "remove_dep", {"dep_id": str(dep_id)})
