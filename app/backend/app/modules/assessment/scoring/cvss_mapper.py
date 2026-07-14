"""
Map a CVSS 3.x vector string to ISO 31000 probability factors.

AV mapping:
  N (Network)   → internet
  A (Adjacent)  → red_interna
  L (Local)     → red_interna
  P (Physical)  → acceso_fisico

AC mapping (CVSS 3.x has only L/H; "alta" must be set manually):
  L (Low)  → ninguna
  H (High) → moderada

PR mapping:
  N (None)  → ninguno
  L (Low)   → basico
  H (High)  → privilegiado

E (Exploit Code Maturity — Temporal, optional):
  X / U → sin_precedente
  P     → documentada
  F     → publico
  H     → activa
  (absent in base-only vector) → sin_precedente
"""
from __future__ import annotations

_AV_MAP: dict[str, str] = {
    "N": "internet",
    "A": "red_interna",
    "L": "red_interna",
    "P": "acceso_fisico",
}
_AC_MAP: dict[str, str] = {
    "L": "ninguna",
    "H": "moderada",
}
_PR_MAP: dict[str, str] = {
    "N": "ninguno",
    "L": "basico",
    "H": "privilegiado",
}
_E_MAP: dict[str, str] = {
    "X": "sin_precedente",
    "U": "sin_precedente",
    "P": "documentada",
    "F": "publico",
    "H": "activa",
}


def factors_from_cvss(cvss_vector: str) -> dict[str, str]:
    """Parse a CVSS 3.x vector string and return ISO 31000 factor values.

    Returns dict with keys: access_vector, complexity, privileges, exploit_evidence.
    Raises ValueError on unrecognised vector format or unknown metric values.
    """
    if "/" not in cvss_vector:
        raise ValueError(f"Unrecognised CVSS vector: {cvss_vector!r}")

    parts = cvss_vector.split("/")
    if parts[0].startswith("CVSS:"):
        parts = parts[1:]

    metrics: dict[str, str] = {}
    for part in parts:
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        metrics[key] = val

    av = metrics.get("AV")
    ac = metrics.get("AC")
    pr = metrics.get("PR")
    e  = metrics.get("E", "X")

    if av not in _AV_MAP:
        raise ValueError(f"Unknown AV value: {av!r}")
    if ac not in _AC_MAP:
        raise ValueError(f"Unknown AC value: {ac!r}")
    if pr not in _PR_MAP:
        raise ValueError(f"Unknown PR value: {pr!r}")
    if e not in _E_MAP:
        raise ValueError(f"Unknown E value: {e!r}")

    return {
        "access_vector":    _AV_MAP[av],
        "complexity":       _AC_MAP[ac],
        "privileges":       _PR_MAP[pr],
        "exploit_evidence": _E_MAP[e],
    }
