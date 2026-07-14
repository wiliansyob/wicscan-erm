"""
Tabla 17 — Nivel de impacto consolidado.

impact_level = max of the four operational dimensions.
"""
from __future__ import annotations

_LEVEL_ORDER: dict[str, int] = {
    "Muy Alto": 4,
    "Alto":     3,
    "Medio":    2,
    "Bajo":     1,
    "Muy Bajo": 0,
}


def impact_level_from_dimensions(
    operational: str,
    financial: str,
    normative: str,
    reputational: str,
) -> str:
    """Return the highest of the four impact dimensions (Tabla 17)."""
    return max(
        (operational, financial, normative, reputational),
        key=lambda x: _LEVEL_ORDER.get(x, 0),
    )
