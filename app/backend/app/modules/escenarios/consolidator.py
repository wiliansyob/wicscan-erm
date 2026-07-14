"""
Consolidator de escenarios — agrupa findings directamente en escenarios de riesgo.

No depende de contextual_findings. Lee findings brutos filtrados por proyecto.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.escenarios.models import RiskScenario, ScenarioFindingLink

_SEV_ORDER: dict[str, int] = {
    "critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0, "informational": 0,
}

# Traducción de categorías OWASP/técnicas → español
_CAT_ES: dict[str, str] = {
    # OWASP Top 10 2021
    "a01_broken_access_control":       "Control de Acceso Roto",
    "a02_cryptographic_failures":      "Fallos Criptográficos",
    "a03_injection":                   "Inyección",
    "a04_insecure_design":             "Diseño Inseguro",
    "a05_security_misconfiguration":   "Configuración de Seguridad Incorrecta",
    "a06_vulnerable_components":       "Componentes con Vulnerabilidades Conocidas",
    "a07_identification_failures":     "Fallos de Identificación y Autenticación",
    "a08_software_data_integrity":     "Fallos de Integridad de Software y Datos",
    "a09_logging_failures":            "Fallos de Registro y Monitoreo",
    "a10_ssrf":                        "Falsificación de Solicitudes del Servidor (SSRF)",
    # Categorías comunes de scanners
    "weak_crypto":                     "Criptografía Débil",
    "hardcoded_credentials":           "Credenciales Embebidas en Código",
    "security_misconfiguration":       "Configuración de Seguridad Incorrecta",
    "server_leaks_information":        "Exposición de Información del Servidor",
    "cross_domain_misconfiguration":   "Mala Configuración entre Dominios",
    "injection":                       "Inyección",
    "sql_injection":                   "Inyección SQL",
    "command_injection":               "Inyección de Comandos",
    "xss":                             "Cross-Site Scripting (XSS)",
    "cross_site_scripting":            "Cross-Site Scripting (XSS)",
    "csrf":                            "Falsificación de Solicitudes (CSRF)",
    "ssrf":                            "Falsificación de Solicitudes del Servidor (SSRF)",
    "xxe":                             "Entidades Externas XML (XXE)",
    "authentication":                  "Fallos de Autenticación",
    "broken_authentication":           "Autenticación Rota",
    "access_control":                  "Control de Acceso",
    "broken_access_control":           "Control de Acceso Roto",
    "insecure_deserialization":        "Deserialización Insegura",
    "sensitive_data_exposure":         "Exposición de Datos Sensibles",
    "path_traversal":                  "Traversal de Rutas",
    "open_redirect":                   "Redirección Abierta",
    "information_disclosure":          "Exposición de Información",
    "insecure_configuration":          "Configuración Insegura",
    "missing_security_headers":        "Cabeceras de Seguridad Faltantes",
    "insecure_direct_object_reference":"Referencia Directa Insegura a Objetos (IDOR)",
    "file_inclusion":                  "Inclusión de Archivos",
    "business_logic":                  "Lógica de Negocio",
    "api_security":                    "Seguridad de API",
    "cryptography":                    "Criptografía",
    "logging_monitoring":              "Registro y Monitoreo",
    "components":                      "Componentes Vulnerables",
    "manual_review":                   "Revisión Manual",
    "other":                           "Otros",
}


def _translate_category(raw: str) -> str:
    """Devuelve la etiqueta en español para una clave de categoría."""
    key = raw.lower().strip().replace(" ", "_").replace("-", "_")
    if key in _CAT_ES:
        return _CAT_ES[key]
    # Intento parcial: busca si alguna clave conocida está contenida en el raw
    for known_key, label in _CAT_ES.items():
        if known_key in key:
            return label
    # Fallback: capitalizar y limpiar el raw
    return raw.replace("_", " ").replace("-", " ").title()


def group_findings_into_scenarios(finding_contexts: list[dict]) -> list[dict]:
    """Agrupa findings por vector técnico (categoría de vulnerabilidad, activo) en escenarios.

    Dos tipos distintos de vulnerabilidad en el mismo activo producen DOS escenarios separados.
    El proceso de negocio se registra como metadato para enriquecer el escenario, no como clave de agrupación.
    """
    groups: dict[tuple[str, str | None], list[dict]] = defaultdict(list)

    for fc in finding_contexts:
        owasp = (fc.get("owasp_category") or "").strip()
        cat   = (fc.get("category") or "").strip()
        vuln_key = owasp if owasp else (cat if cat else "other")
        asset_id = fc.get("asset_id")

        groups[(vuln_key, asset_id)].append(fc)

    result = []
    for group_key in sorted(groups, key=lambda k: (k[0], k[1] or "")):
        items = groups[group_key]
        vuln_key, asset_id = group_key

        primary    = items[0]
        asset_name = primary.get("asset_name")

        gk_display  = _translate_category(vuln_key)
        consequence = f"{gk_display} en {asset_name}" if asset_name else gk_display

        max_item     = max(items, key=lambda x: _SEV_ORDER.get((x.get("severity") or "low").lower(), 0))
        max_severity = max_item.get("severity") or "low"

        combined_group_key = f"{vuln_key}::{asset_id}" if asset_id else vuln_key

        # Proceso predominante entre los findings del grupo (por votación de peso)
        process_votes: dict[str, int] = {}
        for fc in items:
            pid = fc.get("process_id")
            if pid:
                process_votes[pid] = process_votes.get(pid, 0) + 1
        top_process_id = max(process_votes, key=lambda k: process_votes[k]) if process_votes else None
        top_process_name = next(
            (fc.get("process_name") for fc in items if fc.get("process_id") == top_process_id), None
        ) if top_process_id else None

        result.append({
            "group_key":     combined_group_key,
            "consequence":   consequence,
            "asset_id":      asset_id,
            "asset_name":    asset_name,
            "process_id":    top_process_id,
            "process_name":  top_process_name,
            "finding_ids":   [fc["finding_id"] for fc in items],
            "max_severity":  max_severity,
            "finding_count": len(items),
        })

    return result


@dataclass
class ConsolidateStats:
    findings_processed: int
    scenarios_created: int
    scenarios_updated: int


async def consolidate_scenarios(
    db: AsyncSession,
    project_id: uuid.UUID,
    finding_ids: list[uuid.UUID] | None = None,
) -> tuple[ConsolidateStats, list[RiskScenario]]:
    """Agrupa findings en RiskScenario (escenarios). Idempotente.

    Si se pasan finding_ids solo consolida esos; si no, todos los abiertos del proyecto.
    """
    from app.models.finding import Finding
    from app.models.scan import Scan, ScanSession
    from app.models.asset import Asset
    from app.modules.contexto.bia.models import AssetProcessLink, BusinessProcess

    stmt = (
        select(
            Finding.id.label("finding_id"),
            Finding.category,
            Finding.owasp_category,
            Finding.severity,
            Finding.asset_id,
            Asset.name.label("asset_name"),
        )
        .join(Scan, Finding.scan_id == Scan.id)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .outerjoin(Asset, Finding.asset_id == Asset.id)
        .where(
            ScanSession.project_id == project_id,
            Finding.status == "open",
        )
    )
    if finding_ids:
        stmt = stmt.where(Finding.id.in_(finding_ids))

    rows = (await db.execute(stmt)).mappings().all()

    # Build asset → primary process mapping (highest weight wins per asset)
    asset_ids_set = {r["asset_id"] for r in rows if r["asset_id"]}
    asset_process_map: dict[uuid.UUID, tuple[str, str]] = {}
    if asset_ids_set:
        links = await db.execute(
            select(
                AssetProcessLink.asset_id,
                AssetProcessLink.process_id,
                BusinessProcess.name.label("process_name"),
                AssetProcessLink.weight,
            )
            .join(BusinessProcess, AssetProcessLink.process_id == BusinessProcess.id)
            .where(AssetProcessLink.asset_id.in_(asset_ids_set))
            .order_by(AssetProcessLink.weight.desc())
        )
        for lrow in links.mappings().all():
            aid = lrow["asset_id"]
            if aid not in asset_process_map:
                asset_process_map[aid] = (str(lrow["process_id"]), lrow["process_name"])

    finding_contexts = []
    for r in rows:
        asset_proc = asset_process_map.get(r["asset_id"]) if r["asset_id"] else None
        finding_contexts.append({
            "finding_id":     str(r["finding_id"]),
            "asset_id":       str(r["asset_id"]) if r["asset_id"] else None,
            "asset_name":     r["asset_name"],
            "category":       r["category"] or "",
            "owasp_category": r["owasp_category"],
            "severity":       r["severity"] or "low",
            "process_id":     asset_proc[0] if asset_proc else None,
            "process_name":   asset_proc[1] if asset_proc else None,
        })

    groups = group_findings_into_scenarios(finding_contexts)

    existing_result = await db.execute(
        select(RiskScenario).where(RiskScenario.project_id == project_id)
    )
    existing: dict[str, RiskScenario] = {
        s.group_key: s for s in existing_result.scalars().all()
    }

    created = 0
    updated = 0
    upserted: list[RiskScenario] = []
    sc_code_count = len(existing)

    for group in groups:
        gk       = group["group_key"]
        scenario = existing.get(gk)

        proc_uuid = uuid.UUID(group["process_id"]) if group.get("process_id") else None

        if scenario is None:
            sc_code_count += 1
            scenario = RiskScenario(
                project_id=project_id,
                scenario_code=f"SC-{sc_code_count:03d}",
                consequence=group["consequence"],
                group_key=gk,
                asset_id=uuid.UUID(group["asset_id"]) if group["asset_id"] else None,
                business_process_id=proc_uuid,
                status="pending",
            )
            db.add(scenario)
            await db.flush()
            created += 1
        else:
            scenario.consequence = group["consequence"]
            scenario.asset_id = uuid.UUID(group["asset_id"]) if group["asset_id"] else None
            if proc_uuid is not None:
                scenario.business_process_id = proc_uuid
            updated += 1

        await db.execute(
            delete(ScenarioFindingLink).where(ScenarioFindingLink.scenario_id == scenario.id)
        )
        for finding_id_str in group["finding_ids"]:
            db.add(ScenarioFindingLink(
                scenario_id=scenario.id,
                finding_id=uuid.UUID(finding_id_str),
            ))

        upserted.append(scenario)

    await db.flush()

    return ConsolidateStats(
        findings_processed=len(finding_contexts),
        scenarios_created=created,
        scenarios_updated=updated,
    ), upserted
