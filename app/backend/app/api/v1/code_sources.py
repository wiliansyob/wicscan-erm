import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.core.exceptions import NotFoundError
from app.models.code_source import CodeSource
from app.models.project import Project
from app.schemas.code_source import CodeSourceCreate, CodeSourceOut

router = APIRouter(tags=["code-sources"])

UPLOADS_DIR = Path("/app/uploads")


async def _verify_project(project_id: uuid.UUID, workspace_id: uuid.UUID, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.workspace_id == workspace_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    return project


async def _get_code_source_or_404(cs_id: uuid.UUID, workspace_id: uuid.UUID, db: AsyncSession) -> CodeSource:
    result = await db.execute(
        select(CodeSource)
        .join(Project, CodeSource.project_id == Project.id)
        .where(CodeSource.id == cs_id, Project.workspace_id == workspace_id)
    )
    cs = result.scalar_one_or_none()
    if not cs:
        raise NotFoundError("CodeSource", str(cs_id))
    return cs


@router.get("/projects/{project_id}/code-sources", response_model=list[CodeSourceOut])
async def list_code_sources(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    asset_id: uuid.UUID | None = None,
):
    await _verify_project(project_id, user.workspace_id, db)
    q = select(CodeSource).where(CodeSource.project_id == project_id)
    if asset_id:
        q = q.where(CodeSource.asset_id == asset_id)
    result = await db.execute(q.order_by(CodeSource.created_at.desc()))
    return result.scalars().all()


@router.post("/projects/{project_id}/code-sources", response_model=CodeSourceOut, status_code=201)
async def create_code_source(
    project_id: uuid.UUID,
    payload: CodeSourceCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await _verify_project(project_id, user.workspace_id, db)
    
    # Initialize the code source model from the payload
    cs_data = payload.model_dump()
    
    # GitHub URLs don't need preprocessing. They are cloned dynamically during the scan.
    if cs_data.get("source_type") == "github":
        cs_data["status"] = "ready"
        cs_data["ready_at"] = datetime.now(timezone.utc)
        
    cs = CodeSource(project_id=project_id, **cs_data)
    db.add(cs)
    await db.flush()
    await db.refresh(cs)
    return cs


@router.post("/projects/{project_id}/code-sources/upload", response_model=CodeSourceOut, status_code=201)
async def upload_zip_source(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    label: str | None = Form(None),
    asset_id: uuid.UUID | None = Form(None),
):
    """Accept a ZIP file and register it as a ready code source."""
    await _verify_project(project_id, user.workspace_id, db)

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=422, detail="Only .zip files are accepted")

    upload_dir = UPLOADS_DIR / str(project_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4()}.zip"
    dest = upload_dir / stored_name
    content = await file.read()
    dest.write_bytes(content)

    cs = CodeSource(
        project_id=project_id,
        asset_id=asset_id,
        source_type="zip",
        label=label or file.filename,
        zip_filename=file.filename,
        local_snapshot_path=str(dest),
        status="ready",
        ready_at=datetime.now(timezone.utc),
    )
    db.add(cs)
    await db.flush()
    await db.refresh(cs)
    return cs


@router.get("/code-sources/{cs_id}", response_model=CodeSourceOut)
async def get_code_source(cs_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await _get_code_source_or_404(cs_id, user.workspace_id, db)


@router.delete("/code-sources/{cs_id}", status_code=204)
async def delete_code_source(cs_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    cs = await _get_code_source_or_404(cs_id, user.workspace_id, db)
    await db.delete(cs)
