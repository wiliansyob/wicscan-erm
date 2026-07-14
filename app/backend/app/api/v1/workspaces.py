from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.database import get_db
from app.models.workspace import Workspace

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


from typing import Any

class WorkspaceSettingsUpdate(BaseModel):
    ai_config: dict[str, Any]


@router.get("/settings")
async def get_workspace_settings(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workspace).where(Workspace.id == user.workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    return {"ai_config": workspace.ai_config or {}}


@router.patch("/settings")
async def update_workspace_settings(payload: WorkspaceSettingsUpdate, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workspace).where(Workspace.id == user.workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    workspace.ai_config = payload.ai_config
    flag_modified(workspace, "ai_config")
    await db.commit()
    
    return {"ai_config": workspace.ai_config}
