import uuid
import csv
import io
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, text, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.core.exceptions import NotFoundError
from app.models.finding import Finding
from app.models.project import Project
from app.models.scan import Scan, ScanSession
from app.schemas.common import PaginatedResponse
from app.schemas.finding import FindingOut, FindingStatusUpdate, FindingManualCreate, FindingUpdate
from app.models.asset import Asset
from app.models.code_source import CodeSource
from app.modules.contexto.bia.excel_export import build_vuln_excel

router = APIRouter(prefix="/findings", tags=["findings"])
vuln_export_router = APIRouter(tags=["findings"])


@router.get("", response_model=PaginatedResponse[FindingOut])
async def list_findings(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    project_id: uuid.UUID | None = Query(None),
    asset_id: uuid.UUID | None = Query(None),
    severity: list[str] | None = Query(None),
    status: str | None = Query(None),
    scanner: str | None = Query(None),
    scan_session_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=5000),
):
    q = (
        select(Finding)
        .join(Scan, Finding.scan_id == Scan.id)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .join(Project, ScanSession.project_id == Project.id)
        .where(Project.workspace_id == user.workspace_id)
    )
    if project_id:
        q = q.where(ScanSession.project_id == project_id)
    if asset_id:
        q = q.where(Finding.asset_id == asset_id)
    if severity:
        q = q.where(Finding.severity.in_(severity))
    if status:
        q = q.where(Finding.status == status)
    if scanner:
        q = q.where(Finding.scanner == scanner)
    if scan_session_id:
        q = q.where(Scan.session_id == scan_session_id)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    findings = (await db.execute(
        q.order_by(Finding.first_detected_at.desc()).offset((page - 1) * size).limit(size)
    )).scalars().all()
    return PaginatedResponse(items=list(findings), total=total, page=page, size=size, pages=max(1, -(-total // size)))


@router.get("/stats/summary")
async def findings_summary(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    project_id: uuid.UUID | None = Query(None),
    asset_id: uuid.UUID | None = Query(None),
):
    q = (
        select(Finding.severity, func.count(Finding.id).label("count"))
        .join(Scan, Finding.scan_id == Scan.id)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .join(Project, ScanSession.project_id == Project.id)
        .where(Project.workspace_id == user.workspace_id, Finding.status == "open")
        .group_by(Finding.severity)
    )
    if project_id:
        q = q.where(ScanSession.project_id == project_id)
    if asset_id:
        q = q.where(Finding.asset_id == asset_id)
    rows = (await db.execute(q)).all()
    summary = {row.severity: row.count for row in rows}
    return {
        "critical": summary.get("critical", 0),
        "high": summary.get("high", 0),
        "medium": summary.get("medium", 0),
        "low": summary.get("low", 0),
        "info": summary.get("info", 0),
    }


@router.get("/stats/sources")
async def findings_sources(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    project_id: uuid.UUID | None = Query(None),
    asset_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
):
    q = (
        select(Finding.scanner)
        .join(Scan, Finding.scan_id == Scan.id)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .join(Project, ScanSession.project_id == Project.id)
        .where(Project.workspace_id == user.workspace_id, Finding.scanner.is_not(None))
        .distinct()
    )
    if project_id:
        q = q.where(ScanSession.project_id == project_id)
    if asset_id:
        q = q.where(Finding.asset_id == asset_id)
    if status:
        q = q.where(Finding.status == status)
    
    rows = (await db.execute(q)).scalars().all()
    # Filter out empty strings if any
    return [r for r in rows if r]


@router.get("/{finding_id}", response_model=FindingOut)
async def get_finding(finding_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Finding)
        .join(Scan, Finding.scan_id == Scan.id)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .join(Project, ScanSession.project_id == Project.id)
        .where(Finding.id == finding_id, Project.workspace_id == user.workspace_id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise NotFoundError("Finding", str(finding_id))
    return finding


@router.patch("/{finding_id}/status", response_model=FindingOut)
async def update_finding_status(
    finding_id: uuid.UUID,
    payload: FindingStatusUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Finding)
        .join(Scan, Finding.scan_id == Scan.id)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .join(Project, ScanSession.project_id == Project.id)
        .where(Finding.id == finding_id, Project.workspace_id == user.workspace_id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise NotFoundError("Finding", str(finding_id))
    finding.status = payload.status
    finding.status_changed_by = user.id
    finding.status_reason = payload.reason
    return finding


@router.patch("/{finding_id}", response_model=FindingOut)
async def update_finding(
    finding_id: uuid.UUID,
    payload: FindingUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Finding)
        .join(Scan, Finding.scan_id == Scan.id)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .join(Project, ScanSession.project_id == Project.id)
        .where(Finding.id == finding_id, Project.workspace_id == user.workspace_id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise NotFoundError("Finding", str(finding_id))
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(finding, key, value)
        
    await db.commit()
    await db.refresh(finding)
    return finding


@router.delete("/{finding_id}", status_code=204)
async def delete_finding(
    finding_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Finding, Scan, ScanSession)
        .join(Scan, Finding.scan_id == Scan.id)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .join(Project, ScanSession.project_id == Project.id)
        .where(Finding.id == finding_id, Project.workspace_id == user.workspace_id)
    )
    row = result.first()
    if not row:
        raise NotFoundError("Finding", str(finding_id))
        
    finding, scan, session = row
    
    await db.delete(finding)
    
    # Update counters
    if scan.findings_count > 0:
        scan.findings_count -= 1
    if session.total_findings_count > 0:
        session.total_findings_count -= 1
        
    await db.commit()
    return None

import httpx
from app.config import get_settings
settings = get_settings()

@router.get("/{finding_id}/snippet")
async def get_finding_snippet(finding_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Finding)
        .join(Scan, Finding.scan_id == Scan.id)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .join(Project, ScanSession.project_id == Project.id)
        .where(Finding.id == finding_id, Project.workspace_id == user.workspace_id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise NotFoundError("Finding", str(finding_id))
        
    if not finding.component or not finding.line_start:
        return {"snippet": []}
        
    # Extraer el project_key que suele ser la primera parte del component "projectKey:path"
    if ":" not in finding.component:
        return {"snippet": []}
        
    project_key, file_path = finding.component.split(":", 1)
    
    # 15 lineas de contexto antes y despues
    start = max(1, finding.line_start - 15)
    end = finding.line_start + 15
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.SCANNER_MANAGER_URL}/api/v1/scanners/sonarqube/snippet",
                params={
                    "project_key": project_key,
                    "file_path": file_path,
                    "line_start": start,
                    "line_end": end
                }
            )
            if resp.status_code == 200:
                return resp.json()
            return {"snippet": []}
    except Exception:
        return {"snippet": []}

@router.post("/manual", response_model=FindingOut)
async def create_manual_finding(
    payload: FindingManualCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    # 1. Verify asset belongs to a project in the user's workspace
    asset = (await db.execute(
        select(Asset)
        .join(Project, Asset.project_id == Project.id)
        .where(Asset.id == payload.asset_id, Project.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    
    if not asset:
        raise NotFoundError("Asset", str(payload.asset_id))
        
    # 2. Get or create a "manual" CodeSource
    code_source = (await db.execute(
        select(CodeSource)
        .where(CodeSource.project_id == asset.project_id, CodeSource.source_type == "manual")
    )).scalars().first()
    
    if not code_source:
        code_source = CodeSource(
            project_id=asset.project_id,
            source_type="manual",
            label="Manual Entry",
            status="ready"
        )
        db.add(code_source)
        await db.flush()

    # 3. Get or create a "manual" ScanSession
    session = (await db.execute(
        select(ScanSession)
        .where(ScanSession.project_id == asset.project_id, ScanSession.code_source_id == code_source.id)
    )).scalars().first()
    
    if not session:
        session = ScanSession(
            project_id=asset.project_id,
            code_source_id=code_source.id,
            status="completed",
            scanners_requested=["manual"],
            total_findings_count=0
        )
        db.add(session)
        await db.flush()
        
    # 4. Get or create a "manual" Scan
    scan = (await db.execute(
        select(Scan)
        .where(Scan.session_id == session.id, Scan.scanner_type == "manual")
    )).scalars().first()
    
    if not scan:
        scan = Scan(
            session_id=session.id,
            scanner_type="manual",
            status="completed",
            findings_count=0
        )
        db.add(scan)
        await db.flush()
        
    # 5. Insert Finding
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    
    max_seq_result = await db.execute(
        select(func.max(func.cast(func.substring(Finding.finding_code, 3), Integer)))
        .where(Finding.finding_code.like("F-%"))
    )
    max_seq = max_seq_result.scalar() or 0
    next_seq = max_seq + 1

    finding = Finding(
        scan_id=scan.id,
        asset_id=asset.id,
        finding_code=f"F-{next_seq:04d}",
        scanner=payload.source or "manual",
        finding_type=payload.finding_type,
        category=payload.category,
        cwe=payload.cwe,
        owasp_category=payload.owasp_category,
        cvss_score=payload.cvss_score,
        severity=payload.severity,
        title=payload.title,
        description=payload.description,
        remediation_guidance=payload.remediation_guidance,
        file_path=payload.file_path,
        line_start=payload.line_start,
        confidence=1.0,
        status="open",
        first_detected_at=now,
        last_seen_at=now
    )
    
    db.add(finding)
    
    # Update counters
    session.total_findings_count += 1
    session.new_findings_count += 1
    scan.findings_count += 1
    
    await db.commit()
    await db.refresh(finding)
    
    return finding


@router.post("/upload-csv")
async def upload_csv_findings(
    user: CurrentUser,
    asset_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only .csv files are accepted")

    # 1. Verify asset belongs to a project in the user's workspace
    asset = (await db.execute(
        select(Asset)
        .join(Project, Asset.project_id == Project.id)
        .where(Asset.id == asset_id, Project.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    
    if not asset:
        raise NotFoundError("Asset", str(asset_id))
        
    # Read and parse CSV
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Must be UTF-8.")
        
    stream = io.StringIO(text)
    reader = csv.DictReader(stream)
    
    required_cols = {"title", "severity"}
    if not reader.fieldnames or not required_cols.issubset(set(k.lower() for k in reader.fieldnames if k)):
        raise HTTPException(status_code=400, detail=f"CSV must contain at least headers: {', '.join(required_cols)}")
    
    # Lowercase headers for easy access
    reader.fieldnames = [k.lower().strip() if k else "" for k in reader.fieldnames]

    # 2. Get or create a "manual" CodeSource
    code_source = (await db.execute(
        select(CodeSource)
        .where(CodeSource.project_id == asset.project_id, CodeSource.source_type == "manual")
    )).scalars().first()
    
    if not code_source:
        code_source = CodeSource(
            project_id=asset.project_id,
            source_type="manual",
            label="Manual Entry",
            status="ready"
        )
        db.add(code_source)
        await db.flush()

    # 3. Get or create a "manual" ScanSession
    session = (await db.execute(
        select(ScanSession)
        .where(ScanSession.project_id == asset.project_id, ScanSession.code_source_id == code_source.id)
    )).scalars().first()
    
    if not session:
        session = ScanSession(
            project_id=asset.project_id,
            code_source_id=code_source.id,
            status="completed",
            scanners_requested=["manual"],
            total_findings_count=0
        )
        db.add(session)
        await db.flush()
        
    # 4. Get or create a "manual" Scan
    scan = (await db.execute(
        select(Scan)
        .where(Scan.session_id == session.id, Scan.scanner_type == "manual")
    )).scalars().first()
    
    if not scan:
        scan = Scan(
            session_id=session.id,
            scanner_type="manual",
            status="completed",
            findings_count=0
        )
        db.add(scan)
        await db.flush()

    # 5. Insert Findings
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    
    findings_to_insert = []
    for row in reader:
        title = row.get("title", "").strip()
        severity = row.get("severity", "medium").strip().lower()
        if not title:
            continue
            
        finding = Finding(
            scan_id=scan.id,
            asset_id=asset.id,
            scanner=(row.get("source") or row.get("fuente") or "").strip() or "manual",
            finding_type=row.get("finding_type", "vulnerability").strip() or "vulnerability",
            category=row.get("category", "manual_review").strip() or "manual_review",
            cwe=row.get("cwe", "").strip() or None,
            owasp_category=row.get("owasp_category", "").strip() or None,
            cvss_score=float(row["cvss_score"]) if row.get("cvss_score", "").strip() else None,
            severity=severity if severity in ["critical", "high", "medium", "low", "info"] else "medium",
            title=title,
            description=row.get("description", "").strip() or None,
            remediation_guidance=row.get("remediation_guidance", "").strip() or None,
            confidence=1.0,
            status="open",
            first_detected_at=now,
            last_seen_at=now,
            created_at=now
        )
        findings_to_insert.append(finding)
        
    if findings_to_insert:
        db.add_all(findings_to_insert)
        
        # 6. Actualizar contadores
        scan.findings_count += len(findings_to_insert)
        session.total_findings_count += len(findings_to_insert)
        db.add(scan)
        db.add(session)
        
        await db.commit()

    return {"detail": f"Successfully uploaded {len(findings_to_insert)} findings."}


# ─── Vulnerability Excel export (Tablas 15 + 16) ─────────────────────────────

@vuln_export_router.get("/projects/{project_id}/vulnerabilities/export", response_class=StreamingResponse)
async def export_vuln_excel(
    project_id: uuid.UUID,
    _user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """TFM Tabla 15 (activos × hallazgos) + Tabla 16 (escenarios contextuales)."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    pid = str(project_id)

    findings_q = text("""
        SELECT
            f.finding_code,
            f.title,
            f.finding_type,
            f.category,
            f.cwe,
            f.owasp_category,
            f.cvss_score,
            f.severity,
            f.scanner,
            f.confidence,
            f.file_path,
            f.line_start,
            f.status,
            f.first_detected_at,
            a.name            AS asset_name,
            a.asset_type,
            a.criticality     AS asset_criticality,
            a.technical_owner AS asset_owner
        FROM findings f
        LEFT JOIN assets a      ON a.id = f.asset_id
        JOIN scans sc           ON sc.id = f.scan_id
        JOIN scan_sessions ss   ON ss.id = sc.session_id
        WHERE ss.project_id = :pid
          AND f.status NOT IN ('false_positive', 'wont_fix')
        ORDER BY
            CASE f.severity
                WHEN 'critical' THEN 1 WHEN 'high'   THEN 2
                WHEN 'medium'   THEN 3 WHEN 'low'    THEN 4
                ELSE 5
            END,
            a.name NULLS LAST,
            f.title
    """)
    finding_rows = [dict(r._mapping) for r in (await db.execute(findings_q, {"pid": pid})).fetchall()]

    scenarios_q = text("""
        SELECT
            e.scenario_code,
            e.title             AS scenario_title,
            e.group_key,
            e.probability,
            e.prob_level,
            e.impact,
            e.impact_level,
            e.impact_operational,
            e.impact_financial,
            e.impact_normative,
            e.impact_reputational,
            COUNT(DISTINCT eh.finding_id)               AS finding_count,
            STRING_AGG(DISTINCT a.name, ', ')           AS asset_name,
            STRING_AGG(DISTINCT a.asset_type, ', ')     AS asset_type,
            STRING_AGG(DISTINCT a.criticality, ', ')    AS asset_criticality,
            r.risk_code,
            r.risk_title,
            r.risk_score,
            r.risk_level,
            r.status                                    AS risk_status,
            bp.name                                     AS process_name,
            b.impact_24h,
            b.sn_active,
            STRING_AGG(DISTINCT t.treatment_type, ', ') AS treatment_types,
            COUNT(DISTINCT t.id)                        AS treatment_count,
            STRING_AGG(DISTINCT f.finding_code, ', ')   AS finding_codes
        FROM escenarios e
        LEFT JOIN escenario_hallazgos eh ON eh.scenario_id = e.id
        LEFT JOIN findings f             ON f.id = eh.finding_id
        LEFT JOIN assets a               ON a.id = COALESCE(e.asset_id, f.asset_id)
        LEFT JOIN riesgos r              ON r.scenario_id = e.id
        LEFT JOIN procesos_negocio bp    ON bp.id = COALESCE(e.business_process_id, r.business_process_id)
        LEFT JOIN estimaciones_bia b     ON b.process_id = bp.id
        LEFT JOIN tratamientos t         ON t.risk_id = r.id
        WHERE e.project_id = :pid
        GROUP BY
            e.id, e.scenario_code, e.title, e.group_key,
            e.probability, e.prob_level, e.impact, e.impact_level,
            e.impact_operational, e.impact_financial, e.impact_normative, e.impact_reputational,
            r.risk_code, r.risk_title, r.risk_score, r.risk_level, r.status,
            bp.name, b.impact_24h, b.sn_active
        ORDER BY
            CASE COALESCE(r.risk_level, e.impact_level)
                WHEN 'critical' THEN 1 WHEN 'high'   THEN 2
                WHEN 'medium'   THEN 3 WHEN 'low'    THEN 4
                ELSE 5
            END,
            e.scenario_code NULLS LAST
    """)
    scenario_rows = [dict(r._mapping) for r in (await db.execute(scenarios_q, {"pid": pid})).fetchall()]

    assets_q = text("""
        SELECT 
            a.id, a.name, a.asset_type, a.criticality, a.description, a.technical_owner, a.business_owner, a.url, a.ip_address,
            STRING_AGG(bp.name, ', ') as process_names
        FROM assets a
        LEFT JOIN activo_proceso_links apl ON a.id = apl.asset_id
        LEFT JOIN procesos_negocio bp ON apl.process_id = bp.id
        WHERE a.project_id = :pid
        GROUP BY a.id
        ORDER BY a.name
    """)
    asset_rows = [dict(r._mapping) for r in (await db.execute(assets_q, {"pid": pid})).fetchall()]

    buf = build_vuln_excel(asset_rows, finding_rows, scenario_rows, project.name)
    safe_name = quote(f"Vulnerabilidades_{project.name}.xlsx", safe="")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )
