import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.core.exceptions import NotFoundError
from app.models.asset import Asset
from app.models.code_source import CodeSource
from app.models.project import Project
from app.schemas.asset import AssetCreate, AssetOut, AssetUpdate
from app.schemas.common import PaginatedResponse

router = APIRouter(tags=["assets"])


async def _verify_project(project_id: uuid.UUID, workspace_id: uuid.UUID, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.workspace_id == workspace_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    return project


async def _get_asset_or_404(asset_id: uuid.UUID, workspace_id: uuid.UUID, db: AsyncSession) -> Asset:
    result = await db.execute(
        select(Asset)
        .join(Project, Asset.project_id == Project.id)
        .where(Asset.id == asset_id, Project.workspace_id == workspace_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise NotFoundError("Asset", str(asset_id))
    return asset


@router.get("/projects/{project_id}/assets", response_model=PaginatedResponse[AssetOut])
async def list_assets(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
):
    await _verify_project(project_id, user.workspace_id, db)
    q = select(Asset).where(Asset.project_id == project_id, Asset.is_active.is_(True))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    assets = (await db.execute(q.offset((page - 1) * size).limit(size).order_by(Asset.created_at.desc()))).scalars().all()
    return PaginatedResponse(items=list(assets), total=total, page=page, size=size, pages=max(1, -(-total // size)))


@router.post("/projects/{project_id}/assets", response_model=AssetOut, status_code=201)
async def create_asset(
    project_id: uuid.UUID,
    payload: AssetCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await _verify_project(project_id, user.workspace_id, db)
    asset = Asset(project_id=project_id, **payload.model_dump())
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


@router.get("/assets/{asset_id}", response_model=AssetOut)
async def get_asset(asset_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await _get_asset_or_404(asset_id, user.workspace_id, db)


@router.patch("/assets/{asset_id}", response_model=AssetOut)
async def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    asset = await _get_asset_or_404(asset_id, user.workspace_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    await db.flush()
    await db.refresh(asset)
    return asset


@router.delete("/assets/{asset_id}", status_code=204)
async def delete_asset(asset_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    asset = await _get_asset_or_404(asset_id, user.workspace_id, db)
    # code_sources FK uses SET NULL so we delete them explicitly to cascade scan_sessions → scans → findings
    cs_result = await db.execute(select(CodeSource).where(CodeSource.asset_id == asset_id))
    for cs in cs_result.scalars().all():
        await db.delete(cs)
    await db.delete(asset)
