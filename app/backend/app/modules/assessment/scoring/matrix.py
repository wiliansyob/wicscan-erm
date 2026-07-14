"""
Tabla 18 — Matriz de riesgo 5 × 5 (determinista).

(probability_level, impact_level) → risk_level
"""
from __future__ import annotations

MATRIX: dict[tuple[str, str], str] = {
    ("Muy Alta", "Muy Bajo"): "Medio",
    ("Muy Alta", "Bajo"):     "Alto",
    ("Muy Alta", "Medio"):    "Alto",
    ("Muy Alta", "Alto"):     "Crítico",
    ("Muy Alta", "Muy Alto"): "Crítico",

    ("Alta", "Muy Bajo"):     "Bajo",
    ("Alta", "Bajo"):         "Medio",
    ("Alta", "Medio"):        "Alto",
    ("Alta", "Alto"):         "Alto",
    ("Alta", "Muy Alto"):     "Crítico",

    ("Media", "Muy Bajo"):    "Bajo",
    ("Media", "Bajo"):        "Medio",
    ("Media", "Medio"):       "Medio",
    ("Media", "Alto"):        "Alto",
    ("Media", "Muy Alto"):    "Alto",

    ("Baja", "Muy Bajo"):     "Bajo",
    ("Baja", "Bajo"):         "Bajo",
    ("Baja", "Medio"):        "Medio",
    ("Baja", "Alto"):         "Medio",
    ("Baja", "Muy Alto"):     "Medio",

    ("Muy Baja", "Muy Bajo"): "Bajo",
    ("Muy Baja", "Bajo"):     "Bajo",
    ("Muy Baja", "Medio"):    "Bajo",
    ("Muy Baja", "Alto"):     "Bajo",
    ("Muy Baja", "Muy Alto"): "Medio",
}


def risk_level_from_matrix(probability_level: str, impact_level: str) -> str:
    """Return the risk level from the deterministic 5×5 matrix (Tabla 18)."""
    return MATRIX.get((probability_level, impact_level), "Medio")
