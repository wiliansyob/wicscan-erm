from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class QuestionDefinitionIn(BaseModel):
    block: str
    question_id: str
    text: str
    type: str
    options: list[str] | None = None
    order: int = 0
    feeds: list[str] | None = None


class QuestionDependencyIn(BaseModel):
    parent_question_id: str
    trigger_value: str
    child_question_id: str | None = None
    effect: dict | None = None


class DefinitionCreateIn(BaseModel):
    notes: str | None = None


class QuestionDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    definition_id: uuid.UUID
    block: str
    question_id: str
    text: str
    type: str
    options: Any | None
    order: int
    feeds: Any | None


class QuestionDependencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    definition_id: uuid.UUID
    parent_question_id: str
    trigger_value: str
    child_question_id: str | None
    effect: Any | None


class DefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int | None
    status: str
    published_at: datetime | None
    notes: str | None
    created_at: datetime
    questions: list[QuestionDefinitionOut] = []
    dependencies: list[QuestionDependencyOut] = []


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str]


class PublishResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    status: str
    published_at: datetime
