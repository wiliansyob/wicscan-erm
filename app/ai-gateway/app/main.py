"""
AI Gateway — multi-provider LLM abstraction for risk analysis.

Provider selection priority:
  1. Per-request override (payload.provider)
  2. Environment DEFAULT_PROVIDER
  3. Auto-fallback: try each provider in order until one succeeds

Endpoints:
  POST /api/v1/analyze/risk       — analyze a finding for risk assessment
  POST /api/v1/analyze/executive  — executive summary for a project
  GET  /api/v1/providers          — list available providers
"""

import json
import re
from contextlib import asynccontextmanager
from typing import Literal

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel

from app.config import get_settings
from app.prompts.risk_prompts import (
    RISK_ANALYSIS_SYSTEM_PROMPT,
    GROUPED_RISK_SYSTEM_PROMPT,
    PROBABILITY_ASSESSMENT_SYSTEM_PROMPT,
    RISKS_FROM_SCENARIOS_SYSTEM_PROMPT,
    EXECUTIVE_SUMMARY_SYSTEM_PROMPT,
    TREATMENT_PLAN_SYSTEM_PROMPT,
    SCENARIOS_SCORING_SYSTEM_PROMPT,
    build_risk_analysis_prompt,
    build_grouped_risk_prompt,
    build_probability_prompt,
    build_risks_from_scenarios_prompt,
    build_executive_summary_prompt,
    build_treatment_plan_prompt,
    build_scenarios_scoring_prompt,
    PROMPTS_MAP,
)
from app.providers.base import BaseProvider, LLMResponse

log = structlog.get_logger(__name__)
settings = get_settings()

_providers: dict[str, BaseProvider] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _initialize_providers()
    log.info("ai_gateway_startup", default_provider=settings.DEFAULT_PROVIDER)
    yield
    log.info("ai_gateway_shutdown")


async def _initialize_providers():
    from app.providers.ollama_provider import OllamaProvider
    from app.providers.openai_provider import OpenAIProvider
    from app.providers.anthropic_provider import AnthropicProvider
    from app.providers.gemini_provider import GeminiProvider

    # Always register Ollama (local, no key required)
    ollama = OllamaProvider(base_url=settings.OLLAMA_URL, model=settings.OLLAMA_MODEL)
    _providers["ollama"] = ollama

    # Pull model in background (non-blocking)
    try:
        await ollama.ensure_model_pulled()
        log.info("ollama_model_ready", model=settings.OLLAMA_MODEL)
    except Exception as exc:
        log.warning("ollama_model_pull_failed", error=str(exc))

    if settings.OPENAI_API_KEY:
        _providers["openai"] = OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
        log.info("provider_registered", provider="openai")

    if settings.ANTHROPIC_API_KEY:
        _providers["anthropic"] = AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY, model=settings.ANTHROPIC_MODEL)
        log.info("provider_registered", provider="anthropic")

    if settings.GEMINI_API_KEY:
        _providers["gemini"] = GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
        log.info("provider_registered", provider="gemini")


app = FastAPI(
    title=settings.APP_NAME,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)


def _get_provider(preferred: str | None = None, api_key: str | None = None, api_url: str | None = None, model: str | None = None) -> BaseProvider:
    target = preferred or settings.DEFAULT_PROVIDER
    
    # If dynamic key provided, create ephemeral provider
    if api_key and target in ["openai", "anthropic", "gemini"]:
        from app.providers.openai_provider import OpenAIProvider
        from app.providers.anthropic_provider import AnthropicProvider
        from app.providers.gemini_provider import GeminiProvider
        if target == "openai":
            return OpenAIProvider(api_key=api_key, model=model or settings.OPENAI_MODEL, base_url=api_url)
        elif target == "anthropic":
            return AnthropicProvider(api_key=api_key, model=model or settings.ANTHROPIC_MODEL, base_url=api_url)
        elif target == "gemini":
            return GeminiProvider(api_key=api_key, model=model or settings.GEMINI_MODEL, base_url=api_url)
            
    # If custom OpenAI-compatible provider
    if api_key and target.startswith("custom_"):
        from app.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=model or "unknown", base_url=api_url)
            
    # If dynamic Ollama URL provided, create ephemeral provider
    if api_url and target == "ollama":
        from app.providers.ollama_provider import OllamaProvider
        return OllamaProvider(base_url=api_url, model=model or settings.OLLAMA_MODEL)
            
    provider = _providers.get(target)
    if provider:
        return provider
    # Fallback order
    for name in ["anthropic", "openai", "gemini", "ollama"]:
        if name in _providers:
            log.warning("provider_fallback", requested=target, using=name)
            return _providers[name]
    raise HTTPException(status_code=503, detail="No AI provider available")


