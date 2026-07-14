"""
Questionnaire tree validation — runs before publishing a definition.

Rules enforced:
  1. No broken parent references: every parent_question_id in QuestionDependency
     must exist as a question_id in QuestionDefinition for the same definition.
  2. No broken child references: every child_question_id (when not null) must
     exist in QuestionDefinition for the same definition.
  3. No cycles: no question can transitively depend on itself.

All three rules are pure logic once the data is loaded. validate_tree() is
a pure function so it can be called without a DB (e.g. in unit tests).
validate_definition() is the async wrapper that loads data from DB.
"""
from __future__ import annotations

import uuid
from collections import defaultdict, deque

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.catalog.models import QuestionDefinition, QuestionDependency


# ─────────────────────────────────────────────────────────────────────────────
# Pure validation core (no DB — testable in isolation)
# ─────────────────────────────────────────────────────────────────────────────


def validate_tree(
    questions: list[dict],
    dependencies: list[dict],
) -> list[str]:
    """
    Validate a questionnaire tree.

    Args:
        questions: list of dicts with at least {"question_id": str}
        dependencies: list of dicts with
            {"parent_question_id": str, "child_question_id": str | None}

    Returns:
        List of human-readable error strings. Empty list = valid.
    """
    errors: list[str] = []
    q_ids = {q["question_id"] for q in questions}

    for dep in dependencies:
        parent = dep["parent_question_id"]
        child = dep.get("child_question_id")

        if parent not in q_ids:
            errors.append(f"Dependencia referencia pregunta padre inexistente: '{parent}'")
        if child is not None and child not in q_ids:
            errors.append(f"Dependencia referencia pregunta hijo inexistente: '{child}'")

    if not errors:
        # Only check cycles if references are sound
        cycle_err = _find_cycle(q_ids, dependencies)
        if cycle_err:
            errors.append(cycle_err)

    return errors


def _find_cycle(q_ids: set[str], dependencies: list[dict]) -> str | None:
    """Return an error message if the dependency graph has a cycle, else None."""
    graph: dict[str, list[str]] = defaultdict(list)
    for dep in dependencies:
        child = dep.get("child_question_id")
        if child:
            graph[dep["parent_question_id"]].append(child)

    # DFS with three-color marking: 0=white, 1=gray (in stack), 2=black (done)
    color: dict[str, int] = {qid: 0 for qid in q_ids}

    def dfs(node: str) -> bool:
        color[node] = 1
        for neighbour in graph.get(node, []):
            if color.get(neighbour, 0) == 1:
                return True  # back-edge → cycle
            if color.get(neighbour, 0) == 0 and dfs(neighbour):
                return True
        color[node] = 2
        return False

    for qid in q_ids:
        if color[qid] == 0 and dfs(qid):
            return "El árbol de dependencias contiene un ciclo"

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Async wrapper (loads data from DB)
# ─────────────────────────────────────────────────────────────────────────────


async def validate_definition(db: AsyncSession, definition_id: uuid.UUID) -> list[str]:
    """Load questions + dependencies for a definition and validate the tree."""
    q_result = await db.execute(
        select(QuestionDefinition).where(QuestionDefinition.definition_id == definition_id)
    )
    questions = [{"question_id": q.question_id} for q in q_result.scalars().all()]

    d_result = await db.execute(
        select(QuestionDependency).where(QuestionDependency.definition_id == definition_id)
    )
    dependencies = [
        {"parent_question_id": d.parent_question_id, "child_question_id": d.child_question_id}
        for d in d_result.scalars().all()
    ]

    return validate_tree(questions, dependencies)
