"""
Escenarios router — SC-xxx

  POST /projects/{project_id}/escenarios:consolidar          ← agrupa findings → escenarios
  POST /projects/{project_id}/escenarios:evaluar-probabilidad ← IA asigna probabilidad
  GET  /projects/{project_id}/escenarios                     ← lista escenarios
  GET  /escenarios/{scenario_id}                             ← escenario individual
  PATCH /escenarios/{scenario_id}/probabilidad               ← override manual probabilidad
  PATCH /escenarios/{scenario_id}/impacto                    ← asigna proceso + impacto
  POST /projects/{project_id}/analisis:generar-fichas        ← genera fichas RN-xxx desde escenarios
"""
from __future__ import annotations

import re
import uuid
from typing import Annotated
from urllib.parse import quote

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.models.project import Project
from app.modules.contexto.bia.excel_export import build_scenarios_excel
from app.modules.escenarios.consolidator import consolidate_scenarios
from app.modules.escenarios.models import RiskScenario, ScenarioFindingLink
from app.modules.escenarios.schemas import (
    ConsolidateBody,
    ConsolidateResult,
    RiskScenarioOut,
    ScenarioImpactUpdate,
    ScenarioProbabilityUpdate,
)

log = structlog.get_logger(__name__)
router = APIRouter(tags=["escenarios"])
DB = Annotated[AsyncSession, Depends(get_db)]

_SCORE_LEVEL = {5: "Muy Alta", 4: "Alta", 3: "Media", 2: "Baja", 1: "Muy Baja"}

# ─── Catálogo Maestro de Traducción (module-level) ────────────────────────────
# Mapa: family_key → label técnico almacenado en scenario.consequence
_FAMILY_LABEL: dict[str, str] = {
    "injection":             "Inyección (SQL / Comando / XXE)",
    "xss":                   "Cross-Site Scripting (XSS)",
    "csrf":                  "Falsificación de Petición (CSRF)",
    "ssrf":                  "Server-Side Request Forgery (SSRF)",
    "access_control":        "Control de Acceso y Autorización",
    "broken_auth":           "Autenticación y Gestión de Sesiones",
    "cryptography":          "Criptografía y Protección de Datos",
    "misconfiguration":      "Configuración de Seguridad Incorrecta",
    "data_exposure":         "Exposición de Información Sensible",
    "credentials":           "Credenciales y Secretos Expuestos",
    "vulnerable_components": "Componentes y Dependencias Vulnerables",
    "insecure_design":       "Diseño Inseguro y Lógica de Negocio",
    "logging":               "Registro y Monitoreo Insuficiente",
    "integrity_failures":    "Fallos de Integridad de Software",
}

# Mapa inverso: label técnico → family_key (para extraer familia de consequence)
_LABEL_TO_FAMILY: dict[str, str] = {v.lower(): k for k, v in _FAMILY_LABEL.items()}

# Catálogo Maestro: family_key → Nombre del Riesgo de Negocio (lenguaje Directorio)
_CATALOG_BUSINESS_RISK: dict[str, str] = {
    "injection":             "Riesgo de Manipulación Maliciosa de Sistemas Transaccionales",
    "xss":                   "Riesgo de Fraude Digital y Suplantación de Identidad hacia Clientes",
    "csrf":                  "Riesgo de Ejecución No Autorizada de Transacciones en Nombre del Cliente",
    "broken_auth":           "Riesgo de Acceso Ilegítimo a Cuentas y Sistemas Críticos",
    "data_exposure":         "Riesgo de Fuga Masiva de Información Confidencial y Personal",
    "access_control":        "Riesgo de Escalada de Privilegios y Acceso No Autorizado a Información",
    "misconfiguration":      "Riesgo de Exposición Involuntaria de la Arquitectura Interna de Sistemas",
    "vulnerable_components": "Riesgo de Compromiso por Vulnerabilidades Heredadas en la Cadena de Software",
    "ssrf":                  "Riesgo de Acceso Encubierto a Sistemas Internos desde el Exterior",
    "cryptography":          "Riesgo de Exposición y Robo de Datos Sensibles por Debilidades en Cifrado",
    "credentials":           "Riesgo de Acceso No Autorizado a Sistemas Críticos por Credenciales Expuestas",
    "insecure_design":       "Riesgo de Deficiencias Estructurales en Aplicaciones que Exponen el Negocio",
    "logging":               "Riesgo de Incapacidad de Detección y Respuesta Tardía ante Ataques Silenciosos",
    "integrity_failures":    "Riesgo de Sabotaje de la Cadena de Suministro Digital e Infraestructura Crítica",
}


def _family_from_consequence(consequence: str) -> str | None:
    """Extrae la family_key desde el technical_title almacenado en consequence."""
    c_lower = consequence.strip().lower()
    for label_lower, family in _LABEL_TO_FAMILY.items():
        if c_lower.startswith(label_lower):
            return family
    # Fallback: buscar en cualquier parte del string
    for label_lower, family in _LABEL_TO_FAMILY.items():
        if label_lower in c_lower:
            return family
    return None


def _asset_from_consequence(consequence: str) -> str | None:
    """Extrae el nombre del activo de 'Label en AssetName'."""
    if " en " in consequence:
        return consequence.split(" en ", 1)[1].strip()
    return None


def _enrich(scenario: RiskScenario, finding_count: int, process_name: str | None, asset_name: str | None = None) -> RiskScenarioOut:
    out = RiskScenarioOut.model_validate(scenario)
    out.finding_count = finding_count
    out.business_process_name = process_name
    out.asset_name = asset_name
    return out


# ─── consolidar ───────────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/escenarios:consolidar",
    response_model=ConsolidateResult,
)
async def consolidar(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    body: ConsolidateBody | None = None,
):
    finding_ids = body.finding_ids if body else None
    stats, scenarios = await consolidate_scenarios(db, project_id, finding_ids=finding_ids)
    return ConsolidateResult(
        findings_processed=stats.findings_processed,
        scenarios_created=stats.scenarios_created,
        scenarios_updated=stats.scenarios_updated,
        scenarios=[RiskScenarioOut.model_validate(s) for s in scenarios],
    )