def _extract_json(text: str):
    """Extract JSON (object or array) from LLM response, handling markdown code blocks."""
    text = text.strip()
    # Strip ALL markdown code fences (handles multiple in one response)
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.strip()

    # Direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Models sometimes return multiple arrays for large batches — merge them
    merged: list = []
    pos = 0
    found_any = False
    while pos < len(text):
        start = text.find("[", pos)
        if start == -1:
            break
        depth, end = 0, start
        for i in range(start, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        segment = text[start : end + 1]
        try:
            parsed = json.loads(segment)
            if isinstance(parsed, list):
                merged.extend(parsed)
                found_any = True
        except json.JSONDecodeError:
            pass
        pos = end + 1

    if found_any:
        return merged

    # Single object fallback
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())

    raise ValueError(f"Could not extract JSON from response: {text[:200]}")


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────


class RiskAnalysisRequest(BaseModel):
    finding: dict
    asset: dict
    base_scores: dict
    provider: str | None = None
    api_key: str | None = None
    api_url: str | None = None
    prompt_template: str | None = None
    system_prompt_text: str | None = None

class RiskBatchAnalysisRequest(BaseModel):
    run_id: str
    project: dict
    findings: list[dict]
    business_context: dict | None = None
    ai_provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    api_url: str | None = None
    prompt_template: str | None = None
    system_prompt_text: str | None = None


class RiskAnalysisResponse(BaseModel):
    provider: str
    model: str
    recommendation: dict
    tokens_used: int | None
    raw_response: str | None = None


class ExecutiveSummaryRequest(BaseModel):
    project_context: dict
    provider: str | None = None
    api_key: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────


@app.post("/api/v1/analyze/risk", response_model=RiskAnalysisResponse)
async def analyze_risk(request: RiskAnalysisRequest):
    provider = _get_provider(request.provider, request.api_key, request.api_url, request.model if hasattr(request, "model") else None)
    user_prompt = build_risk_analysis_prompt(request.model_dump())
    
    if request.system_prompt_text:
        system_prompt = request.system_prompt_text
    else:
        system_prompt = PROMPTS_MAP.get(request.prompt_template, RISK_ANALYSIS_SYSTEM_PROMPT) if request.prompt_template else RISK_ANALYSIS_SYSTEM_PROMPT

    try:
        response: LLMResponse = await provider.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=settings.MAX_TOKENS,
            temperature=settings.TEMPERATURE,
        )
    except Exception as exc:
        log.error("ai_completion_failed", provider=provider.name, error=str(exc))
        raise HTTPException(status_code=502, detail=f"AI provider error: {str(exc)}")

    try:
        recommendation = _extract_json(response.content)
    except (ValueError, json.JSONDecodeError) as exc:
        log.warning("response_parse_failed", provider=provider.name, error=str(exc), raw=response.content[:300])
        # Return a safe fallback rather than failing the entire analysis
        recommendation = {
            "probability_score": request.base_scores.get("likelihood", 5.0),
            "impact_score": request.base_scores.get("impact", 5.0),
            "risk_level": request.base_scores.get("risk_level", "medium"),
            "treatment_recommendation": "mitigate",
            "priority": "medium_term",
            "confidence_score": 0.3,
            "parse_error": str(exc),
        }

    log.info(
        "risk_analyzed",
        provider=provider.name,
        model=response.model,
        risk_level=recommendation.get("risk_level"),
        tokens=response.tokens_used,
    )

    return RiskAnalysisResponse(
        provider=provider.name,
        model=response.model,
        recommendation=recommendation,
        tokens_used=response.tokens_used,
    )


