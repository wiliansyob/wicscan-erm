import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.core.exceptions import NotFoundError, BadRequestError
from app.models.finding import Finding
from app.models.project import Project
from app.models.risk import Risk, RiskEngineRun, risk_finding_links
from app.models.scan import Scan, ScanSession
from app.models.code_source import CodeSource
from app.models.workspace import Workspace
from app.schemas.risk import RiskEngineRunCreate, RiskEngineRunOut

router = APIRouter(prefix="/risk-engine", tags=["risk-engine"])


@router.post("/runs", response_model=RiskEngineRunOut, status_code=202)
async def trigger_risk_engine(
    payload: RiskEngineRunCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    project_id: uuid.UUID = Query(...),
):
    project_result = await db.execute(
        select(Project, Workspace)
        .join(Workspace, Project.workspace_id == Workspace.id)
        .where(Project.id == project_id, Project.workspace_id == user.workspace_id)
    )
    row = project_result.first()
    if not row:
        raise NotFoundError("Project", str(project_id))
    project, workspace = row

    session_result = await db.execute(
        select(ScanSession)
        .join(Project, ScanSession.project_id == Project.id)
        .where(ScanSession.id == payload.scan_session_id, Project.workspace_id == user.workspace_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise NotFoundError("ScanSession", str(payload.scan_session_id))
    if session.status != "completed":
        raise BadRequestError(f"Scan session is not completed (status: {session.status})")

    q = select(Finding).join(Scan, Finding.scan_id == Scan.id).join(ScanSession, Scan.session_id == ScanSession.id).where(
        ScanSession.project_id == project_id, Finding.status == "open"
    )
    if payload.finding_ids:
        q = q.where(Finding.id.in_(payload.finding_ids))
    
    findings_count = (await db.execute(q)).scalars()
    open_findings = list(findings_count)

    ai_config = workspace.ai_config or {}
    providers_conf = ai_config.get("providers", {})
    configured_model = None
    if payload.ai_provider in providers_conf:
        configured_model = providers_conf[payload.ai_provider].get("model")

    model_used = payload.model_used or configured_model or _default_model(payload.ai_provider)

    run = RiskEngineRun(
        project_id=project_id,
        scan_session_id=payload.scan_session_id,
        ai_provider=payload.ai_provider,
        model_used=model_used,
        status="pending",
        findings_input_count=len(open_findings),
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    from app.worker.tasks.risk_tasks import run_risk_engine_task
    from fastapi import BackgroundTasks
    # Enqueue async task
    fid_strings = [str(fid) for fid in payload.finding_ids] if payload.finding_ids else None
    run_risk_engine_task.delay(str(run.id), fid_strings, payload.prompt_template)

    return run


@router.get("/runs", response_model=list[RiskEngineRunOut])
async def list_runs(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    project_id: uuid.UUID = Query(...),
    asset_id: uuid.UUID | None = Query(None),
):
    project_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.workspace_id == user.workspace_id)
    )
    if not project_result.scalar_one_or_none():
        raise NotFoundError("Project", str(project_id))

    q = select(RiskEngineRun).where(RiskEngineRun.project_id == project_id)
    if asset_id:
        q = q.join(ScanSession, RiskEngineRun.scan_session_id == ScanSession.id).join(CodeSource, ScanSession.code_source_id == CodeSource.id).where(CodeSource.asset_id == asset_id)
        
    result = await db.execute(q.order_by(RiskEngineRun.created_at.desc()).limit(20))
    return result.scalars().all()


@router.get("/runs/{run_id}", response_model=RiskEngineRunOut)
async def get_run(run_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RiskEngineRun)
        .join(Project, RiskEngineRun.project_id == Project.id)
        .where(RiskEngineRun.id == run_id, Project.workspace_id == user.workspace_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise NotFoundError("RiskEngineRun", str(run_id))
    return run


@router.delete("/runs/{run_id}", status_code=204)
async def delete_run(run_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RiskEngineRun)
        .join(Project, RiskEngineRun.project_id == Project.id)
        .where(RiskEngineRun.id == run_id, Project.workspace_id == user.workspace_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise NotFoundError("RiskEngineRun", str(run_id))
    
    await db.execute(delete(Risk).where(Risk.risk_engine_run_id == run_id))
    await db.delete(run)
    await db.commit()
    return None


def _default_model(provider: str) -> str:
    defaults = {
        "anthropic": "claude-sonnet-4-6",
        "openai": "gpt-4o",
        "gemini": "gemini-flash-latest",
        "ollama": "llama3.2",
    }
    return defaults.get(provider, "unknown")
