import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from urllib.parse import quote
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.models.risk import Risk, RiskTreatment
from app.schemas.common import PaginatedResponse
from app.schemas.risk import RiskCreate, RiskMatrixData, RiskOut, RiskTreatmentCreate, RiskTreatmentOut, RiskUpdate, RiskTreatmentUpdate
from app.modules.contexto.bia.excel_export import build_risks_excel

router = APIRouter(prefix="/risks", tags=["risks"])


async def _get_risk_or_404(risk_id: uuid.UUID, workspace_id: uuid.UUID, db: AsyncSession) -> Risk:
    result = await db.execute(
        select(Risk)
        .join(Project, Risk.project_id == Project.id)
        .where(Risk.id == risk_id, Project.workspace_id == workspace_id)
    )
    risk = result.scalar_one_or_none()
    if not risk:
        raise NotFoundError("Risk", str(risk_id))
    return risk


def _compute_risk_score(probability: int, impact: int) -> tuple[float, str]:
    score = float(probability * impact)
    if score >= 20:
        level = "critical"
    elif score >= 12:
        level = "high"
    elif score >= 6:
        level = "medium"
    else:
        level = "low"
    return score, level


@router.get("", response_model=PaginatedResponse[RiskOut])
async def list_risks(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    project_id: uuid.UUID | None = Query(None),
    asset_id: uuid.UUID | None = Query(None),
    risk_level: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    q = (
        select(Risk)
        .join(Project, Risk.project_id == Project.id)
        .where(Project.workspace_id == user.workspace_id)
    )
    if project_id:
        q = q.where(Risk.project_id == project_id)
    if asset_id:
        q = q.where(Risk.asset_id == asset_id)
    if risk_level:
        q = q.where(Risk.risk_level == risk_level)
    if status:
        q = q.where(Risk.status == status)

    from sqlalchemy.orm import selectinload
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    risks = (await db.execute(
        q.options(selectinload(Risk.findings)).order_by(Risk.risk_score.desc()).offset((page - 1) * size).limit(size)
    )).scalars().all()
    return PaginatedResponse(items=list(risks), total=total, page=page, size=size, pages=max(1, -(-total // size)))


@router.get("/projects/{project_id}/export", response_class=StreamingResponse)
async def export_risks_excel(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.workspace_id == user.workspace_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))

    pid = str(project_id)
    q = text("""
        WITH numbered_assets AS (
            SELECT id, 'ACT-' || LPAD(ROW_NUMBER() OVER(ORDER BY created_at ASC)::text, 3, '0') as asset_code
            FROM assets
            WHERE project_id = :pid
        )
        SELECT
            r.risk_code,
            r.risk_title,
            r.risk_description,
            r.business_impact_operational,
            r.business_impact_financial,
            r.business_impact_normative,
            r.business_impact_reputational,
            r.probability,
            r.impact,
            r.risk_score,
            r.risk_level,
            r.priority,
            e.prob_level,
            e.impact_operational,
            e.impact_financial,
            e.impact_normative,
            e.impact_reputational,
            STRING_AGG(DISTINCT fa.name, chr(10))   AS asset_names,
            STRING_AGG(DISTINCT na.asset_code, chr(10)) AS asset_ids,
            STRING_AGG(DISTINCT bp.name, chr(10))   AS process_names,
            STRING_AGG(DISTINCT f.finding_code, ', ') AS finding_codes,
            MAX(bp.criticality)                      AS proc_criticality,
            MAX(bp.revenue_dependency)               AS proc_revenue_dep,
            MAX(bia.rto_hours)                       AS bia_rto_hours,
            MAX(bia.impact_24h)                      AS bia_impact_24h,
            BOOL_OR(bia.sn_active)                   AS bia_sn_active
        FROM riesgos r
        LEFT JOIN escenarios e    ON r.scenario_id = e.id
        LEFT JOIN escenario_hallazgos eh ON eh.scenario_id = e.id
        LEFT JOIN findings f      ON f.id = eh.finding_id
        LEFT JOIN assets fa       ON fa.id = COALESCE(r.asset_id, e.asset_id, f.asset_id)
        LEFT JOIN numbered_assets na ON na.id = fa.id
        LEFT JOIN activo_proceso_links apl ON apl.asset_id = fa.id
        LEFT JOIN procesos_negocio bp ON bp.id = COALESCE(r.business_process_id, e.business_process_id, apl.process_id)
        LEFT JOIN estimaciones_bia bia ON bia.process_id = bp.id
        WHERE r.project_id = :pid
        GROUP BY
            r.id, r.risk_code, r.risk_title, r.risk_description,
            r.business_impact_operational, r.business_impact_financial, r.business_impact_normative, r.business_impact_reputational,
            r.probability, r.impact, r.risk_score, r.risk_level, r.priority,
            e.prob_level, e.impact_operational, e.impact_financial, e.impact_normative, e.impact_reputational
        ORDER BY r.risk_code NULLS LAST
    """)
    rows = [dict(r._mapping) for r in (await db.execute(q, {"pid": pid})).fetchall()]

    buf = build_risks_excel(rows, project.name)
    safe_name = quote(f"Registro_Riesgos_{project.name}.xlsx", safe="")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )


@router.get("/matrix", response_model=RiskMatrixData)
async def get_risk_matrix(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    project_id: uuid.UUID | None = Query(None),
    asset_id: uuid.UUID | None = Query(None),
):
    q = (
        select(Risk)
        .join(Project, Risk.project_id == Project.id)
        .where(Project.workspace_id == user.workspace_id, Risk.status.notin_(["mitigated", "accepted"]))
    )
    if project_id:
        q = q.where(Risk.project_id == project_id)
    if asset_id:
        q = q.where(Risk.asset_id == asset_id)
    risks = (await db.execute(q)).scalars().all()

    matrix = [[0] * 5 for _ in range(5)]
    risk_positions = []
    level_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for r in risks:
        p_idx = min(4, max(0, r.probability - 1))
        i_idx = min(4, max(0, r.impact - 1))
        matrix[4 - p_idx][i_idx] += 1
        risk_positions.append({
            "id": str(r.id),
            "title": r.risk_title,
            "level": r.risk_level,
            "probability_idx": p_idx,
            "impact_idx": i_idx,
        })
        level_counts[r.risk_level] = level_counts.get(r.risk_level, 0) + 1

    return RiskMatrixData(
        matrix=matrix,
        risks=risk_positions,
        summary={**level_counts, "total": len(risks)},
    )


@router.post("", response_model=RiskOut, status_code=201)
async def create_risk(
    payload: RiskCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    project_id: uuid.UUID = Query(...),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.workspace_id == user.workspace_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Project", str(project_id))

    count_result = await db.execute(
        select(func.count(Risk.id)).where(Risk.project_id == project_id)
    )
    next_num = (count_result.scalar() or 0) + 1
    risk_code = f"R-{next_num:03d}"

    score, level = _compute_risk_score(payload.probability, payload.impact)
    risk = Risk(
        project_id=project_id,
        asset_id=payload.asset_id,
        risk_code=risk_code,
        risk_title=payload.risk_title,
        risk_description=payload.risk_description,
        business_impact_desc=payload.business_impact_desc,
        risk_category=payload.risk_category,
        probability=payload.probability,
        impact=payload.impact,
        risk_score=score,
        risk_level=level,
        methodology=payload.methodology,
        assessed_by="manual",
    )
    db.add(risk)
    await db.flush()
    await db.refresh(risk)
    return risk


@router.get("/{risk_id}", response_model=RiskOut)
async def get_risk(risk_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await _get_risk_or_404(risk_id, user.workspace_id, db)


@router.patch("/{risk_id}", response_model=RiskOut)
async def update_risk(
    risk_id: uuid.UUID,
    payload: RiskUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    risk = await _get_risk_or_404(risk_id, user.workspace_id, db)
    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(risk, field, value)

    if "probability" in updates or "impact" in updates:
        score, level = _compute_risk_score(risk.probability, risk.impact)
        risk.risk_score = score
        risk.risk_level = level

    if risk.scenario_id and any(k in updates for k in ("probability", "impact", "likelihood_rationale", "impact_rationale")):
        from app.modules.escenarios.models import RiskScenario
        scenario = (await db.execute(select(RiskScenario).where(RiskScenario.id == risk.scenario_id))).scalar_one_or_none()
        if scenario:
            _PROB_LEVEL = {1: "Muy Baja", 2: "Baja", 3: "Media", 4: "Alta", 5: "Muy Alta"}
            _IMP_LEVEL  = {1: "Muy Bajo",  2: "Bajo",  3: "Medio", 4: "Alto",  5: "Muy Alto"}
            if "probability" in updates:
                scenario.probability = risk.probability
                scenario.prob_level = _PROB_LEVEL.get(risk.probability, "Media")
            if "impact" in updates:
                scenario.impact = risk.impact
                scenario.impact_level = _IMP_LEVEL.get(risk.impact, "Medio")
            if "likelihood_rationale" in updates:
                scenario.probability_rationale = updates["likelihood_rationale"]
            if "impact_rationale" in updates:
                scenario.impact_rationale = updates["impact_rationale"]

    return risk


@router.patch("/{risk_id}/confirm", response_model=RiskOut)
async def confirm_risk(
    risk_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    risk = await _get_risk_or_404(risk_id, user.workspace_id, db)
    risk.status = "in_progress"
    risk.confirmed_by = user.id
    risk.confirmed_at = datetime.now(timezone.utc)
    risk.assessed_by = "hybrid" if risk.assessed_by == "ai" else risk.assessed_by
    return risk


@router.patch("/{risk_id}/accept", response_model=RiskOut)
async def accept_risk(
    risk_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    risk = await _get_risk_or_404(risk_id, user.workspace_id, db)
    risk.status = "accepted"
    return risk


@router.post("/merge", response_model=RiskOut)
async def merge_risks(
    payload: dict,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Fusiona dos o más riesgos en uno solo.

    El riesgo con mayor score se convierte en el principal.
    Todos los finding_ids de los demás se transfieren al principal.
    La probabilidad se recalcula con el bonus por cobertura total.
    Los riesgos secundarios se eliminan.
    """
    from sqlalchemy import insert, delete
    from app.models.risk import risk_finding_links
    from app.services.risk_engine import apply_coverage_bonus

    risk_ids: list[str] = payload.get("risk_ids", [])
    if len(risk_ids) < 2:
        raise HTTPException(status_code=422, detail="Se necesitan al menos 2 riesgos para fusionar")

    risks: list[Risk] = []
    for rid in risk_ids:
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(Risk)
            .options(selectinload(Risk.findings))
            .join(Project, Risk.project_id == Project.id)
            .where(Risk.id == uuid.UUID(rid), Project.workspace_id == user.workspace_id)
        )
        r = result.scalar_one_or_none()
        if r:
            risks.append(r)

    if len(risks) < 2:
        raise HTTPException(status_code=404, detail="Uno o más riesgos no encontrados")

    # El riesgo con mayor score es el principal (o el especificado)
    keep_id = payload.get("keep_id")
    if keep_id:
        primary = next((r for r in risks if str(r.id) == keep_id), None) or max(risks, key=lambda r: r.risk_score)
    else:
        primary = max(risks, key=lambda r: r.risk_score)

    secondary_risks = [r for r in risks if r.id != primary.id]

    # Recopilar todos los finding_ids únicos de los riesgos secundarios
    secondary_finding_ids: set[uuid.UUID] = set()
    for sr in secondary_risks:
        for f in (sr.findings or []):
            secondary_finding_ids.add(f.id)

    # Obtener finding_ids ya vinculados al principal
    existing_primary_ids: set[uuid.UUID] = {f.id for f in (primary.findings or [])}

    # Transferir finding_ids de los secundarios al principal (sin duplicar)
    new_finding_ids = secondary_finding_ids - existing_primary_ids
    for fid in new_finding_ids:
        await db.execute(
            insert(risk_finding_links).values(
                risk_id=primary.id,
                finding_id=fid,
                is_primary=False,
            )
        )

    # Recalcular probabilidad con bonus por cobertura total
    total_findings = len(existing_primary_ids) + len(new_finding_ids)
    primary.probability = apply_coverage_bonus(primary.probability, total_findings)
    primary.risk_score, primary.risk_level = _compute_risk_score(primary.probability, primary.impact)
    primary.assessed_by = "hybrid"

    # Eliminar riesgos secundarios
    for sr in secondary_risks:
        await db.execute(delete(Risk).where(Risk.id == sr.id))

    await db.flush()
    await db.refresh(primary)
    return primary


@router.post("/{risk_id}/treatments/suggest")
async def suggest_treatments(
    risk_id: uuid.UUID,
    payload: dict,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Call AI gateway to suggest treatment actions for a risk."""
    from sqlalchemy.orm import selectinload
    import httpx
    from app.config import get_settings

    result = await db.execute(
        select(Risk)
        .options(selectinload(Risk.findings))
        .join(Project, Risk.project_id == Project.id)
        .where(Risk.id == risk_id, Project.workspace_id == user.workspace_id)
    )
    risk = result.scalar_one_or_none()
    if not risk:
        raise HTTPException(status_code=404, detail="Riesgo no encontrado")

    risk_dict = {
        "risk_code": risk.risk_code,
        "risk_title": risk.risk_title,
        "risk_description": risk.risk_description,
        "risk_level": risk.risk_level,
        "probability": risk.probability,
        "impact": risk.impact,
        "risk_score": float(risk.risk_score or 0),
        "impact_operational": risk.impact_operational,
        "impact_financial": risk.impact_financial,
        "impact_normative": risk.impact_normative,
        "impact_reputational": risk.impact_reputational,
    }
    findings_list = [
        {
            "id": str(f.id),
            "title": f.title,
            "severity": f.severity,
            "category": f.category,
            "cwe": f.cwe,
            "scanner": f.scanner,
        }
        for f in (risk.findings or [])
    ]

    # Load workspace ai_config to resolve api_key/url/model for the selected provider
    from app.models.workspace import Workspace
    workspace = await db.get(Workspace, user.workspace_id)
    ai_config = (workspace.ai_config or {}) if workspace else {}
    providers_cfg = ai_config.get("providers", {})

    requested_provider = payload.get("ai_provider", "gemini")
    prov_cfg = providers_cfg.get(requested_provider, {})

    api_key = prov_cfg.get("api_key") or None
    api_url = prov_cfg.get("url") or None
    model   = payload.get("model") or prov_cfg.get("model") or None

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.AI_GATEWAY_URL}/api/v1/analyze/treatment-plan",
                json={
                    "risk": risk_dict,
                    "findings": findings_list,
                    "ai_provider": requested_provider,
                    "model": model,
                    "api_key": api_key,
                    "api_url": api_url,
                },
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Error del proveedor de IA: {exc.response.text[:200]}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error al conectar con el gateway de IA: {str(exc)}")


@router.delete("/{risk_id}", status_code=204)
async def delete_risk(
    risk_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import delete as sql_delete
    from app.modules.escenarios.models import RiskScenario

    risk = await _get_risk_or_404(risk_id, user.workspace_id, db)

    # Reset linked scenario status so it can be re-converted
    if risk.scenario_id:
        scenario = await db.get(RiskScenario, risk.scenario_id)
        if scenario and scenario.status == "risk_generated":
            scenario.status = "impact_assessed"

    await db.execute(sql_delete(Risk).where(Risk.id == risk.id))
    return None


@router.post("/{risk_id}/treatments", response_model=RiskTreatmentOut, status_code=201)
async def add_treatment(
    risk_id: uuid.UUID,
    payload: RiskTreatmentCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    risk = await _get_risk_or_404(risk_id, user.workspace_id, db)
    treatment = RiskTreatment(risk_id=risk.id, **payload.model_dump())
    db.add(treatment)
    await db.flush()

    if payload.expected_risk_reduction:
        residual = round(risk.risk_score * (1.0 - min(0.9, payload.expected_risk_reduction / 100)), 2)
        _, residual_level = _compute_risk_score(
            max(1, int(residual ** 0.5)), max(1, int(residual ** 0.5))
        )
        risk.residual_score = residual
        risk.residual_level = residual_level

    if risk.status == "open":
        risk.status = "in_progress"

    await db.refresh(treatment)
    return treatment


@router.get("/{risk_id}/treatments", response_model=list[RiskTreatmentOut])
async def list_treatments(risk_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    risk = await _get_risk_or_404(risk_id, user.workspace_id, db)
    result = await db.execute(
        select(RiskTreatment).where(RiskTreatment.risk_id == risk.id).order_by(RiskTreatment.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/treatments/{treatment_id}", response_model=RiskTreatmentOut)
async def update_treatment(
    treatment_id: uuid.UUID,
    payload: RiskTreatmentUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RiskTreatment)
        .join(Risk, RiskTreatment.risk_id == Risk.id)
        .join(Project, Risk.project_id == Project.id)
        .where(RiskTreatment.id == treatment_id, Project.workspace_id == user.workspace_id)
    )
    treatment = result.scalar_one_or_none()
    if not treatment:
        raise NotFoundError("RiskTreatment", str(treatment_id))
    
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(treatment, field, value)
        
    await db.flush()
    await db.refresh(treatment)
    return treatment


@router.delete("/treatments/{treatment_id}", status_code=204)
async def delete_treatment(
    treatment_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RiskTreatment)
        .join(Risk, RiskTreatment.risk_id == Risk.id)
        .join(Project, Risk.project_id == Project.id)
        .where(RiskTreatment.id == treatment_id, Project.workspace_id == user.workspace_id)
    )
    treatment = result.scalar_one_or_none()
    if not treatment:
        raise NotFoundError("RiskTreatment", str(treatment_id))
        
    from sqlalchemy import delete
    await db.execute(delete(RiskTreatment).where(RiskTreatment.id == treatment_id))
    return None
