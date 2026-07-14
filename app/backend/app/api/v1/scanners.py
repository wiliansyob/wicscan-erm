import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.models.scanner import ScannerEngine
from app.schemas.scanner import ScannerEngineCreate, ScannerEngineUpdate, ScannerEngineOut

router = APIRouter(prefix="/scanners", tags=["scanners"])


@router.get("", response_model=list[ScannerEngineOut])
async def list_scanners(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Retrieve all registered scanner engines for the workspace.
    """
    result = await db.execute(
        select(ScannerEngine)
        .where(ScannerEngine.workspace_id == user.workspace_id)
        .order_by(ScannerEngine.name)
    )
    return result.scalars().all()


@router.post("", response_model=ScannerEngineOut)
async def create_scanner(
    payload: ScannerEngineCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Register a new scanner engine.
    """
    scanner = ScannerEngine(
        workspace_id=user.workspace_id,
        name=payload.name,
        engine_type=payload.engine_type,
        category=payload.category,
        url=str(payload.url),
        api_key=payload.api_key,
        is_active=payload.is_active
    )
    db.add(scanner)
    await db.commit()
    await db.refresh(scanner)
    return scanner


@router.put("/{scanner_id}", response_model=ScannerEngineOut)
async def update_scanner(
    scanner_id: uuid.UUID,
    payload: ScannerEngineUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update a registered scanner engine.
    """
    result = await db.execute(
        select(ScannerEngine)
        .where(ScannerEngine.id == scanner_id, ScannerEngine.workspace_id == user.workspace_id)
    )
    scanner = result.scalar_one_or_none()
    if not scanner:
        raise HTTPException(status_code=404, detail="Scanner not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "url" in update_data and update_data["url"] is not None:
        update_data["url"] = str(update_data["url"])

    for field, value in update_data.items():
        setattr(scanner, field, value)

    await db.commit()
    await db.refresh(scanner)
    return scanner


@router.delete("/{scanner_id}")
async def delete_scanner(
    scanner_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete a scanner engine.
    """
    result = await db.execute(
        select(ScannerEngine)
        .where(ScannerEngine.id == scanner_id, ScannerEngine.workspace_id == user.workspace_id)
    )
    scanner = result.scalar_one_or_none()
    if not scanner:
        raise HTTPException(status_code=404, detail="Scanner not found")

    await db.delete(scanner)
    await db.commit()
    return {"ok": True}
