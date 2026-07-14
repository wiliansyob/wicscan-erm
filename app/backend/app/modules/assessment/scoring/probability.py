"""
Tabla 16 — Probabilidad del escenario de riesgo.

Ordered lookup: first matching rule wins.
None is a wildcard matching any factor value.
"""
from __future__ import annotations

_ANY = None

# (access_vector, complexity, privileges, exploit_evidence) → probability
_PROB_TABLE: list[tuple[str | None, str | None, str | None, str | None, str]] = [
    # Row 1: Internet, sin condiciones, sin privilegios, explotación activa → Muy Alta
    ("internet", "ninguna", "ninguno", "activa", "Muy Alta"),
    # Row 2: Internet, sin condiciones, sin privilegios, exploit público → Alta
    ("internet", "ninguna", "ninguno", "publico", "Alta"),
    # Row 2b: Internet, sin condiciones, sin privilegios, técnica documentada → Alta
    ("internet", "ninguna", "ninguno", "documentada", "Alta"),
    # Row 3: Internet, moderada, sin privilegios/básico, cualquiera → Alta
    ("internet", "moderada", "ninguno", _ANY, "Alta"),
    ("internet", "moderada", "basico",  _ANY, "Alta"),
    # Row 4: Red interna, sin condiciones, sin privilegios, cualquiera → Alta
    ("red_interna", "ninguna", "ninguno", _ANY, "Alta"),
    # Row 10 (placed here to take priority over Row 5):
    # Cualquiera, muy específica (alta), privilegiado, sin precedente → Muy Baja
    # Must precede Row 5 so that internet+alta+privilegiado+sin_precedente resolves to Muy Baja,
    # not Media — attack requires high complexity + privileged access + no known exploit.
    (_ANY, "alta", "privilegiado", "sin_precedente", "Muy Baja"),
    # Row 5: Internet, cualquiera, privilegiado, cualquiera → Media
    ("internet", _ANY, "privilegiado", _ANY, "Media"),
    # Row 6: Red interna, moderada, sin privilegios/básico, documentada → Media
    ("red_interna", "moderada", "ninguno", "documentada", "Media"),
    ("red_interna", "moderada", "basico",  "documentada", "Media"),
    # Row 7: Red interna, cualquiera, cualquiera, sin precedente → Baja
    ("red_interna", _ANY, _ANY, "sin_precedente", "Baja"),
    # Row 8: Acceso físico, sin condiciones, sin privilegios, activa → Baja
    ("acceso_fisico", "ninguna", "ninguno", "activa", "Baja"),
    # Row 9: Acceso físico, moderada o alta, cualquiera, cualquiera → Muy Baja
    ("acceso_fisico", "moderada", _ANY, _ANY, "Muy Baja"),
    ("acceso_fisico", "alta",     _ANY, _ANY, "Muy Baja"),
    # Fallbacks by access vector (cover unmatched combinations)
    ("acceso_fisico", _ANY, _ANY, _ANY, "Muy Baja"),
    ("red_interna",   _ANY, _ANY, _ANY, "Baja"),
    ("internet",      _ANY, _ANY, _ANY, "Media"),
]


def lookup_probability(
    access_vector: str,
    complexity: str,
    privileges: str,
    exploit_evidence: str,
) -> str:
    """Return the probability level for the given factor combination (Tabla 16).

    First matching row wins; None entries in the table act as wildcards.
    """
    for av, ac, pr, ev, result in _PROB_TABLE:
        if (
            (av is None or av == access_vector)
            and (ac is None or ac == complexity)
            and (pr is None or pr == privileges)
            and (ev is None or ev == exploit_evidence)
        ):
            return result
    return "Media"
