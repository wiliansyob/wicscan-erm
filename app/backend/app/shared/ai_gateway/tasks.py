"""
IA-redactor tasks (F3/F4).

Thin client for the ai-gateway HTTP service.  This module is the only place
in the backend that talks to ai-gateway — keeps the coupling explicit and easy
to swap (e.g. direct SDK call instead of HTTP in a future refactor).

Role: IA-REDACTOR — generates text (descriptions, rationales, suggestions).
It does NOT calculate risk levels; scoring is deterministic (modules/assessment/scoring/).
"""
from __future__ import annotations

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)


async def call_probability_assessment(payload: dict) -> dict:
    """
    POST to ai-gateway /api/v1/analyze/probability and return parsed JSON.

    payload must contain: run_id, project, scenarios, business_context, ai_provider, model.
    Returns: {"results": [{scenario_code, probability, prob_level, probability_rationale},...], "tokens_used": int}
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{settings.AI_GATEWAY_URL}/api/v1/analyze/probability",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def call_risks_from_scenarios(payload: dict) -> dict:
    """
    POST to ai-gateway /api/v1/analyze/risks-from-scenarios.
    payload: run_id, project, scenarios (with P×I already set), business_context.
    Returns: {"risks": [...], "tokens_used": int}
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{settings.AI_GATEWAY_URL}/api/v1/analyze/risks-from-scenarios",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def call_score_scenarios(payload: dict) -> dict:
    """
    POST to ai-gateway /api/v1/analyze/score-scenarios.

    payload must contain: run_id, project, scenario_groups (pre-grouped by backend),
    ai_provider, model, api_key, api_url.
    Returns: {"scenarios": [{group_id, risk_title, probability, impact, ...}], "tokens_used": int}
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(
            f"{settings.AI_GATEWAY_URL}/api/v1/analyze/score-scenarios",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def call_risks_batch(payload: dict) -> dict:
    """
    POST to ai-gateway /api/v1/analyze/risks-batch and return the parsed JSON.

    payload must contain: run_id, project, findings, ai_provider, model,
    api_key, api_url, prompt_template, system_prompt_text.
    Returns: {"risks": [...], "tokens_used": int, "cost_usd": float}
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(
            f"{settings.AI_GATEWAY_URL}/api/v1/analyze/risks-batch",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
