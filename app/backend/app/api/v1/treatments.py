import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.modules.tratamiento.plan.excel_export import build_treatments_excel

router = APIRouter(tags=["treatments"])

DB = Annotated[AsyncSession, Depends(get_db)]

@router.get("/treatments/projects/{project_id}/export", response_class=StreamingResponse)
async def export_treatments_excel(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: DB,
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.workspace_id == user.workspace_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))

    pid = str(project_id)
    q = text("""
        SELECT
            r.risk_code,
            r.risk_level,
            r.residual_level,
            t.treatment_type,
            t.title,
            t.description,
            t.owner_name,
            t.due_date,
            t.priority,
            t.expected_risk_reduction,
            t.effort
        FROM riesgos r
        JOIN tratamientos t ON t.risk_id = r.id
        WHERE r.project_id = :pid
        ORDER BY r.risk_code NULLS LAST, t.created_at ASC
    """)
    rows = [dict(row._mapping) for row in (await db.execute(q, {"pid": pid})).fetchall()]

    buf = build_treatments_excel(rows, project.name)
    safe_name = quote(f"Plan_Tratamiento_{project.name}.xlsx", safe="")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )
