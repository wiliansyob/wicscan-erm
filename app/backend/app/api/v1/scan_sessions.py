import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.core.exceptions import NotFoundError, BadRequestError
from app.models.code_source import CodeSource
from app.models.project import Project
from app.models.asset import Asset
from app.models.scan import Scan, ScanSession
from app.schemas.common import PaginatedResponse
from app.schemas.scan import ScanOut, ScanSessionCreate, ScanSessionOut
from app.worker.tasks.scan_tasks import trigger_scan_task
from fastapi import Query

router = APIRouter(tags=["scan-sessions"])


async def _verify_project(project_id: uuid.UUID, workspace_id: uuid.UUID, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.workspace_id == workspace_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    return project


async def _get_session_or_404(session_id: uuid.UUID, workspace_id: uuid.UUID, db: AsyncSession) -> ScanSession:
    result = await db.execute(
        select(ScanSession)
        .join(Project, ScanSession.project_id == Project.id)
        .where(ScanSession.id == session_id, Project.workspace_id == workspace_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("ScanSession", str(session_id))
    return session


@router.get("/projects/{project_id}/scan-sessions", response_model=PaginatedResponse[ScanSessionOut])
async def list_scan_sessions(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=5000),
    asset_id: uuid.UUID | None = Query(None),
):
    await _verify_project(project_id, user.workspace_id, db)
    from sqlalchemy import func
    q = select(ScanSession).where(ScanSession.project_id == project_id)
    if asset_id:
        q = q.join(CodeSource, ScanSession.code_source_id == CodeSource.id).where(CodeSource.asset_id == asset_id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    sessions = (await db.execute(
        q.order_by(ScanSession.created_at.desc()).offset((page - 1) * size).limit(size)
    )).scalars().all()
    return PaginatedResponse(items=list(sessions), total=total, page=page, size=size, pages=max(1, -(-total // size)))


@router.post("/projects/{project_id}/scan-sessions", response_model=ScanSessionOut, status_code=202)
async def create_scan_session(
    project_id: uuid.UUID,
    payload: ScanSessionCreate,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    await _verify_project(project_id, user.workspace_id, db)

    if payload.code_source_id:
        cs_result = await db.execute(
            select(CodeSource)
            .join(Project, CodeSource.project_id == Project.id)
            .where(CodeSource.id == payload.code_source_id, Project.workspace_id == user.workspace_id)
        )
        code_source = cs_result.scalar_one_or_none()
        if not code_source:
            raise NotFoundError("CodeSource", str(payload.code_source_id))
        if code_source.status != "ready":
            raise BadRequestError(f"Code source is not ready (status: {code_source.status})")
    elif payload.asset_id:
        asset_result = await db.execute(
            select(Asset)
            .join(Project, Asset.project_id == Project.id)
            .where(Asset.id == payload.asset_id, Project.workspace_id == user.workspace_id)
        )
        asset = asset_result.scalar_one_or_none()
        if not asset:
            raise NotFoundError("Asset", str(payload.asset_id))
        
        # Create a dummy CodeSource for the asset to satisfy DB constraints for DAST scans
        code_source = CodeSource(
            project_id=project_id,
            asset_id=payload.asset_id,
            source_type="url",
            label=f"Auto-generated URL source for {asset.name}",
            status="ready",
            ready_at=datetime.now(timezone.utc)
        )
        db.add(code_source)
        await db.flush()
        payload.code_source_id = code_source.id
    else:
        raise BadRequestError("Must provide code_source_id or asset_id")

    session = ScanSession(
        project_id=project_id,
        code_source_id=payload.code_source_id,
        triggered_by=user.id,
        status="pending",
        is_retest=payload.is_retest,
        baseline_session_id=payload.baseline_session_id,
        scanners_requested=payload.scanners,
    )
    db.add(session)
    await db.flush()

    for scanner_type in payload.scanners:
        scanner_config = payload.scanner_configs.get(scanner_type) if payload.scanner_configs else None
        scan = Scan(session_id=session.id, scanner_type=scanner_type, status="pending", config=scanner_config)
        db.add(scan)
        await db.flush()
        background_tasks.add_task(trigger_scan_task.delay, str(scan.id))

    await db.refresh(session)
    return session


@router.get("/scan-sessions/{session_id}", response_model=ScanSessionOut)
async def get_scan_session(session_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await _get_session_or_404(session_id, user.workspace_id, db)


@router.get("/scan-sessions/{session_id}/scans", response_model=list[ScanOut])
async def list_session_scans(session_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    await _get_session_or_404(session_id, user.workspace_id, db)
    result = await db.execute(select(Scan).where(Scan.session_id == session_id))
    return result.scalars().all()


@router.patch("/scan-sessions/{session_id}/cancel", response_model=ScanSessionOut)
async def cancel_scan_session(session_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    session = await _get_session_or_404(session_id, user.workspace_id, db)
    if session.status not in ("pending", "running"):
        raise BadRequestError(f"Cannot cancel session with status '{session.status}'")
    session.status = "cancelled"
    session.completed_at = datetime.now(timezone.utc)
    return session


@router.delete("/scan-sessions/{session_id}", status_code=204)
async def delete_scan_session(session_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    session = await _get_session_or_404(session_id, user.workspace_id, db)
    await db.delete(session)
