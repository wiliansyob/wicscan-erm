import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.models.scan import Scan, ScanSession
from app.schemas.scan import ScanOut

router = APIRouter(prefix="/scans", tags=["scans"])


@router.get("/{scan_id}", response_model=ScanOut)
async def get_scan(scan_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Scan)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .join(Project, ScanSession.project_id == Project.id)
        .where(Scan.id == scan_id, Project.workspace_id == user.workspace_id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise NotFoundError("Scan", str(scan_id))
    return scan


@router.get("", response_model=list[ScanOut])
async def list_scans(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    session_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
):
    q = (
        select(Scan)
        .join(ScanSession, Scan.session_id == ScanSession.id)
        .join(Project, ScanSession.project_id == Project.id)
        .where(Project.workspace_id == user.workspace_id)
    )
    if session_id:
        q = q.where(Scan.session_id == session_id)
    if status:
        q = q.where(Scan.status == status)
    result = await db.execute(q.order_by(Scan.created_at.desc()).limit(100))
    return result.scalars().all()