@app.post("/api/v1/analyze/risks-batch")
async def analyze_risks_batch(request: RiskBatchAnalysisRequest):
    """
    Agrupa N hallazgos en M escenarios de riesgo de negocio (M << N).
    Una sola llamada a la IA con todos los hallazgos — el modelo devuelve un array agrupado.
    """
    provider = _get_provider(request.ai_provider, request.api_key, request.api_url, request.model)

    user_prompt = build_grouped_risk_prompt(request.findings, request.project, request.business_context)

    system_prompt = request.system_prompt_text if request.system_prompt_text else GROUPED_RISK_SYSTEM_PROMPT

    try:
        response: LLMResponse = await provider.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max(settings.MAX_TOKENS, 4096),
            temperature=0.2,
        )
    except Exception as exc:
        import traceback
        error_details = traceback.format_exc()
        log.error("grouped_analysis_failed", provider=provider.name, error=error_details)
        raise HTTPException(status_code=502, detail=f"Error del proveedor de IA: {str(exc)}")

    # Mapa categoría → (título de riesgo, categoría ISO 31000, impacto base, prioridad)
    CATEGORY_RISK_MAP = {
        "sql_injection":           ("Ejecución de consultas maliciosas en base de datos",        "confidentiality", 5, "immediate"),
        "xss":                     ("Compromiso de sesión y robo de credenciales de usuario",     "confidentiality", 4, "immediate"),
        "command_injection":       ("Ejecución remota de comandos en el servidor",               "integrity",       5, "immediate"),
        "path_traversal":          ("Acceso no autorizado a archivos del sistema",               "confidentiality", 4, "short_term"),
        "hardcoded_credentials":   ("Exposición de credenciales en el código fuente",            "confidentiality", 5, "immediate"),
        "broken_auth":             ("Autenticación deficiente y escalación de privilegios",      "confidentiality", 4, "short_term"),
        "broken_access_control":   ("Control de acceso insuficiente a recursos sensibles",       "confidentiality", 4, "short_term"),
        "weak_crypto":             ("Protección criptográfica insuficiente de datos sensibles",  "confidentiality", 3, "short_term"),
        "insecure_deserialization":("Ejecución de código arbitrario por deserialización insegura","integrity",      5, "immediate"),
        "ssrf":                    ("Acceso no autorizado a recursos internos de la red",        "confidentiality", 4, "short_term"),
        "xxe":                     ("Lectura de archivos internos por inyección de entidades XML","confidentiality", 4, "short_term"),
        "csrf":                    ("Ejecución de acciones no autorizadas en nombre del usuario","integrity",       3, "short_term"),
        "open_redirect":           ("Redirección maliciosa que facilita phishing",               "reputational",    3, "medium_term"),
        "insecure_random":         ("Valores predecibles que comprometen tokens de seguridad",   "confidentiality", 3, "medium_term"),
        "injection":               ("Inyección de datos maliciosos en componentes del sistema",  "integrity",       4, "short_term"),
        "insecure_transport":      ("Comunicación de datos sin cifrado en tránsito",              "confidentiality", 4, "short_term"),
        "container_security":      ("Configuración insegura de contenedores Docker",              "operational",     3, "medium_term"),
        "security_misconfiguration":("Configuración insegura que amplía la superficie de ataque","operational",    3, "medium_term"),
    }

    def _make_fallback_risks(findings: list[dict]) -> list[dict]:
        """Agrupa findings por categoría y crea un riesgo de negocio por grupo."""
        from collections import defaultdict
        groups: dict[str, list[dict]] = defaultdict(list)
        for f in findings:
            cat = f.get("category") or "security_misconfiguration"
            groups[cat].append(f)

        SEV_PROB = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
        risks = []
        for cat, cat_findings in groups.items():
            meta = CATEGORY_RISK_MAP.get(cat, CATEGORY_RISK_MAP["security_misconfiguration"])
            title, iso_cat, base_impact, priority = meta

            # Probabilidad base: máxima severidad del grupo + bonus por volumen
            max_sev = max((SEV_PROB.get(f.get("severity", "low"), 2) for f in cat_findings), default=2)
            bonus = 0 if len(cat_findings) == 1 else (1 if len(cat_findings) <= 4 else 2)
            probability = min(5, max_sev + bonus)

            ids = [f.get("id") for f in cat_findings if f.get("id")]
            # Finding más crítico como primario
            primary = max(cat_findings, key=lambda f: SEV_PROB.get(f.get("severity", "low"), 2))

            risks.append({
                "risk_title": title,
                "risk_description": (
                    f"El análisis detectó {len(cat_findings)} hallazgo{'s' if len(cat_findings) > 1 else ''} críticos relacionados con '{cat}'. "
                    f"Este escenario de riesgo implica que un atacante podría aprovechar estas vulnerabilidades ({title.lower()}) "
                    f"para comprometer el sistema. Riesgo generado automáticamente por fallback de IA."
                ),
                "risk_category": iso_cat,
                "business_impact_operational": f"Impacto directo en la {iso_cat.replace('confidentiality', 'confidencialidad').replace('integrity', 'integridad').replace('availability', 'disponibilidad').replace('operational', 'operación')} del negocio.",
                "business_impact_financial": "Posible pérdida económica por disrupción operativa o incidentes.",
                "business_impact_normative": "Potencial incumplimiento normativo dependiendo de la naturaleza de los datos.",
                "business_impact_reputational": "Posible pérdida de confianza de los clientes e impacto negativo en la imagen.",
                "probability": probability,
                "impact": base_impact,
                "finding_ids": ids,
                "primary_finding_id": primary.get("id"),
                "treatment_recommendation": "mitigate",
                "priority": priority,
                "business_process_id": None,
                "impact_operational": "Medio",
                "impact_financial": "Medio",
                "impact_normative": None,
                "impact_reputational": "Bajo",
            })

        # Ordenar por score descendente
        risks.sort(key=lambda r: r["probability"] * r["impact"], reverse=True)
        return risks

    log.info("grouped_raw_response", content=response.content[:1000])

    # Mapa de indice → UUID real (el modelo recibe 1,2,3... y devuelve indices)
    idx_to_id = {idx + 1: f.get("id") for idx, f in enumerate(request.findings)}

    try:
        raw = _extract_json(response.content)
        grouped_risks: list[dict] = raw if isinstance(raw, list) else raw.get("risks", [])

        # Convertir finding_indices → finding_ids (UUIDs reales) y normalizar llaves traducidas
        for risk in grouped_risks:
            # Normalizar llaves traducidas por IA agresiva
            if "titulo" in risk and "risk_title" not in risk: risk["risk_title"] = risk.pop("titulo")
            if "descripcion" in risk and "risk_description" not in risk: risk["risk_description"] = risk.pop("descripcion")
            if "impacto_operativo" in risk and "business_impact_operational" not in risk: risk["business_impact_operational"] = risk.pop("impacto_operativo")
            if "impacto_financiero" in risk and "business_impact_financial" not in risk: risk["business_impact_financial"] = risk.pop("impacto_financiero")
            if "impacto_normativo" in risk and "business_impact_normative" not in risk: risk["business_impact_normative"] = risk.pop("impacto_normativo")
            if "impacto_reputacional" in risk and "business_impact_reputational" not in risk: risk["business_impact_reputational"] = risk.pop("impacto_reputacional")
            if "categoria" in risk and "risk_category" not in risk: risk["risk_category"] = risk.pop("categoria")
            if "probabilidad" in risk and "probability" not in risk: risk["probability"] = risk.pop("probabilidad")
            if "impacto" in risk and "impact" not in risk: risk["impact"] = risk.pop("impacto")
            if "hallazgos_asociados" in risk and "finding_indices" not in risk: risk["finding_indices"] = risk.pop("hallazgos_asociados")
            if "indice_hallazgo_primario" in risk and "primary_finding_index" not in risk: risk["primary_finding_index"] = risk.pop("indice_hallazgo_primario")
            if "proceso_negocio_id" in risk and "business_process_id" not in risk: risk["business_process_id"] = risk.pop("proceso_negocio_id")
            if "impacto_operacional" in risk and "impact_operational" not in risk: risk["impact_operational"] = risk.pop("impacto_operacional")
            if "impacto_financiero" in risk and "impact_financial" not in risk: risk["impact_financial"] = risk.pop("impacto_financiero")
            if "impacto_normativo" in risk and "impact_normative" not in risk: risk["impact_normative"] = risk.pop("impacto_normativo")
            if "impacto_reputacional" in risk and "impact_reputational" not in risk: risk["impact_reputational"] = risk.pop("impacto_reputacional")

            indices: list[int] = risk.pop("finding_indices", [])
            primary_idx: int | None = risk.pop("primary_finding_index", None)
            if indices:
                risk["finding_ids"] = [idx_to_id[i] for i in indices if i in idx_to_id]
                risk["primary_finding_id"] = idx_to_id.get(primary_idx) if primary_idx else (risk["finding_ids"][0] if risk["finding_ids"] else None)
            elif not risk.get("finding_ids"):
                # Modelo que devolvió UUIDs directamente (compatible con versiones anteriores)
                risk.setdefault("finding_ids", [])

    except (ValueError, json.JSONDecodeError) as exc:
        log.error("grouped_parse_failed", error=str(exc), raw=response.content[:400])
        grouped_risks = _make_fallback_risks(request.findings)

    # Si el modelo devolvió lista vacía, aplicar fallback también
    if not grouped_risks:
        log.warning("grouped_empty_response", raw=response.content[:400])
        grouped_risks = _make_fallback_risks(request.findings)

    log.info(
        "grouped_risks_generated",
        provider=provider.name,
        findings_in=len(request.findings),
        risks_out=len(grouped_risks),
        tokens=response.tokens_used,
    )

    return {"risks": grouped_risks, "tokens_used": response.tokens_used, "cost_usd": 0.0}

