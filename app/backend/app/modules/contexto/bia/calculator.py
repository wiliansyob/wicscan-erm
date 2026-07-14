"""
BIA Calculator — F2.B (§3.2.2.2 del TFM).

Pure function: I(t) = CD(t) + PI(t) + SN

  CD(t): costes directos proporcionales al tiempo
         = (num_staff × avg_salary_hour + infra_cost_per_hour + contractual_penalty_per_hour) × t
  PI(t): pérdida de ingresos
         = hourly_revenue × revenue_dependency_pct × t + sla_at_risk_value
  SN:    sanciones (independiente de t, solo si sn_active=True)

Impact level classification (Tabla 17) by tranche:
  Muy Alto : pct>10% OR sanction>500.000€
  Alto     : pct>5%  OR sanction>50.000€
  Medio    : pct>1%  OR sanction>0
  Bajo     : pct>0%
  Muy Bajo : pct=0

Recovery objectives (defaults from criticality):
  critical  → MTPD=4h,  RTO=2h,  RPO=1h
  important → MTPD=24h, RTO=8h,  RPO=4h
  support   → MTPD=72h, RTO=24h, RPO=8h
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ─── Continuity defaults by criticality ──────────────────────────────────────

_CONTINUITY: dict[str, dict[str, float]] = {
    "critical":  {"mtpd": 4.0,  "rto": 2.0,  "rpo": 1.0},
    "important": {"mtpd": 24.0, "rto": 8.0,  "rpo": 4.0},
    "support":   {"mtpd": 72.0, "rto": 24.0, "rpo": 8.0},
}

# Revenue-dependency band → midpoint fraction
_REVENUE_DEP_PCT: dict[str, float] = {
    "<20":   0.10,
    "20-50": 0.35,
    ">50":   0.65,
}

_TIME_HORIZONS = (2, 8, 24)


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class BiaInput:
    # Staff direct costs
    num_staff_affected: int = 0
    avg_salary_hour: float = 0.0        # €/h per employee

    # Infrastructure direct costs
    infra_cost_per_hour: float = 0.0    # €/h

    # Contractual penalty per hour during outage
    contractual_penalty_per_hour: float = 0.0  # €/h
    # Flat SLA-breach value (added once per tranche, not × t)
    sla_at_risk_value: float = 0.0      # €

    # Revenue loss
    # Gross revenue rate exposed by this process (€/h)
    hourly_revenue: float = 0.0         # €/h
    # Override the revenue_dependency band; if None, derived from revenue_dependency_band
    revenue_dependency_pct: float | None = None
    # Band string: "<20" | "20-50" | ">50" — used when revenue_dependency_pct is None
    revenue_dependency_band: str = "<20"

    # Sanctions (personal-data breach)
    sn_active: bool = False
    sanction_amount: float = 0.0        # €

    # Annual org revenue — needed for impact-level classification
    annual_revenue: float = 0.0         # €/year

    # For continuity-objective defaults
    criticality: str = "important"      # critical|important|support

    # Manual overrides for MTPD/RTO/RPO; None → use criticality defaults
    mtpd_hours: float | None = None
    rto_hours: float | None = None
    rpo_hours: float | None = None


@dataclass
class TrancheResult:
    hours: int
    cd: float
    pi: float
    sn: float
    total: float
    impact_level: str   # Muy Alto | Alto | Medio | Bajo | Muy Bajo


@dataclass
class BiaResult:
    impact_2h: float
    impact_8h: float
    impact_24h: float
    impact_level_2h: str
    impact_level_8h: str
    impact_level_24h: str
    mtpd_hours: float
    rto_hours: float
    rpo_hours: float
    breakdown: dict[str, Any]  # "params" + "2"|"8"|"24" tranche dicts


# ─── Pure calculation ─────────────────────────────────────────────────────────


def _classify_impact(total: float, sn: float, annual_revenue: float) -> str:
    """
    Tabla 17 financial threshold classifier.

    Uses the maximum between the financial-pct classification and
    the sanction-magnitude classification.
    """
    # Financial dimension (pct of annual revenue)
    if annual_revenue > 0:
        pct = (total - sn) / annual_revenue * 100
    else:
        pct = 0.0

    if pct > 10:
        fin_level = "Muy Alto"
    elif pct > 5:
        fin_level = "Alto"
    elif pct > 1:
        fin_level = "Medio"
    elif pct > 0:
        fin_level = "Bajo"
    else:
        fin_level = "Muy Bajo"

    # Sanctions dimension
    if sn > 500_000:
        sn_level = "Muy Alto"
    elif sn > 50_000:
        sn_level = "Alto"
    elif sn > 0:
        sn_level = "Medio"
    else:
        sn_level = "Muy Bajo"

    # Take the worst
    _order = ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]
    return _order[max(_order.index(fin_level), _order.index(sn_level))]


def calculate_bia(inp: BiaInput) -> BiaResult:
    """
    Compute I(t) = CD(t) + PI(t) + SN at t = RPO, RTO, MTPD (dynamic per process).

    The three stored columns (impact_2h, impact_8h, impact_24h) now hold
    I(RPO), I(RTO), I(MTPD) respectively. The actual hours are stored in
    breakdown.params and in the BiaResult fields.
    """
    rdp = inp.revenue_dependency_pct
    if rdp is None:
        rdp = _REVENUE_DEP_PCT.get(inp.revenue_dependency_band, 0.10)

    sn = inp.sanction_amount if inp.sn_active else 0.0

    # Resolve continuity objectives: user override takes precedence over criticality defaults
    cont = _CONTINUITY.get(inp.criticality, _CONTINUITY["important"])
    mtpd = inp.mtpd_hours if inp.mtpd_hours is not None else cont["mtpd"]
    rto  = inp.rto_hours  if inp.rto_hours  is not None else cont["rto"]
    rpo  = inp.rpo_hours  if inp.rpo_hours  is not None else cont["rpo"]

    def _tranche(t: float) -> TrancheResult:
        cd = (
            inp.num_staff_affected * inp.avg_salary_hour * t
            + inp.infra_cost_per_hour * t
            + inp.contractual_penalty_per_hour * t
        )
        pi = inp.hourly_revenue * rdp * t + inp.sla_at_risk_value
        total = cd + pi + sn
        return TrancheResult(
            hours=t,
            cd=round(cd, 2),
            pi=round(pi, 2),
            sn=round(sn, 2),
            total=round(total, 2),
            impact_level=_classify_impact(total, sn, inp.annual_revenue),
        )

    t_rpo  = _tranche(rpo)
    t_rto  = _tranche(rto)
    t_mtpd = _tranche(mtpd)

    # Build breakdown JSON
    params: dict[str, Any] = {
        "num_staff_affected": inp.num_staff_affected,
        "avg_salary_hour": inp.avg_salary_hour,
        "infra_cost_per_hour": inp.infra_cost_per_hour,
        "contractual_penalty_per_hour": inp.contractual_penalty_per_hour,
        "sla_at_risk_value": inp.sla_at_risk_value,
        "hourly_revenue": inp.hourly_revenue,
        "revenue_dependency_pct": rdp,
        "sn_active": inp.sn_active,
        "sanction_amount": inp.sanction_amount,
        "annual_revenue": inp.annual_revenue,
        "criticality": inp.criticality,
        "mtpd_hours": mtpd,
        "rto_hours": rto,
        "rpo_hours": rpo,
    }

    def _tr_dict(tr: TrancheResult) -> dict:
        return {"hours": tr.hours, "cd": tr.cd, "pi": tr.pi, "sn": tr.sn,
                "total": tr.total, "impact_level": tr.impact_level}

    breakdown: dict[str, Any] = {
        "params": params,
        "rpo":  _tr_dict(t_rpo),
        "rto":  _tr_dict(t_rto),
        "mtpd": _tr_dict(t_mtpd),
    }

    # impact_2h/8h/24h columns repurposed: store I(RPO), I(RTO), I(MTPD)
    return BiaResult(
        impact_2h=t_rpo.total,
        impact_8h=t_rto.total,
        impact_24h=t_mtpd.total,
        impact_level_2h=t_rpo.impact_level,
        impact_level_8h=t_rto.impact_level,
        impact_level_24h=t_mtpd.impact_level,
        mtpd_hours=mtpd,
        rto_hours=rto,
        rpo_hours=rpo,
        breakdown=breakdown,
    )
