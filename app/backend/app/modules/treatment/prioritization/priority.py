"""
Tabla 20 — Prioridad del plan de tratamiento.

action_priority = f(risk_level, effort)

| Nivel         | Esfuerzo bajo | Esfuerzo alto |
|---------------|---------------|---------------|
| Crítico/Alto  |       1       |       2       |
| Medio/Bajo    |       3       |       4       |

Handles both Spanish (new ISO 31000 risks) and English (legacy) risk levels.
"""
from __future__ import annotations

# Normalise legacy English risk levels to Spanish
_NORMALISE: dict[str, str] = {
    "critical": "Crítico", "Crítico": "Crítico",
    "high":     "Alto",    "Alto":    "Alto",
    "medium":   "Medio",   "Medio":   "Medio",
    "low":      "Bajo",    "Bajo":    "Bajo",
}

_PRIORITY_TABLE: dict[tuple[str, str], int] = {
    ("Crítico", "low"): 1, ("Crítico", "high"): 2,
    ("Alto",    "low"): 1, ("Alto",    "high"): 2,
    ("Medio",   "low"): 3, ("Medio",   "high"): 4,
    ("Bajo",    "low"): 3, ("Bajo",    "high"): 4,
}

_PRIORITY_LABELS: dict[int, str] = {
    1: "Tratar de inmediato",
    2: "Planificar con responsable y fecha",
    3: "Planificación ordinaria",
    4: "Evaluar coste vs. riesgo residual",
}


def action_priority_from_table(risk_level: str, effort: str) -> int:
    """Return action priority 1–4 from Tabla 20.

    risk_level accepts Spanish or English values.
    Returns 4 (lowest priority) as fallback for unknown combinations.
    """
    normalised = _NORMALISE.get(risk_level, risk_level)
    return _PRIORITY_TABLE.get((normalised, effort), 4)


def priority_label(action_priority: int) -> str:
    """Return the human-readable label for a priority level (1–4)."""
    return _PRIORITY_LABELS.get(action_priority, "Planificación ordinaria")
