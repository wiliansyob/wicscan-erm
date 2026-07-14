"""
F4 indicator calculator — §3.4.3.

Pure function — no DB, fully testable.

The four indicators (calculated per quarter):
  1. pending_critical_high  — open risks at Crítico or Alto
  2. actions_on_time_pct    — % of due treatments completed on time
  3. incidents_count        — incident-type trigger events in the period
  4. normative_status       — active regulations summary (from NormativeProfile)
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timezone


# ─── period helpers ──────────────────────────────────────────────────────────

def parse_period_range(period: str) -> tuple[datetime, datetime]:
    """Parse 'YYYY-QN' into (start, end) UTC datetimes.

    Raises ValueError for invalid format.
    """
    try:
        year_str, q_str = period.split("-Q")
        year = int(year_str)
        q = int(q_str)
        if q not in (1, 2, 3, 4):
            raise ValueError(f"Quarter must be 1–4, got {q}")
    except (AttributeError, ValueError) as exc:
        raise ValueError(
            f"Invalid period {period!r}. Expected format: YYYY-QN (e.g. 2026-Q3)"
        ) from exc

    _START_MONTH = {1: 1, 2: 4, 3: 7, 4: 10}
    _END_MONTH   = {1: 3, 2: 6, 3: 9, 4: 12}
    s_month = _START_MONTH[q]
    e_month = _END_MONTH[q]
    e_day   = calendar.monthrange(year, e_month)[1]
    start = datetime(year, s_month, 1, 0, 0, 0, tzinfo=timezone.utc)
    end   = datetime(year, e_month, e_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def current_period() -> str:
    """Return the current quarter as 'YYYY-QN'."""
    now = datetime.now(tz=timezone.utc)
    q = (now.month - 1) // 3 + 1
    return f"{now.year}-Q{q}"


# ─── normative status helper ─────────────────────────────────────────────────

def _build_normative_status(normative: dict | None) -> dict:
    if not normative:
        return {}
    status: dict[str, str] = {}
    if normative.get("rgpd_applies"):
        status["RGPD"] = "active"
    nis2 = normative.get("nis2_status") or "none"
    if nis2 != "none":
        status["NIS2"] = nis2
    if normative.get("ens_applies"):
        status["ENS"] = normative.get("ens_level") or "basic"
    dora = normative.get("dora_status") or "none"
    if dora != "none":
        status["DORA"] = dora
    return status


# ─── pure calculation ─────────────────────────────────────────────────────────

@dataclass
class IndicatorResult:
    period: str
    pending_critical_high: int
    actions_on_time_pct: float
    incidents_count: int
    normative_status: dict


def calculate_indicators(
    period: str,
    open_risks: list[dict],
    period_treatments: list[dict],
    period_events: list[dict],
    normative_profile: dict | None,
) -> IndicatorResult:
    """Calculate the four ISO 31000 §3.4.3 indicators.

    Args:
        period:             Quarter string, e.g. "2026-Q3".
        open_risks:         All risks for the project; each dict needs
                            {risk_level: str, status: str}.
        period_treatments:  RiskTreatments whose due_date falls in period;
                            each dict needs {status, completed_at, due_date}.
        period_events:      TriggerEvents detected in period; each needs
                            {event_type: str}.
        normative_profile:  NormativeProfile as dict (or None).

    Returns:
        IndicatorResult dataclass.
    """
    # 1. Pending critical / high risks
    critical_high = {"Crítico", "Alto", "critical", "high"}
    pending = sum(
        1 for r in open_risks
        if r.get("status") == "open"
        and r.get("risk_level", "") in critical_high
    )

    # 2. Actions on time %
    total = len(period_treatments)
    if total == 0:
        on_time_pct = 100.0
    else:
        on_time = 0
        for t in period_treatments:
            if t.get("status") == "completed":
                due     = t.get("due_date")
                done_at = t.get("completed_at")
                if due is not None and done_at is not None and done_at <= due:
                    on_time += 1
        on_time_pct = round(on_time / total * 100, 1)

    # 3. Incidents in period
    incidents = sum(
        1 for e in period_events if e.get("event_type") == "incident"
    )

    # 4. Normative status
    norm_status = _build_normative_status(normative_profile)

    return IndicatorResult(
        period=period,
        pending_critical_high=pending,
        actions_on_time_pct=on_time_pct,
        incidents_count=incidents,
        normative_status=norm_status,
    )
