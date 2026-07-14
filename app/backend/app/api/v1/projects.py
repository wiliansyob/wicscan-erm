import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.core.exceptions import NotFoundError
from app.models.asset import Asset
from app.models.project import Project
from app.models.risk import Risk
from app.schemas.common import PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


async def _get_project_or_404(project_id: uuid.UUID, workspace_id: uuid.UUID, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.workspace_id == workspace_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    return project


async def _enrich_project(project: Project, db: AsyncSession) -> dict:
    asset_count = (await db.execute(
        select(func.count(Asset.id)).where(Asset.project_id == project.id, Asset.is_active.is_(True))
    )).scalar() or 0

    risk_counts = await db.execute(
        select(Risk.risk_level, func.count(Risk.id))
        .where(Risk.project_id == project.id, Risk.status.notin_(["mitigated", "accepted"]))
        .group_by(Risk.risk_level)
    )
    risk_by_level = {row[0]: row[1] for row in risk_counts}

    return {
        **project.__dict__,
        "asset_count": asset_count,
        "open_risk_count": sum(risk_by_level.values()),
        "critical_risk_count": risk_by_level.get("critical", 0),
    }


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    payload: ProjectCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    project = Project(workspace_id=user.workspace_id, **payload.model_dump())
    db.add(project)
    await db.flush()
    return await _enrich_project(project, db)


@router.get("", response_model=PaginatedResponse[ProjectOut])
async def list_projects(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
):
    q = select(Project).where(Project.workspace_id == user.workspace_id)
    if status:
        q = q.where(Project.status == status)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    q = q.offset((page - 1) * size).limit(size).order_by(Project.created_at.desc())
    projects = (await db.execute(q)).scalars().all()

    items = [await _enrich_project(p, db) for p in projects]
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=max(1, -(-total // size)))


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    project = await _get_project_or_404(project_id, user.workspace_id, db)
    return await _enrich_project(project, db)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, user.workspace_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    return await _enrich_project(project, db)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    project = await _get_project_or_404(project_id, user.workspace_id, db)
    await db.delete(project)