class ProbabilityAssessmentRequest(BaseModel):
    run_id: str
    project: dict
    scenarios: list[dict]
    business_context: dict | None = None
    ai_provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    api_url: str | None = None


@app.post("/api/v1/analyze/probability")
async def assess_probability(request: ProbabilityAssessmentRequest):
    """
    Evalúa la probabilidad (1-5) de materialización de cada escenario de riesgo.
    Recibe escenarios con sus hallazgos agrupados y devuelve scores por scenario_code.
    """
    provider = _get_provider(request.ai_provider, request.api_key, request.api_url, request.model)
    user_prompt = build_probability_prompt(request.scenarios, request.project, request.business_context)

    try:
        response: LLMResponse = await provider.complete(
            system_prompt=PROBABILITY_ASSESSMENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=max(settings.MAX_TOKENS, 4096),
            temperature=0.2,
        )
    except Exception as exc:
        log.error("probability_assessment_failed", provider=provider.name, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Error del proveedor de IA: {str(exc)}")

    log.info("probability_raw_response", content=response.content[:500])

    try:
        raw = _extract_json(response.content)
        results: list[dict] = raw if isinstance(raw, list) else raw.get("scenarios", [])
        # Normalize translated keys
        for r in results:
            if "codigo_escenario" in r and "scenario_code" not in r:
                r["scenario_code"] = r.pop("codigo_escenario")
            if "probabilidad" in r and "probability" not in r:
                r["probability"] = r.pop("probabilidad")
            if "nivel_probabilidad" in r and "prob_level" not in r:
                r["prob_level"] = r.pop("nivel_probabilidad")
            if "justificacion" in r and "probability_rationale" not in r:
                r["probability_rationale"] = r.pop("justificacion")
    except (ValueError, json.JSONDecodeError) as exc:
        log.error("probability_parse_failed", error=str(exc), raw=response.content[:400])
        # Fallback: assign probability=3 (Media) to all scenarios
        results = [
            {
                "scenario_code": s.get("scenario_code"),
                "probability": 3,
                "prob_level": "Media",
                "probability_rationale": "Evaluación automática por defecto (fallo al parsear respuesta IA).",
            }
            for s in request.scenarios
        ]

    log.info(
        "probability_assessed",
        provider=provider.name,
        scenarios_in=len(request.scenarios),
        scenarios_out=len(results),
        tokens=response.tokens_used,
    )

    return {"results": results, "tokens_used": response.tokens_used}


class RisksFromScenariosRequest(BaseModel):
    run_id: str
    project: dict
    scenarios: list[dict]
    business_context: dict | None = None
    ai_provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    api_url: str | None = None


@app.post("/api/v1/analyze/risks-from-scenarios")
async def risks_from_scenarios(request: RisksFromScenariosRequest):
    """
    Genera narrativa ejecutiva de riesgo para escenarios con P e I ya evaluados.
    No recalcula probabilidad ni impacto — solo genera risk_title, description, etc.
    """
    provider = _get_provider(request.ai_provider, request.api_key, request.api_url, request.model)
    user_prompt = build_risks_from_scenarios_prompt(request.scenarios, request.project, request.business_context)

    try:
        response: LLMResponse = await provider.complete(
            system_prompt=RISKS_FROM_SCENARIOS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=max(settings.MAX_TOKENS, 4096),
            temperature=0.3,
        )
    except Exception as exc:
        log.error("risks_from_scenarios_failed", provider=provider.name, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Error del proveedor de IA: {str(exc)}")

    log.info("risks_from_scenarios_raw", content=response.content[:500])

    try:
        raw = _extract_json(response.content)
        results: list[dict] = raw if isinstance(raw, list) else raw.get("risks", [])
        for r in results:
            if "codigo_escenario" in r and "scenario_code" not in r:
                r["scenario_code"] = r.pop("codigo_escenario")
            if "titulo_riesgo" in r and "risk_title" not in r:
                r["risk_title"] = r.pop("titulo_riesgo")
            # Fix double "Riesgo de Riesgo de..." from models that copy the business_title prefix
            if "risk_title" in r:
                r["risk_title"] = re.sub(r"(?i)^riesgo\s+de\s+riesgo\s+de\s+", "Riesgo de ", r["risk_title"])
            if "descripcion" in r and "risk_description" not in r:
                r["risk_description"] = r.pop("descripcion")
            if "impacto_operativo" in r and "business_impact_operational" not in r:
                r["business_impact_operational"] = r.pop("impacto_operativo")
            if "impacto_financiero" in r and "business_impact_financial" not in r:
                r["business_impact_financial"] = r.pop("impacto_financiero")
            if "impacto_normativo" in r and "business_impact_normative" not in r:
                r["business_impact_normative"] = r.pop("impacto_normativo")
            if "impacto_reputacional" in r and "business_impact_reputational" not in r:
                r["business_impact_reputational"] = r.pop("impacto_reputacional")
            if "categoria" in r and "risk_category" not in r:
                r["risk_category"] = r.pop("categoria")
            if "recomendacion" in r and "treatment_recommendation" not in r:
                r["treatment_recommendation"] = r.pop("recomendacion")
    except (ValueError, json.JSONDecodeError) as exc:
        log.error("risks_from_scenarios_parse_failed", error=str(exc), raw=response.content[:400])
        # Fallback: generate minimal narrative from scenario data
        results = [
            {
                "scenario_code": s.get("scenario_code"),
                "risk_title": (
                    f"Riesgo de seguridad en {s['process_name']}"
                    if s.get("process_name")
                    else "Riesgo de seguridad en activo de negocio"
                )[:80],
                "risk_description": (
                    f"Se han identificado debilidades de seguridad que podrían permitir a un actor externo "
                    f"comprometer {'el proceso de ' + s['process_name'] if s.get('process_name') else 'un sistema de negocio'}. "
                    f"El nivel de riesgo evaluado es P={s.get('probability')} × I={s.get('impact')}. "
                    f"Se recomienda revisar los controles de seguridad asociados."
                ),
                "business_impact_operational": (
                    f"Interrupción del proceso {'de ' + s['process_name'] if s.get('process_name') else 'de negocio afectado'}. "
                    f"Score P={s.get('probability')} × I={s.get('impact')} indica exposición {'crítica' if (s.get('probability',0) * s.get('impact',0)) >= 15 else 'significativa'}."
                ),
                "business_impact_financial": "Pérdidas económicas directas e indirectas asociadas al incidente. Requiere cuantificación basada en BIA.",
                "business_impact_normative": "Posible incumplimiento de obligaciones regulatorias. Revisar marco normativo aplicable (RGPD, NIS2, ENS).",
                "business_impact_reputational": "Riesgo de daño reputacional ante clientes, socios y mercado. Alcance dependiente de la naturaleza del activo comprometido.",
                "risk_category": "security",
                "affected_cia": ["C", "I"],
                "treatment_recommendation": "mitigate",
                "priority": "medium_term",
            }
            for s in request.scenarios
        ]

    log.info(
        "risks_from_scenarios_generated",
        provider=provider.name,
        scenarios_in=len(request.scenarios),
        risks_out=len(results),
        tokens=response.tokens_used,
    )
    return {"risks": results, "tokens_used": response.tokens_used}


class ScenariosScoringRequest(BaseModel):
    run_id: str
    project: dict
    scenario_groups: list[dict]
    ai_provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    api_url: str | None = None


@app.post("/api/v1/analyze/score-scenarios")
async def score_scenarios(request: ScenariosScoringRequest):
    """
    Recibe grupos pre-agrupados por el backend (un grupo = activo × categoría) y devuelve
    título ejecutivo + probabilidad + impacto para cada grupo.
    NO reagrupa — solo puntúa y titula.
    """
    provider = _get_provider(request.ai_provider, request.api_key, request.api_url, request.model)
    user_prompt = build_scenarios_scoring_prompt(request.scenario_groups, request.project)

    try:
        response: LLMResponse = await provider.complete(
            system_prompt=SCENARIOS_SCORING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=max(settings.MAX_TOKENS, 4096),
            temperature=0.2,
        )
    except Exception as exc:
        log.error("score_scenarios_failed", provider=provider.name, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Error del proveedor de IA: {str(exc)}")

    log.info("score_scenarios_raw", content=response.content[:500])

    try:
        raw = _extract_json(response.content)
        results: list[dict] = raw if isinstance(raw, list) else raw.get("scenarios", [])
        # Normalize Spanish keys the AI might return
        for r in results:
            if "grupo_id" in r and "group_id" not in r:
                r["group_id"] = r.pop("grupo_id")
            if "titulo" in r and "risk_title" not in r:
                r["risk_title"] = r.pop("titulo")
            if "titulo_tecnico" in r and "technical_title" not in r:
                r["technical_title"] = r.pop("titulo_tecnico")
            if "etiqueta_tecnica" in r and "technical_title" not in r:
                r["technical_title"] = r.pop("etiqueta_tecnica")
            if "probabilidad" in r and "probability" not in r:
                r["probability"] = r.pop("probabilidad")
            if "impacto" in r and "impact" not in r:
                r["impact"] = r.pop("impacto")
    except (ValueError, json.JSONDecodeError) as exc:
        log.error("score_scenarios_parse_failed", error=str(exc), raw=response.content[:400])
        # Fallback: assign median scores and generate titles from group data
        _SEV_PROB = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
        results = [
            {
                "group_id": sg.get("group_id"),
                "technical_title": f"{sg.get('category_label') or (sg.get('category') or 'Vulnerabilidad').replace('_', ' ').title()} en {sg.get('asset_name') or 'activo desconocido'}",
                "risk_title": f"Riesgo de {(sg.get('category_label') or sg.get('category') or 'seguridad').lower()} en {sg.get('asset_name') or 'activo de negocio'}",
                "probability": _SEV_PROB.get((sg.get("max_severity") or "low").lower(), 2),
                "impact": 3,
                "probability_rationale": "Estimación automática por fallo al parsear respuesta IA.",
                "impact_rationale": "Estimación automática por fallo al parsear respuesta IA.",
            }
            for sg in request.scenario_groups
        ]

    log.info(
        "score_scenarios_done",
        provider=provider.name,
        groups_in=len(request.scenario_groups),
        scored=len(results),
        tokens=response.tokens_used,
    )

    return {"scenarios": results, "tokens_used": response.tokens_used}


class TreatmentPlanRequest(BaseModel):
    risk: dict
    findings: list[dict] = []
    ai_provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    api_url: str | None = None


@app.post("/api/v1/analyze/treatment-plan")
async def suggest_treatment_plan(request: TreatmentPlanRequest):
    """Sugiere acciones de tratamiento para un riesgo dado basadas en sus hallazgos vinculados."""
    provider = _get_provider(request.ai_provider, request.api_key, request.api_url, request.model)
    user_prompt = build_treatment_plan_prompt(request.risk, request.findings)

    try:
        response: LLMResponse = await provider.complete(
            system_prompt=TREATMENT_PLAN_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=2048,
            temperature=0.3,
        )
    except Exception as exc:
        log.error("treatment_plan_failed", provider=provider.name, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Error del proveedor de IA: {str(exc)}")

    try:
        actions = _extract_json(response.content)
        if not isinstance(actions, list):
            actions = actions.get("actions", actions.get("tratamientos", []))
    except (ValueError, json.JSONDecodeError) as exc:
        log.error("treatment_plan_parse_failed", error=str(exc))
        risk_level = request.risk.get("risk_level", "medium")
        priority = "immediate" if risk_level in ("critical", "high") else "medium_term"
        actions = [
            {
                "treatment_type": "mitigate",
                "title": "Implementar controles de seguridad para el riesgo identificado",
                "description": "Revisar y reforzar los controles existentes relacionados con este riesgo.",
                "owner_name": "Equipo de Seguridad",
                "priority": priority,
                "expected_risk_reduction": 50,
            }
        ]

    log.info("treatment_plan_generated", provider=provider.name, actions=len(actions), tokens=response.tokens_used)
    return {"actions": actions, "tokens_used": response.tokens_used}


@app.post("/api/v1/analyze/executive")
async def executive_summary(request: ExecutiveSummaryRequest):
    provider = _get_provider(request.provider, request.api_key)
    user_prompt = build_executive_summary_prompt(request.project_context)

    try:
        response = await provider.complete(
            system_prompt=EXECUTIVE_SUMMARY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=2048,
            temperature=0.2,
        )
        summary = _extract_json(response.content)
    except Exception as exc:
        log.error("executive_summary_failed", error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc))

    return {"provider": provider.name, "model": response.model, "summary": summary}


class CodeScanRequest(BaseModel):
    file_path: str
    code_snippet: str
    language: str | None = None
    system_prompt_text: str
    user_prompt_text: str
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    api_url: str | None = None
    prompt_version: str | None = None


@app.post("/api/v1/scan/code")
async def scan_code(request: CodeScanRequest):
    """IA-escáner (F1): analyse a source-code snippet and return security findings."""
    provider = _get_provider(request.provider, request.api_key, request.api_url, request.model)
    try:
        response: LLMResponse = await provider.complete(
            system_prompt=request.system_prompt_text,
            user_prompt=request.user_prompt_text,
            max_tokens=settings.MAX_TOKENS,
            temperature=0.1,
        )
    except Exception as exc:
        log.error("code_scan_failed", provider=provider.name, file=request.file_path, error=str(exc))
        raise HTTPException(status_code=502, detail=f"AI provider error: {str(exc)}")

    try:
        parsed = _extract_json(response.content)
        findings: list[dict] = parsed if isinstance(parsed, list) else parsed.get("findings", [])
    except (ValueError, json.JSONDecodeError) as exc:
        log.warning("code_scan_parse_failed", file=request.file_path, error=str(exc))
        findings = []

    log.info(
        "code_scanned",
        provider=provider.name,
        file=request.file_path,
        findings=len(findings),
        tokens=response.tokens_used,
    )
    return {
        "findings": findings,
        "provider": response.provider,
        "model": response.model,
        "tokens_used": response.tokens_used,
        "prompt_version": request.prompt_version,
    }


@app.get("/api/v1/providers")
async def list_providers():
    status: dict[str, bool] = {}
    for name, provider in _providers.items():
        status[name] = await provider.is_available()
    return {
        "providers": status,
        "default": settings.DEFAULT_PROVIDER,
        "available": [k for k, v in status.items() if v],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-gateway", "providers": list(_providers.keys())}