# ─── lista ────────────────────────────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/escenarios",
    response_model=list[RiskScenarioOut],
)
async def list_escenarios(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    from app.modules.contexto.bia.models import BusinessProcess
    from app.models.asset import Asset

    rows = await db.execute(
        select(
            RiskScenario,
            func.count(ScenarioFindingLink.finding_id).label("finding_count"),
            BusinessProcess.name.label("process_name"),
            Asset.name.label("asset_name"),
        )
        .outerjoin(ScenarioFindingLink, ScenarioFindingLink.scenario_id == RiskScenario.id)
        .outerjoin(BusinessProcess, BusinessProcess.id == RiskScenario.business_process_id)
        .outerjoin(Asset, Asset.id == RiskScenario.asset_id)
        .where(RiskScenario.project_id == project_id)
        .group_by(RiskScenario.id, BusinessProcess.name, Asset.name)
        .order_by(RiskScenario.scenario_code)
    )
    return [_enrich(s, fc or 0, pn, an) for s, fc, pn, an in rows.all()]


# ─── export Excel ────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/escenarios/export", response_class=StreamingResponse)
async def export_escenarios_excel(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """Tabla de Escenarios de Riesgo — todos los campos P, I, dimensiones, riesgo, tratamientos."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    pid = str(project_id)
    q = text("""
        SELECT
            e.scenario_code,
            e.title                                             AS scenario_title,
            e.consequence,
            e.group_key,
            e.status,
            e.probability,
            e.prob_level,
            e.probability_rationale,
            e.impact,
            e.impact_level,
            e.impact_rationale,
            e.impact_operational,
            e.impact_financial,
            e.impact_normative,
            e.impact_reputational,
            STRING_AGG(DISTINCT f.finding_code, ', ')           AS finding_codes,
            COUNT(DISTINCT eh.finding_id)                       AS finding_count,
            STRING_AGG(DISTINCT fa.name,        chr(10))        AS asset_names,
            STRING_AGG(DISTINCT fa.asset_type,  ', ')           AS asset_types,
            STRING_AGG(DISTINCT fa.criticality, ', ')           AS asset_criticalities,
            STRING_AGG(DISTINCT bp.name,        chr(10))        AS process_names,
            r.risk_code,
            r.risk_level,
            r.status                                            AS risk_status,
            STRING_AGG(DISTINCT t.treatment_type, ', ')         AS treatment_types,
            COUNT(DISTINCT t.id)                                AS treatment_count
        FROM escenarios e
        LEFT JOIN escenario_hallazgos eh   ON eh.scenario_id = e.id
        LEFT JOIN findings f               ON f.id = eh.finding_id
        LEFT JOIN assets fa                ON fa.id = f.asset_id
        LEFT JOIN activo_proceso_links apl ON apl.asset_id = fa.id
        LEFT JOIN procesos_negocio bp      ON bp.id = apl.process_id
        LEFT JOIN riesgos r                ON r.scenario_id = e.id
        LEFT JOIN tratamientos t           ON t.risk_id = r.id
        WHERE e.project_id = :pid
        GROUP BY
            e.id, e.scenario_code, e.title, e.consequence, e.group_key, e.status,
            e.probability, e.prob_level, e.probability_rationale,
            e.impact, e.impact_level, e.impact_rationale,
            e.impact_operational, e.impact_financial, e.impact_normative, e.impact_reputational,
            r.risk_code, r.risk_level, r.status
        ORDER BY e.scenario_code NULLS LAST
    """)
    rows = [dict(r._mapping) for r in (await db.execute(q, {"pid": pid})).fetchall()]

    buf = build_scenarios_excel(rows, project.name)
    safe_name = quote(f"Escenarios_{project.name}.xlsx", safe="")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )


# ─── individual ───────────────────────────────────────────────────────────────

@router.get("/escenarios/{scenario_id}", response_model=RiskScenarioOut)
async def get_escenario(
    scenario_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    from app.modules.contexto.bia.models import BusinessProcess
    from app.models.asset import Asset

    row = await db.execute(
        select(
            RiskScenario,
            func.count(ScenarioFindingLink.finding_id).label("finding_count"),
            BusinessProcess.name.label("process_name"),
            Asset.name.label("asset_name"),
        )
        .outerjoin(ScenarioFindingLink, ScenarioFindingLink.scenario_id == RiskScenario.id)
        .outerjoin(BusinessProcess, BusinessProcess.id == RiskScenario.business_process_id)
        .outerjoin(Asset, Asset.id == RiskScenario.asset_id)
        .where(RiskScenario.id == scenario_id)
        .group_by(RiskScenario.id, BusinessProcess.name, Asset.name)
    )
    result = row.first()
    if not result:
        raise HTTPException(status_code=404, detail="Escenario no encontrado")
    s, fc, pn, an = result
    return _enrich(s, fc or 0, pn, an)


# ─── IA probabilidad ──────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/escenarios:evaluar-probabilidad",
    response_model=list[RiskScenarioOut],
)
async def evaluar_probabilidad(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    from app.models.asset import Asset
    from app.models.finding import Finding
    from app.models.project import Project
    from app.models.workspace import Workspace
    from app.modules.contexto.bia.models import BusinessProcess
    from app.shared.ai_gateway.tasks import call_probability_assessment

    scenario_rows = await db.execute(
        select(RiskScenario)
        .where(RiskScenario.project_id == project_id)
        .order_by(RiskScenario.scenario_code)
    )
    scenarios = scenario_rows.scalars().all()
    if not scenarios:
        raise HTTPException(
            status_code=404,
            detail="No hay escenarios. Ejecuta 'Consolidar' primero.",
        )

    scenario_ids = [s.id for s in scenarios]
    link_rows = await db.execute(
        select(
            ScenarioFindingLink.scenario_id,
            Finding.title,
            Finding.description,
            Finding.finding_type,
            Finding.severity,
            Finding.category,
            Finding.owasp_category,
            Finding.cwe,
            Finding.scanner,
            Asset.name.label("asset_name"),
        )
        .join(Finding, ScenarioFindingLink.finding_id == Finding.id)
        .outerjoin(Asset, Finding.asset_id == Asset.id)
        .where(ScenarioFindingLink.scenario_id.in_(scenario_ids))
    )
    link_data = link_rows.mappings().all()

    findings_by_scenario: dict[uuid.UUID, list[dict]] = {s.id: [] for s in scenarios}
    for row in link_data:
        findings_by_scenario[row["scenario_id"]].append({
            "title": row["title"],
            "description": (row["description"] or "")[:300],
            "finding_type": row["finding_type"] or "vulnerability",
            "severity": row["severity"],
            "category": row["category"],
            "owasp_category": row["owasp_category"],
            "cwe": row["cwe"],
            "scanner": row["scanner"],
            "asset_name": row["asset_name"],
        })

    processes_result = await db.execute(
        select(BusinessProcess).where(BusinessProcess.project_id == project_id)
    )
    processes = [
        {"id": str(p.id), "name": p.name, "criticality": p.criticality, "revenue_dependency": p.revenue_dependency}
        for p in processes_result.scalars().all()
    ]

    normative: dict = {}

    project_row = await db.get(Project, project_id)

    # Obtener API key del workspace
    ai_provider = "gemini"
    api_key: str | None = None
    api_url: str | None = None
    model: str | None = None
    if project_row:
        ws = await db.get(Workspace, project_row.workspace_id)
        if ws and ws.ai_config:
            providers_conf = ws.ai_config.get("providers", {})
            # Buscar primer proveedor habilitado con API key
            for pname, pconf in providers_conf.items():
                if pconf and pconf.get("api_key") and pconf.get("enabled", True):
                    ai_provider = pname
                    api_key = pconf.get("api_key")
                    api_url = pconf.get("url")
                    model = pconf.get("model")
                    break
            # Retro-compatibilidad
            if not api_key:
                for pname in ("gemini", "anthropic", "openai"):
                    api_key = ws.ai_config.get(f"{pname}_api_key")
                    if api_key:
                        ai_provider = pname
                        break

    scenario_payloads = [
        {
            "scenario_code": s.scenario_code,
            "consequence": s.consequence,
            "title": s.title,
            "findings": findings_by_scenario.get(s.id, []),
        }
        for s in scenarios
    ]

    ai_result = await call_probability_assessment({
        "run_id": str(uuid.uuid4()),
        "project": {
            "name": project_row.name if project_row else str(project_id),
            "business_context": getattr(project_row, "business_context", None),
        },
        "scenarios": scenario_payloads,
        "business_context": {"processes": processes, "normative": normative},
        "ai_provider": ai_provider,
        "api_key": api_key,
        "api_url": api_url,
        "model": model,
    })

    results_by_code: dict[str, dict] = {r["scenario_code"]: r for r in ai_result.get("results", [])}
    for scenario in scenarios:
        result = results_by_code.get(scenario.scenario_code)
        if result:
            scenario.probability = result.get("probability", 3)
            scenario.prob_level = result.get("prob_level", "Media")
            scenario.probability_rationale = result.get("probability_rationale")
            # Guardar título generado por IA si viene en la respuesta
            if result.get("scenario_title") and not scenario.title:
                scenario.title = result["scenario_title"]
            if scenario.status == "pending":
                scenario.status = "prob_assessed"

    await db.flush()

    updated_rows = await db.execute(
        select(
            RiskScenario,
            func.count(ScenarioFindingLink.finding_id).label("finding_count"),
            Asset.name.label("asset_name"),
        )
        .outerjoin(ScenarioFindingLink, ScenarioFindingLink.scenario_id == RiskScenario.id)
        .outerjoin(Asset, Asset.id == RiskScenario.asset_id)
        .where(RiskScenario.project_id == project_id)
        .group_by(RiskScenario.id, Asset.name)
        .order_by(RiskScenario.scenario_code)
    )
    return [_enrich(s, fc or 0, None, an) for s, fc, an in updated_rows.all()]


# ─── analizar con IA: agrupa + probabilidad en un solo paso ──────────────────

@router.post(
    "/projects/{project_id}/escenarios:analizar",
    response_model=list[RiskScenarioOut],
)
async def analizar_con_ia(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    body: ConsolidateBody | None = None,
):
    """La IA recibe todos los hallazgos y devuelve escenarios agrupados con probabilidad."""
    import re
    from app.models.asset import Asset
    from app.models.finding import Finding
    from app.models.project import Project
    from app.models.scan import Scan, ScanSession
    from app.models.workspace import Workspace
    from app.shared.ai_gateway.tasks import call_score_scenarios

    # 1. AI config from workspace
    project_row = await db.get(Project, project_id)
    ai_provider = "gemini"
    api_key: str | None = None
    api_url: str | None = None
    model: str | None = None
    if project_row:
        ws = await db.get(Workspace, project_row.workspace_id)
        if ws and ws.ai_config:
            # If the client specified a provider, use that one's credentials
            requested_provider = body.ai_provider if body else None
            if requested_provider:
                pconf = ws.ai_config.get("providers", {}).get(requested_provider, {})
                if pconf and pconf.get("api_key"):
                    ai_provider = requested_provider
                    api_key = pconf.get("api_key")
                    api_url = pconf.get("url")
                    model = body.model or pconf.get("model")
            # Fallback: first enabled provider in workspace
            if not api_key:
                for pname, pconf in ws.ai_config.get("providers", {}).items():
                    if pconf and pconf.get("api_key") and pconf.get("enabled", True):
                        ai_provider = pname
                        api_key = pconf.get("api_key")
                        api_url = pconf.get("url")
                        model = pconf.get("model")
                        break
            if not api_key:
                for pname in ("gemini", "anthropic", "openai"):
                    api_key = ws.ai_config.get(f"{pname}_api_key")
                    if api_key:
                        ai_provider = pname
                        break

    # 2. Fetch findings
    finding_ids = body.finding_ids if body else None
    stmt = (
        select(
            Finding.id,
            Finding.asset_id,
            Finding.title,
            Finding.description,
            Finding.finding_type,
            Finding.severity,
            Finding.category,
            Finding.owasp_category,
            Finding.cwe,
            Finding.file_path,
            Finding.line_start,
            Finding.scanner,
            Asset.name.label("asset_name"),
        )
        .join(Scan, Finding.scan_id == Scan.id)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .outerjoin(Asset, Finding.asset_id == Asset.id)
        .where(ScanSession.project_id == project_id, Finding.status.in_(["open", "confirmed"]))
    )
    if finding_ids:
        stmt = stmt.where(Finding.id.in_(finding_ids))

    rows = (await db.execute(stmt)).mappings().all()
    if not rows:
        raise HTTPException(status_code=422, detail="No hay hallazgos abiertos para analizar.")

    # Build finding_id → asset_id map
    finding_asset_map: dict[str, uuid.UUID] = {
        str(r["id"]): r["asset_id"]
        for r in rows if r["asset_id"]
    }

    # Build asset_id → best process_id map via AssetProcessLink (highest weight wins)
    from app.modules.contexto.bia.models import AssetProcessLink, BusinessProcess, BiaEstimate
    asset_ids = list({v for v in finding_asset_map.values()})
    asset_process_map: dict[uuid.UUID, uuid.UUID] = {}
    if asset_ids:
        links_result = await db.execute(
            select(AssetProcessLink.asset_id, AssetProcessLink.process_id, AssetProcessLink.weight)
            .where(AssetProcessLink.asset_id.in_(asset_ids))
            .order_by(AssetProcessLink.weight.desc())
        )
        for link_row in links_result.mappings().all():
            # Keep only the highest-weight process per asset (rows already ordered desc)
            if link_row["asset_id"] not in asset_process_map:
                asset_process_map[link_row["asset_id"]] = link_row["process_id"]

    # Load BIA data for all relevant processes to auto-suggest impact dimensions
    process_ids = list(set(asset_process_map.values()))
    bia_map: dict[uuid.UUID, BiaEstimate] = {}
    process_map: dict[uuid.UUID, BusinessProcess] = {}
    if process_ids:
        bia_result = await db.execute(
            select(BiaEstimate).where(BiaEstimate.process_id.in_(process_ids))
        )
        for bia_row in bia_result.scalars().all():
            bia_map[bia_row.process_id] = bia_row
        proc_result = await db.execute(
            select(BusinessProcess).where(BusinessProcess.id.in_(process_ids))
        )
        for proc_row in proc_result.scalars().all():
            process_map[proc_row.id] = proc_row

    def _bia_to_dimensions(proc: BusinessProcess, bia: BiaEstimate | None) -> dict:
        """Derive the 4 impact dimension labels from BIA data."""
        _rto_op = {"critical": "Muy Alto", "important": "Alto", "support": "Medio"}
        _rev_rep = {">50": "Alto", "20-50": "Medio", "<20": "Bajo"}
        op = _rto_op.get(proc.criticality, "Medio")
        rep = _rev_rep.get(proc.revenue_dependency, "Bajo")
        if proc.contractual_commitment and proc.contractual_commitment.get("exists"):
            rep = "Muy Alto" if rep == "Alto" else "Alto"
        norm = "Bajo"
        fin = "Medio"
        if bia:
            if bia.sn_active:
                sanction = (bia.breakdown or {}).get("params", {}).get("sanction_amount", 0)
                norm = "Muy Alto" if sanction > 500_000 else "Alto" if sanction > 50_000 else "Medio"
            bd = bia.breakdown or {}
            fin_level = bd.get("rto", {}).get("impact_level") or bd.get("mtpd", {}).get("impact_level")
            fin = fin_level if fin_level else "Medio"
        return {"impact_operational": op, "impact_financial": fin,
                "impact_normative": norm, "impact_reputational": rep}

    # 3. Backend pre-groups findings by (asset_id × threat_family)
    # Threat families collapse granular OWASP categories into broader risk families
    # so the AI receives fewer, richer groups instead of many fine-grained ones.
    from collections import defaultdict

    _CWE_TO_FAMILY: dict[str, str] = {
        "89": "injection", "79": "xss", "78": "injection",
        "22": "access_control", "798": "credentials",
        "306": "broken_auth", "639": "access_control",
        "327": "cryptography", "502": "integrity_failures",
        "918": "ssrf", "611": "injection", "352": "csrf", "330": "cryptography",
        "77": "injection", "319": "cryptography",
        "1104": "vulnerable_components", "693": "misconfiguration",
        "1021": "misconfiguration", "209": "data_exposure",
        "325": "cryptography", "472": "integrity_failures",
        "434": "access_control", "287": "broken_auth", "200": "data_exposure",
    }

    _THREAT_FAMILY: dict[str, str] = {
        "a03_injection": "injection", "injection": "injection",
        "sql_injection": "injection", "command_injection": "injection",
        "xxe": "injection", "ldap_injection": "injection",
        "xss": "xss", "cross_site_scripting": "xss",
        "csrf": "csrf",
        "ssrf": "ssrf", "a10_ssrf": "ssrf",
        "a01_broken_access_control": "access_control", "broken_access_control": "access_control",
        "access_control": "access_control", "insecure_direct_object_reference": "access_control",
        "path_traversal": "access_control", "file_inclusion": "access_control",
        "open_redirect": "access_control",
        "a07_identification_failures": "broken_auth", "broken_authentication": "broken_auth",
        "authentication": "broken_auth", "broken_auth": "broken_auth",
        "a02_cryptographic_failures": "cryptography", "weak_crypto": "cryptography",
        "cryptography": "cryptography", "insecure_transport": "cryptography",
        "missing_encryption": "cryptography", "sensitive_data_exposure": "cryptography",
        "a05_security_misconfiguration": "misconfiguration", "security_misconfiguration": "misconfiguration",
        "insecure_configuration": "misconfiguration", "missing_security_headers": "misconfiguration",
        "cross_domain_misconfiguration": "misconfiguration",
        "information_disclosure": "data_exposure", "server_leaks_information": "data_exposure",
        "hardcoded_credentials": "credentials",
        "a06_vulnerable_components": "vulnerable_components", "components": "vulnerable_components",
        "vulnerable_components": "vulnerable_components",
        "a04_insecure_design": "insecure_design", "business_logic": "insecure_design",
        "a09_logging_failures": "logging", "logging_monitoring": "logging",
        "a08_software_data_integrity": "integrity_failures",
        "insecure_deserialization": "integrity_failures",
    }

    _THREAT_FAMILY_LABEL: dict[str, str] = {
        "injection":            "Inyección (SQL / Comando / XXE)",
        "xss":                  "Cross-Site Scripting (XSS)",
        "csrf":                 "Falsificación de Petición (CSRF)",
        "ssrf":                 "Server-Side Request Forgery (SSRF)",
        "access_control":       "Control de Acceso y Autorización",
        "broken_auth":          "Autenticación y Gestión de Sesiones",
        "cryptography":         "Criptografía y Protección de Datos",
        "misconfiguration":     "Configuración de Seguridad Incorrecta",
        "data_exposure":        "Exposición de Información Sensible",
        "credentials":          "Credenciales y Secretos Expuestos",
        "vulnerable_components":"Componentes y Dependencias Vulnerables",
        "insecure_design":      "Diseño Inseguro y Lógica de Negocio",
        "logging":              "Registro y Monitoreo Insuficiente",
        "integrity_failures":   "Fallos de Integridad de Software",
    }

    def _threat_family(r: dict) -> str:
        owasp = (r.get("owasp_category") or "").strip().lower()
        if owasp and owasp in _THREAT_FAMILY:
            return _THREAT_FAMILY[owasp]
        cwe_raw = (r.get("cwe") or "").strip().upper().lstrip("CWE-")
        if cwe_raw and cwe_raw in _CWE_TO_FAMILY:
            return _CWE_TO_FAMILY[cwe_raw]
        cat = (r.get("category") or "").strip().lower()
        if cat and cat in _THREAT_FAMILY:
            return _THREAT_FAMILY[cat]
        for key, family in _THREAT_FAMILY.items():
            if key in cat:
                return family
        return cat or "other"

    def _slugify(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", text.lower().strip()).strip("_")[:120]

    # Group: key = (asset_id_str, threat_family) — broad families reduce duplicate scenarios
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        asset_key = str(r["asset_id"]) if r["asset_id"] else "no_asset"
        family = _threat_family(dict(r))
        groups[(asset_key, family)].append(dict(r))

    _SEV_RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}

    # Build scenario_groups payload for AI
    scenario_groups: list[dict] = []
    for gidx, ((asset_key, family_key), grp_rows) in enumerate(groups.items(), start=1):
        sample = grp_rows[0]
        asset_name = sample.get("asset_name") or ""
        aid = sample.get("asset_id")
        proc_id = asset_process_map.get(aid) if aid else None
        proc_obj = process_map.get(proc_id) if proc_id else None
        bia_obj = bia_map.get(proc_id) if proc_id else None

        max_sev_row = max(grp_rows, key=lambda r: _SEV_RANK.get((r.get("severity") or "low").lower(), 1))
        max_severity = max_sev_row.get("severity", "low")
        scanners = list({r.get("scanner") or "unknown" for r in grp_rows})
        finding_ids_in_group = [str(r["id"]) for r in grp_rows]
        summaries = [
            f"[{(r.get('severity') or 'low').upper()}] {(r.get('title') or '')[:80]}"
            + (f" — {(r.get('description') or '')[:150]}" if r.get("description") else "")
            for r in grp_rows[:8]
        ]
        family_label = _THREAT_FAMILY_LABEL.get(family_key, family_key.replace("_", " ").title())

        sg: dict = {
            "group_id": gidx,
            "asset_name": asset_name,
            "category": family_key,
            "category_label": family_label,
            "max_severity": max_severity,
            "finding_count": len(grp_rows),
            "scanner_types": scanners,
            "finding_ids": finding_ids_in_group,
            "finding_summaries": summaries,
        }
        if proc_obj:
            sg["business_process_id"] = str(proc_id)
            sg["business_process_name"] = proc_obj.name
            sg["business_process_criticality"] = proc_obj.criticality
            sg["revenue_dependency"] = proc_obj.revenue_dependency
        if bia_obj:
            if bia_obj.rto_hours is not None:
                sg["rto_hours"] = bia_obj.rto_hours
            if bia_obj.impact_24h is not None:
                sg["impact_24h_eur"] = bia_obj.impact_24h
            sg["sn_active"] = bia_obj.sn_active
        scenario_groups.append(sg)

    log.info("analizar_pregroups", total_groups=len(scenario_groups), total_findings=len(rows))

    # 4. AI call: score and title each pre-grouped scenario
    try:
        ai_result = await call_score_scenarios({
            "run_id": str(uuid.uuid4()),
            "project": {
                "name": project_row.name if project_row else str(project_id),
                "business_context": getattr(project_row, "description", None),
            },
            "scenario_groups": scenario_groups,
            "ai_provider": ai_provider,
            "api_key": api_key,
            "api_url": api_url,
            "model": model,
        })
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300] if exc.response else str(exc)
        raise HTTPException(status_code=502, detail=f"Error del proveedor IA: {detail}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error al contactar con la IA: {str(exc)[:200]}")

    ai_scenarios = ai_result.get("scenarios", [])
    # Index AI results by group_id for O(1) lookup
    ai_by_gid: dict[int, dict] = {s.get("group_id", 0): s for s in ai_scenarios}

    # 5. Delete existing scenarios and create new ones
    existing_ids_result = await db.execute(
        select(RiskScenario.id).where(RiskScenario.project_id == project_id)
    )
    existing_ids = [r[0] for r in existing_ids_result.all()]
    if existing_ids:
        await db.execute(
            delete(ScenarioFindingLink).where(ScenarioFindingLink.scenario_id.in_(existing_ids))
        )
        await db.execute(delete(RiskScenario).where(RiskScenario.project_id == project_id))

    _PROB_LEVEL = {1: "Muy Baja", 2: "Baja", 3: "Media", 4: "Alta", 5: "Muy Alta"}
    _IMP_LEVEL  = {1: "Muy Bajo",  2: "Bajo",  3: "Medio", 4: "Alto",  5: "Muy Alto"}
    _DIM_SCORE  = {"Muy Alto": 5, "Alto": 4, "Medio": 3, "Bajo": 2, "Muy Bajo": 1}

    def _bia_min_impact(dims: dict) -> int | None:
        """Floor impact score derived from BIA dimension labels."""
        scores = [_DIM_SCORE[v] for v in dims.values() if v in _DIM_SCORE]
        return max(scores) if scores else None

    created: list[RiskScenario] = []

    for sc_idx, sg in enumerate(scenario_groups, start=1):
        gid = sg["group_id"]
        ai_data = ai_by_gid.get(gid, {})

        # Business title → shown to management/CTO (stored in `title`)
        business_title = (ai_data.get("risk_title") or "").strip()
        if not business_title:
            proc_name = sg.get("business_process_name") or ""
            asset_label = sg.get("asset_name") or "activo"
            business_title = (
                f"Riesgo en {proc_name}: {sg['category_label']}"
                if proc_name else
                f"Riesgo de {sg['category_label']} en {asset_label}"
            )

        # Technical title → shown to security analysts (stored in `consequence`)
        technical_title = (ai_data.get("technical_title") or "").strip()
        if not technical_title:
            technical_title = f"{sg['category_label']} en {sg['asset_name'] or 'activo desconocido'}"

        prob = ai_data.get("probability")
        imp  = ai_data.get("impact")

        # Resolve process id
        assigned_process_id: uuid.UUID | None = None
        raw_proc_id = sg.get("business_process_id")
        if raw_proc_id:
            try:
                assigned_process_id = uuid.UUID(raw_proc_id)
            except (ValueError, TypeError):
                pass

        # BIA dimensions — prefer AI override, fall back to computed BIA
        bia_dimensions: dict = {}
        if assigned_process_id:
            proc_o = process_map.get(assigned_process_id)
            bia_o  = bia_map.get(assigned_process_id)
            if proc_o:
                bia_dimensions = _bia_to_dimensions(proc_o, bia_o)

        # BIA sets the floor: impact score cannot be lower than what BIA dictates
        if isinstance(imp, int) and bia_dimensions:
            bia_floor = _bia_min_impact(bia_dimensions)
            if bia_floor and imp < bia_floor:
                imp = bia_floor

        group_key_val = _slugify(technical_title) or f"scenario_{sc_idx}"

        scenario = RiskScenario(
            project_id=project_id,
            scenario_code=f"SC-{sc_idx:03d}",
            title=business_title,       # management/CTO view
            consequence=technical_title, # analyst/technical view
            group_key=group_key_val,
            status="prob_assessed" if not bia_dimensions else "impact_assessed",
            business_process_id=assigned_process_id,
            probability=prob if isinstance(prob, int) else None,
            prob_level=_PROB_LEVEL.get(prob) if isinstance(prob, int) else None,
            probability_rationale=ai_data.get("probability_rationale") or ai_data.get("risk_description"),
            impact=imp if isinstance(imp, int) else None,
            impact_level=_IMP_LEVEL.get(imp) if isinstance(imp, int) else None,
            impact_rationale=ai_data.get("impact_rationale") or (
                "Impacto derivado del BIA: "
                + ", ".join(f"{k.replace('impact_', '').capitalize()}={v}"
                            for k, v in bia_dimensions.items() if v)
                if bia_dimensions else None
            ),
            impact_operational=bia_dimensions.get("impact_operational") or ai_data.get("impact_operational"),
            impact_financial=bia_dimensions.get("impact_financial") or ai_data.get("impact_financial"),
            impact_normative=bia_dimensions.get("impact_normative") or ai_data.get("impact_normative"),
            impact_reputational=bia_dimensions.get("impact_reputational") or ai_data.get("impact_reputational"),
        )
        db.add(scenario)
        await db.flush()

        for fid_str in sg["finding_ids"]:
            try:
                db.add(ScenarioFindingLink(
                    scenario_id=scenario.id,
                    finding_id=uuid.UUID(fid_str),
                ))
            except (ValueError, TypeError):
                pass

        created.append(scenario)

    await db.flush()

    enriched_rows = await db.execute(
        select(
            RiskScenario,
            func.count(ScenarioFindingLink.finding_id).label("finding_count"),
            Asset.name.label("asset_name"),
        )
        .outerjoin(ScenarioFindingLink, ScenarioFindingLink.scenario_id == RiskScenario.id)
        .outerjoin(Asset, Asset.id == RiskScenario.asset_id)
        .where(RiskScenario.id.in_([s.id for s in created]))
        .group_by(RiskScenario.id, Asset.name)
        .order_by(RiskScenario.scenario_code)
    )
    return [_enrich(s, fc or 0, None, an) for s, fc, an in enriched_rows.all()]


# ─── generar fichas RN-xxx ────────────────────────────────────────────────────

@router.post("/projects/{project_id}/analisis:generar-fichas", response_model=list[dict])
async def generar_fichas(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    body: ConsolidateBody | None = None,
):
    from app.models.asset import Asset
    from app.models.finding import Finding
    from app.models.project import Project
    from app.models.risk import Risk
    from app.models.workspace import Workspace
    from app.modules.contexto.bia.models import BusinessProcess
    from app.shared.ai_gateway.tasks import call_risks_from_scenarios

    # Resolve AI provider: client preference → workspace first-enabled → legacy keys
    project_row = await db.get(Project, project_id)
    ai_provider = "gemini"
    api_key: str | None = None
    api_url: str | None = None
    model: str | None = None
    if project_row:
        ws = await db.get(Workspace, project_row.workspace_id)
        if ws and ws.ai_config:
            requested = body.ai_provider if body else None
            if requested:
                pconf = ws.ai_config.get("providers", {}).get(requested, {})
                if pconf and pconf.get("api_key"):
                    ai_provider = requested
                    api_key = pconf.get("api_key")
                    api_url = pconf.get("url")
                    model = body.model or pconf.get("model")
            if not api_key:
                for pname, pconf in ws.ai_config.get("providers", {}).items():
                    if pconf and pconf.get("api_key") and pconf.get("enabled", True):
                        ai_provider = pname
                        api_key = pconf.get("api_key")
                        api_url = pconf.get("url")
                        model = pconf.get("model")
                        break
            if not api_key:
                for pname in ("gemini", "anthropic", "openai"):
                    api_key = ws.ai_config.get(f"{pname}_api_key")
                    if api_key:
                        ai_provider = pname
                        break

    result = await db.execute(
        select(RiskScenario)
        .where(
            RiskScenario.project_id == project_id,
            RiskScenario.probability.isnot(None),
            RiskScenario.impact.isnot(None),
        )
        .order_by(RiskScenario.scenario_code)
    )
    scenarios = result.scalars().all()
    if not scenarios:
        raise HTTPException(
            status_code=422,
            detail="No hay escenarios con P e I evaluados. Completa primero /probabilidad y /impacto.",
        )

    scenario_ids = [s.id for s in scenarios]

    link_rows = await db.execute(
        select(
            ScenarioFindingLink.scenario_id,
            ScenarioFindingLink.finding_id,
            Finding.title,
            Finding.severity,
            Finding.category,
            Finding.owasp_category,
            Finding.cwe,
            Asset.name.label("asset_name"),
        )
        .join(Finding, ScenarioFindingLink.finding_id == Finding.id)
        .outerjoin(Asset, Finding.asset_id == Asset.id)
        .where(ScenarioFindingLink.scenario_id.in_(scenario_ids))
    )
    link_data = link_rows.mappings().all()

    findings_by_scenario: dict[uuid.UUID, list[dict]] = {s.id: [] for s in scenarios}
    finding_ids_by_scenario: dict[uuid.UUID, list[uuid.UUID]] = {s.id: [] for s in scenarios}
    for row in link_data:
        findings_by_scenario[row["scenario_id"]].append({
            "title": row["title"],
            "severity": row["severity"],
            "category": row["category"],
            "owasp_category": row["owasp_category"],
            "cwe": row["cwe"],
            "asset_name": row["asset_name"],
        })
        finding_ids_by_scenario[row["scenario_id"]].append(row["finding_id"])

    process_ids = list({s.business_process_id for s in scenarios if s.business_process_id})
    process_map: dict[uuid.UUID, str] = {}
    processes_context: list[dict] = []
    if process_ids:
        from app.modules.contexto.bia.models import BiaEstimate
        procs_result = await db.execute(
            select(BusinessProcess).where(BusinessProcess.id.in_(process_ids))
        )
        proc_obj_map: dict[uuid.UUID, BusinessProcess] = {
            p.id: p for p in procs_result.scalars().all()
        }
        process_map = {pid: p.name for pid, p in proc_obj_map.items()}

        bia_result = await db.execute(
            select(BiaEstimate).where(BiaEstimate.process_id.in_(process_ids))
        )
        bia_obj_map: dict[uuid.UUID, BiaEstimate] = {
            b.process_id: b for b in bia_result.scalars().all()
        }

        for pid, proc in proc_obj_map.items():
            bia = bia_obj_map.get(pid)
            rdep = proc.revenue_dependency
            entry: dict = {
                "id": str(pid),
                "name": proc.name,
                "criticality": proc.criticality,
                "revenue_dependency": rdep,
            }
            if bia:
                if bia.rto_hours is not None:
                    entry["rto_hours"] = bia.rto_hours
                if bia.impact_24h is not None:
                    entry["impact_24h_eur"] = bia.impact_24h
                entry["sn_active"] = bia.sn_active
            processes_context.append(entry)

    normative: dict = {}

    scenario_payloads = [
        {
            "scenario_code": s.scenario_code,
            "technical_label": s.consequence,                    # analyst ref (e.g. "XSS en AppWeb")
            "business_title": s.title or s.consequence,          # management ref (never None)
            "probability": s.probability,
            "prob_level": s.prob_level,
            "probability_rationale": s.probability_rationale,
            "impact": s.impact,
            "impact_level": s.impact_level,
            "impact_rationale": s.impact_rationale,
            "impact_operational": s.impact_operational,
            "impact_financial": s.impact_financial,
            "impact_normative": s.impact_normative,
            "impact_reputational": s.impact_reputational,
            "process_name": process_map.get(s.business_process_id, "") if s.business_process_id else "",
            "findings": findings_by_scenario.get(s.id, []),
        }
        for s in scenarios
    ]

    try:
        ai_result = await call_risks_from_scenarios({
            "run_id": str(uuid.uuid4()),
            "project": {
                "name": project_row.name if project_row else str(project_id),
                "business_context": getattr(project_row, "business_context", None),
            },
            "scenarios": scenario_payloads,
            "business_context": {"normative": normative, "processes": processes_context},
            "ai_provider": ai_provider,
            "api_key": api_key,
            "api_url": api_url,
            "model": model,
        })
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error al contactar con la IA: {str(exc)[:200]}")

    existing_codes = await db.execute(
        select(Risk.risk_code).where(
            Risk.project_id == project_id,
            Risk.risk_code.like("RN-%"),
        )
    )
    existing_nums = []
    for (code,) in existing_codes.all():
        try:
            existing_nums.append(int(code.split("-")[1]))
        except (IndexError, ValueError):
            pass
    next_num = max(existing_nums, default=0) + 1

    def _risk_level(score: float) -> str:
        if score >= 17:
            return "critical"
        if score >= 10:
            return "high"
        if score >= 5:
            return "medium"
        return "low"

    def _priority(score: float) -> str:
        if score >= 20:
            return "immediate"
        if score >= 12:
            return "short_term"
        if score >= 6:
            return "medium_term"
        return "long_term"

    raw_risks = ai_result.get("risks", [])
    ai_by_code: dict[str, dict] = {
        r["scenario_code"]: r
        for r in raw_risks
        if isinstance(r, dict) and r.get("scenario_code")
    }

    created_risks: list[dict] = []
    for scenario in scenarios:
        ai_data = ai_by_code.get(scenario.scenario_code, {})
        prob = scenario.probability
        impact = scenario.impact
        score = float(prob * impact)

        existing_risk = (await db.execute(
            select(Risk).where(Risk.scenario_id == scenario.id)
        )).scalar_one_or_none()

        ai_title = (ai_data.get("risk_title") or "").strip()
        # Fix double "Riesgo de Riesgo de..." that some models produce
        ai_title = re.sub(r'(?i)^riesgo\s+de\s+riesgo\s+de\s+', 'Riesgo de ', ai_title)
        if ai_title and "Riesgo de seguridad en " not in ai_title:
            risk_title = ai_title
        else:
            proc = process_map.get(scenario.business_process_id, "") if scenario.business_process_id else ""
            _t = (scenario.title or "").strip()
            # Avoid "Riesgo de Riesgo de..." when scenario.title already starts with Riesgo
            if _t.lower().startswith("riesgo"):
                risk_title = _t
            else:
                risk_title = f"Riesgo de {_t}" if _t else (f"Riesgo de seguridad en {proc}" if proc else "Riesgo de seguridad")
        risk_title = risk_title[:512]
        risk_description = ai_data.get("risk_description")
        business_impact_operational = ai_data.get("business_impact_operational")
        business_impact_financial = ai_data.get("business_impact_financial")
        business_impact_normative = ai_data.get("business_impact_normative")
        business_impact_reputational = ai_data.get("business_impact_reputational")
        risk_category = ai_data.get("risk_category", "security")
        affected_cia = ai_data.get("affected_cia", ["C"])
        ai_priority = ai_data.get("priority") or _priority(score)

        if existing_risk is None:
            risk = Risk(
                project_id=project_id,
                scenario_id=scenario.id,
                risk_code=f"RN-{next_num:03d}",
                risk_title=risk_title,
                risk_description=risk_description,
                business_impact_operational=business_impact_operational,
                business_impact_financial=business_impact_financial,
                business_impact_normative=business_impact_normative,
                business_impact_reputational=business_impact_reputational,
                risk_category=risk_category,
                probability=prob,
                impact=impact,
                risk_score=score,
                risk_level=_risk_level(score),
                affected_cia=affected_cia,
                likelihood_rationale=scenario.probability_rationale,
                impact_rationale=scenario.impact_rationale,
                impact_operational=scenario.impact_operational,
                impact_financial=scenario.impact_financial,
                impact_normative=scenario.impact_normative,
                impact_reputational=scenario.impact_reputational,
                prob_level=scenario.prob_level,
                impact_level=scenario.impact_level,
                business_process_id=scenario.business_process_id,
                methodology="iso_31000",
                assessed_by="scenario_assessment",
                priority=ai_priority,
                status="open",
            )
            db.add(risk)
            await db.flush()
            next_num += 1
        else:
            risk = existing_risk
            risk.risk_title = risk_title
            risk.risk_description = risk_description
            risk.business_impact_operational = business_impact_operational
            risk.business_impact_financial = business_impact_financial
            risk.business_impact_normative = business_impact_normative
            risk.business_impact_reputational = business_impact_reputational
            risk.risk_category = risk_category
            risk.affected_cia = affected_cia
            risk.priority = ai_priority
            risk.probability = prob
            risk.impact = impact
            risk.risk_score = score
            risk.risk_level = _risk_level(score)
            risk.impact_operational = scenario.impact_operational
            risk.impact_financial = scenario.impact_financial
            risk.impact_normative = scenario.impact_normative
            risk.impact_reputational = scenario.impact_reputational
            risk.prob_level = scenario.prob_level
            risk.impact_level = scenario.impact_level
            risk.business_process_id = scenario.business_process_id
            await db.flush()

        # Sync finding links from the scenario's escenario_hallazgos
        from app.models.risk import risk_finding_links
        fids = finding_ids_by_scenario.get(scenario.id, [])
        await db.execute(
            delete(risk_finding_links).where(risk_finding_links.c.risk_id == risk.id)
        )
        for fid in fids:
            await db.execute(
                risk_finding_links.insert().values(
                    risk_id=risk.id, finding_id=fid, is_primary=False
                )
            )

        scenario.status = "risk_generated"
        created_risks.append({
            "id": str(risk.id),
            "risk_code": risk.risk_code,
            "risk_title": risk.risk_title,
            "probability": risk.probability,
            "impact": risk.impact,
            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level,
            "priority": risk.priority,
            "business_process_id": str(risk.business_process_id) if risk.business_process_id else None,
        })

    return created_risks


# ─── aplicar catálogo de traducción a riesgos existentes ─────────────────────

@router.post("/projects/{project_id}/risks:aplicar-catalogo")
async def aplicar_catalogo_a_riesgos(
    project_id: uuid.UUID,
    db: DB,
    _user: CurrentUser,
):
    """
    Renombra todos los RN-xxx del proyecto usando el Catálogo Maestro de Traducción.
    No usa IA — aplica el mapeo de familia técnica → nombre ejecutivo directamente.
    Formato: '[Nombre del Catálogo] en [activo]'
    """
    from app.models.risk import Risk

    result = await db.execute(
        select(Risk, RiskScenario)
        .join(RiskScenario, Risk.scenario_id == RiskScenario.id, isouter=True)
        .where(Risk.project_id == project_id)
    )
    rows = result.all()

    updated = 0
    skipped = 0
    for risk, scenario in rows:
        if not scenario:
            skipped += 1
            continue

        consequence = scenario.consequence or ""
        family = _family_from_consequence(consequence)
        if not family:
            skipped += 1
            continue

        business_name = _CATALOG_BUSINESS_RISK.get(family)
        if not business_name:
            skipped += 1
            continue

        asset = _asset_from_consequence(consequence)
        # También intentamos el nombre del proceso de negocio si hay
        proc_name = None
        if scenario.business_process_id:
            from app.modules.contexto.bia.models import BusinessProcess
            proc = (await db.execute(
                select(BusinessProcess).where(BusinessProcess.id == scenario.business_process_id)
            )).scalar_one_or_none()
            if proc:
                proc_name = proc.name

        if proc_name and asset:
            new_title = f"{business_name} — {proc_name} ({asset})"
        elif asset:
            new_title = f"{business_name} en {asset}"
        else:
            new_title = business_name

        risk.risk_title = new_title[:512]
        # También actualiza scenario.title para coherencia
        scenario.title = new_title[:512]
        updated += 1

    await db.commit()
    log.info("catalog_rename_done", project_id=str(project_id), updated=updated, skipped=skipped)
    return {"updated": updated, "skipped": skipped, "total": len(rows)}


# ─── hallazgos de un escenario ───────────────────────────────────────────────

@router.get("/escenarios/{scenario_id}/hallazgos")
async def get_scenario_hallazgos(
    scenario_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    from app.models.asset import Asset
    from app.models.finding import Finding

    _SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

    rows = await db.execute(
        select(
            Finding.id,
            Finding.title,
            Finding.severity,
            Finding.category,
            Finding.owasp_category,
            Finding.cwe,
            Finding.description,
            Finding.file_path,
            Finding.line_start,
            Finding.scanner,
            Finding.finding_type,
            Finding.confidence,
            Asset.name.label("asset_name"),
        )
        .join(ScenarioFindingLink, ScenarioFindingLink.finding_id == Finding.id)
        .outerjoin(Asset, Finding.asset_id == Asset.id)
        .where(ScenarioFindingLink.scenario_id == scenario_id)
    )
    findings = [
        {
            "id":             str(r["id"]),
            "title":          r["title"],
            "severity":       r["severity"],
            "category":       r["category"],
            "owasp_category": r["owasp_category"],
            "cwe":            r["cwe"],
            "description":    r["description"],
            "file_path":      r["file_path"],
            "line_start":     r["line_start"],
            "scanner":        r["scanner"],
            "finding_type":   r["finding_type"],
            "confidence":     r["confidence"],
            "asset_name":     r["asset_name"],
        }
        for r in rows.mappings().all()
    ]
    findings.sort(key=lambda f: _SEV_RANK.get((f["severity"] or "info").lower(), 9))
    return findings


# ─── eliminar escenario ───────────────────────────────────────────────────────

@router.delete("/escenarios/{scenario_id}", status_code=204)
async def delete_escenario(
    scenario_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    scenario = await db.get(RiskScenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Escenario no encontrado")
    await db.execute(
        delete(ScenarioFindingLink).where(ScenarioFindingLink.scenario_id == scenario_id)
    )
    await db.delete(scenario)
    await db.flush()


# ─── override manual probabilidad ────────────────────────────────────────────

@router.patch("/escenarios/{scenario_id}/probabilidad", response_model=RiskScenarioOut)
async def update_probabilidad(
    scenario_id: uuid.UUID,
    body: ScenarioProbabilityUpdate,
    db: DB,
    current_user: CurrentUser,
):
    scenario = await db.get(RiskScenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Escenario no encontrado")

    scenario.probability = body.probability
    scenario.prob_level = body.prob_level
    scenario.probability_rationale = body.probability_rationale
    if scenario.status == "pending":
        scenario.status = "prob_assessed"

    from app.models.risk import Risk
    risk = (await db.execute(select(Risk).where(Risk.scenario_id == scenario_id))).scalar_one_or_none()
    if risk:
        risk.probability = scenario.probability
        risk.prob_level = scenario.prob_level
        risk.likelihood_rationale = scenario.probability_rationale
        from app.api.v1.risks import _compute_risk_score
        score, level = _compute_risk_score(risk.probability, risk.impact)
        risk.risk_score = score
        risk.risk_level = level
    await db.flush()
    await db.refresh(scenario)
    return RiskScenarioOut.model_validate(scenario)


# ─── asignar impacto ──────────────────────────────────────────────────────────

@router.patch("/escenarios/{scenario_id}/impacto", response_model=RiskScenarioOut)
async def update_impacto(
    scenario_id: uuid.UUID,
    body: ScenarioImpactUpdate,
    db: DB,
    current_user: CurrentUser,
):
    scenario = await db.get(RiskScenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Escenario no encontrado")

    scenario.business_process_id = body.business_process_id
    scenario.impact = body.impact
    scenario.impact_level = _SCORE_LEVEL.get(body.impact, body.impact_level)
    scenario.impact_rationale = body.impact_rationale
    scenario.impact_operational = body.impact_operational
    scenario.impact_financial = body.impact_financial
    scenario.impact_normative = body.impact_normative
    scenario.impact_reputational = body.impact_reputational
    if scenario.status in ("pending", "prob_assessed"):
        scenario.status = "impact_assessed"

    from app.models.risk import Risk
    risk = (await db.execute(select(Risk).where(Risk.scenario_id == scenario_id))).scalar_one_or_none()
    if risk:
        risk.impact = scenario.impact
        risk.impact_level = scenario.impact_level
        risk.impact_rationale = scenario.impact_rationale
        risk.impact_operational = scenario.impact_operational
        risk.impact_financial = scenario.impact_financial
        risk.impact_normative = scenario.impact_normative
        risk.impact_reputational = scenario.impact_reputational
        
        from app.api.v1.risks import _compute_risk_score
        score, level = _compute_risk_score(risk.probability, risk.impact)
        risk.risk_score = score
        risk.risk_level = level
    await db.flush()
    await db.refresh(scenario)
    return RiskScenarioOut.model_validate(scenario)
