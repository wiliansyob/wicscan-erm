"""
Admin catalog router — questionnaire definition CRUD + lifecycle.

Endpoints (plan §6):
  POST   /admin/questionnaire-definitions              ← create draft or clone latest published
  GET    /admin/questionnaire-definitions              ← list all
  GET    /admin/questionnaire-definitions/{id}         ← detail with questions+deps
  PUT    /admin/questionnaire-definitions/{id}/questions/{qid}
  DELETE /admin/questionnaire-definitions/{id}/questions/{qid}
  POST   /admin/questionnaire-definitions/{id}/dependencies
  DELETE /admin/questionnaire-definitions/{id}/dependencies/{dep_id}
  POST   /admin/questionnaire-definitions/{id}/validate
  POST   /admin/questionnaire-definitions/{id}/publish
  POST   /admin/questionnaire-definitions/{id}/archive
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.modules.admin.catalog.models import (
    QuestionDefinition,
    QuestionDependency,
    QuestionnaireDefinition,
)
from app.modules.admin.catalog import versioning, validation
from app.modules.admin.catalog.schemas import (
    DefinitionCreateIn,
    DefinitionOut,
    PublishResult,
    QuestionDefinitionIn,
    QuestionDefinitionOut,
    QuestionDependencyIn,
    QuestionDependencyOut,
    ValidationResult,
)

router = APIRouter(prefix="/admin/questionnaire-definitions", tags=["admin-catalog"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ─────────────────────────────────────────────────────────────────────────────
# Definitions
# ─────────────────────────────────────────────────────────────────────────────


@router.post("", response_model=DefinitionOut, status_code=201)
async def create_definition(
    payload: DefinitionCreateIn,
    db: DB,
    current_user: CurrentUser,
):
    """Create an empty draft. If a published definition exists, clone it instead."""
    result = await db.execute(
        select(QuestionnaireDefinition)
        .where(QuestionnaireDefinition.status == "published")
        .limit(1)
    )
    if result.scalar_one_or_none():
        defn = await versioning.clone_latest_published(db, user_id=current_user.id)
        if payload.notes:
            defn.notes = payload.notes
    else:
        defn = await versioning.create_draft(db, notes=payload.notes, user_id=current_user.id)

    questions, deps = await _load_defn_detail(db, defn.id)
    return _build_definition_out(defn, questions, deps)


@router.get("", response_model=list[DefinitionOut])
async def list_definitions(db: DB, current_user: CurrentUser):
    result = await db.execute(
        select(QuestionnaireDefinition).order_by(QuestionnaireDefinition.created_at.desc())
    )
    defns = result.scalars().all()
    out = []
    for defn in defns:
        questions, deps = await _load_defn_detail(db, defn.id)
        out.append(_build_definition_out(defn, questions, deps))
    return out


@router.get("/{definition_id}", response_model=DefinitionOut)
async def get_definition(definition_id: uuid.UUID, db: DB, current_user: CurrentUser):
    defn = await db.get(QuestionnaireDefinition, definition_id)
    if not defn:
        raise HTTPException(status_code=404, detail="Definición no encontrada")
    questions, deps = await _load_defn_detail(db, defn.id)
    return _build_definition_out(defn, questions, deps)


# ─────────────────────────────────────────────────────────────────────────────
# Questions
# ─────────────────────────────────────────────────────────────────────────────


@router.put("/{definition_id}/questions/{question_id}", response_model=QuestionDefinitionOut)
async def upsert_question(
    definition_id: uuid.UUID,
    question_id: str,
    payload: QuestionDefinitionIn,
    db: DB,
    current_user: CurrentUser,
):
    try:
        q = await versioning.upsert_question(
            db, definition_id, question_id,
            block=payload.block,
            text=payload.text,
            q_type=payload.type,
            options=payload.options,
            order=payload.order,
            feeds=payload.feeds,
            user_id=current_user.id,
        )
        return QuestionDefinitionOut.model_validate(q)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{definition_id}", status_code=204)
async def delete_definition(
    definition_id: uuid.UUID,
    db: DB,
    _current_user: CurrentUser,
):
    """Delete a draft definition. Published and archived definitions cannot be deleted."""
    defn = await db.get(QuestionnaireDefinition, definition_id)
    if not defn:
        raise HTTPException(status_code=404, detail="Definición no encontrada")
    if defn.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden eliminar borradores. Archiva primero la definición si está publicada.",
        )
    await db.delete(defn)
    await db.commit()


@router.delete("/{definition_id}/questions/{question_id}", status_code=204)
async def delete_question(
    definition_id: uuid.UUID,
    question_id: str,
    db: DB,
    current_user: CurrentUser,
):
    try:
        await versioning.delete_question(db, definition_id, question_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Dependencies
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/{definition_id}/dependencies", response_model=QuestionDependencyOut, status_code=201)
async def add_dependency(
    definition_id: uuid.UUID,
    payload: QuestionDependencyIn,
    db: DB,
    current_user: CurrentUser,
):
    try:
        dep = await versioning.add_dependency(
            db, definition_id,
            parent_question_id=payload.parent_question_id,
            trigger_value=payload.trigger_value,
            child_question_id=payload.child_question_id,
            effect=payload.effect,
            user_id=current_user.id,
        )
        return QuestionDependencyOut.model_validate(dep)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{definition_id}/dependencies/{dep_id}", status_code=204)
async def remove_dependency(
    definition_id: uuid.UUID,
    dep_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    try:
        await versioning.remove_dependency(db, definition_id, dep_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/{definition_id}/validate", response_model=ValidationResult)
async def validate_definition(
    definition_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    errors = await validation.validate_definition(db, definition_id)
    return ValidationResult(valid=len(errors) == 0, errors=errors)


@router.post("/{definition_id}/publish", response_model=PublishResult)
async def publish_definition(
    definition_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    try:
        defn = await versioning.publish(db, definition_id, user_id=current_user.id)
        return PublishResult.model_validate(defn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{definition_id}/archive", response_model=DefinitionOut)
async def archive_definition(
    definition_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    try:
        defn = await versioning.archive(db, definition_id, user_id=current_user.id)
        questions, deps = await _load_defn_detail(db, defn.id)
        return _build_definition_out(defn, questions, deps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


async def _load_defn_detail(
    db: AsyncSession, definition_id: uuid.UUID
) -> tuple[list[QuestionDefinition], list[QuestionDependency]]:
    q_result = await db.execute(
        select(QuestionDefinition)
        .where(QuestionDefinition.definition_id == definition_id)
        .order_by(QuestionDefinition.block, QuestionDefinition.order)
    )
    d_result = await db.execute(
        select(QuestionDependency).where(QuestionDependency.definition_id == definition_id)
    )
    return q_result.scalars().all(), d_result.scalars().all()


def _build_definition_out(
    defn: QuestionnaireDefinition,
    questions: list[QuestionDefinition],
    deps: list[QuestionDependency],
) -> DefinitionOut:
    return DefinitionOut(
        id=defn.id,
        version=defn.version,
        status=defn.status,
        published_at=defn.published_at,
        notes=defn.notes,
        created_at=defn.created_at,
        questions=[QuestionDefinitionOut.model_validate(q) for q in questions],
        dependencies=[QuestionDependencyOut.model_validate(d) for d in deps],
    )
