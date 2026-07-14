"""
BIA router (F2.B).

Business process CRUD + BIA calculation endpoints.

  POST   /projects/{project_id}/processes
  GET    /projects/{project_id}/processes
  GET    /processes/{process_id}
  PUT    /processes/{process_id}
  DELETE /processes/{process_id}

  POST   /processes/{process_id}/bia      ← calculate + persist
  GET    /processes/{process_id}/bia
  DELETE /processes/{process_id}/bia
"""
from __future__ import annotations

import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.models.project import Project
from app.modules.contexto.bia.calculator import BiaInput, calculate_bia
from app.modules.contexto.bia.excel_export import build_bia_excel
from app.modules.contexto.bia.models import AssetProcessLink, BiaEstimate, BusinessProcess
from app.modules.contexto.bia.schemas import (
    AssetProcessLinkIn,
    AssetProcessLinkOut,
    BiaCalculateIn,
    BiaEstimateOut,
    BusinessProcessIn,
    BusinessProcessOut,
    BusinessProcessWithBiaOut,
)
from app.models.asset import Asset

router = APIRouter(tags=["bia"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ─── Business processes ───────────────────────────────────────────────────────


@router.post("/projects/{project_id}/processes", response_model=BusinessProcessOut, status_code=201)
async def create_process(
    project_id: uuid.UUID,
    payload: BusinessProcessIn,
    db: DB,
    current_user: CurrentUser,
):
    process = BusinessProcess(
        project_id=project_id,
        name=payload.name,
        owner=payload.owner_name,
        criticality=payload.criticality,
        revenue_dependency=payload.revenue_dependency,
        manual_alternative="documented" if payload.has_manual_alternative else "none",
        contractual_commitment={"exists": True} if payload.contractual_commitments else None,
    )
    db.add(process)
    await db.flush()
    await db.refresh(process)
    return BusinessProcessOut.from_orm(process)


@router.get("/projects/{project_id}/processes", response_model=list[BusinessProcessWithBiaOut])
async def list_processes(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(BusinessProcess)
        .where(BusinessProcess.project_id == project_id)
        .order_by(BusinessProcess.created_at)
    )
    processes = result.scalars().all()

    out = []
    for proc in processes:
        bia = await _get_bia_for_process(db, proc.id)
        links = await _load_asset_links(db, proc.id)
        item = BusinessProcessWithBiaOut.from_orm(proc)
        item.bia = BiaEstimateOut.model_validate(bia) if bia else None
        item.asset_links = links
        out.append(item)
    return out


@router.get("/projects/{project_id}/processes/export", response_class=StreamingResponse)
async def export_processes_excel(
    project_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """TFM Tabla 11 (BIA-1) + Tabla 12 (BIA-2)."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    proc_result = await db.execute(
        select(BusinessProcess)
        .where(BusinessProcess.project_id == project_id)
        .order_by(BusinessProcess.created_at)
    )
    process_rows: list[dict] = []
    for proc in proc_result.scalars().all():
        bia   = await _get_bia_for_process(db, proc.id)
        links = await _load_asset_links(db, proc.id)
        process_rows.append({
            "name":                   proc.name,
            "owner":                  proc.owner,
            "criticality":            proc.criticality,
            "revenue_dependency":     proc.revenue_dependency,
            "manual_alternative":     proc.manual_alternative,
            "contractual_commitment": proc.contractual_commitment,
            "asset_names":            ", ".join(lnk.asset_name for lnk in links if lnk.asset_name),
            "bia": {
                "impact_2h":  bia.impact_2h,
                "impact_8h":  bia.impact_8h,
                "impact_24h": bia.impact_24h,
                "sn_active":  bia.sn_active,
                "mtpd_hours": bia.mtpd_hours,
                "rto_hours":  bia.rto_hours,
                "rpo_hours":  bia.rpo_hours,
                "breakdown":  bia.breakdown,
            } if bia else None,
        })

    buf = build_bia_excel(process_rows, project.name)
    safe_name = quote(f"BIA_{project.name}.xlsx", safe="")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )


@router.get("/processes/{process_id}", response_model=BusinessProcessWithBiaOut)
async def get_process(
    process_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    process = await db.get(BusinessProcess, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Proceso de negocio no encontrado")
    bia = await _get_bia_for_process(db, process_id)
    links = await _load_asset_links(db, process_id)
    item = BusinessProcessWithBiaOut.from_orm(process)
    item.bia = BiaEstimateOut.model_validate(bia) if bia else None
    item.asset_links = links
    return item


@router.put("/processes/{process_id}", response_model=BusinessProcessOut)
async def update_process(
    process_id: uuid.UUID,
    payload: BusinessProcessIn,
    db: DB,
    current_user: CurrentUser,
):
    process = await db.get(BusinessProcess, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Proceso de negocio no encontrado")
    process.name = payload.name
    process.owner = payload.owner_name
    process.criticality = payload.criticality
    process.revenue_dependency = payload.revenue_dependency
    process.manual_alternative = "documented" if payload.has_manual_alternative else "none"
    process.contractual_commitment = {"exists": True} if payload.contractual_commitments else None
    await db.flush()
    await db.refresh(process)
    return BusinessProcessOut.from_orm(process)


@router.delete("/processes/{process_id}", status_code=204)
async def delete_process(
    process_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    process = await db.get(BusinessProcess, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Proceso de negocio no encontrado")
    await db.delete(process)
    await db.flush()


# ─── BIA estimation ───────────────────────────────────────────────────────────


@router.post("/processes/{process_id}/bia", response_model=BiaEstimateOut, status_code=201)
async def calculate_and_save_bia(
    process_id: uuid.UUID,
    payload: BiaCalculateIn,
    db: DB,
    current_user: CurrentUser,
):
    """
    Run the BIA calculator with the provided inputs and persist the results.
    If a BiaEstimate already exists for this process, it is overwritten.
    """
    process = await db.get(BusinessProcess, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Proceso de negocio no encontrado")

    # Frontend sends pct as 0–100; calculator expects fraction 0.0–1.0
    rdp = payload.revenue_dependency_pct
    if rdp is not None and rdp > 1.0:
        rdp = rdp / 100.0

    inp = BiaInput(
        num_staff_affected=payload.num_staff_affected,
        avg_salary_hour=payload.avg_salary_hour,
        infra_cost_per_hour=payload.infra_cost_per_hour,
        contractual_penalty_per_hour=payload.contractual_penalty_per_hour,
        sla_at_risk_value=payload.sla_at_risk_value,
        hourly_revenue=payload.hourly_revenue,
        revenue_dependency_pct=rdp,
        revenue_dependency_band=process.revenue_dependency,
        sn_active=payload.sn_active,
        sanction_amount=payload.sanction_amount,
        annual_revenue=payload.annual_revenue,
        criticality=process.criticality,
        mtpd_hours=payload.mtpd_hours,
        rto_hours=payload.rto_hours,
        rpo_hours=payload.rpo_hours,
    )
    result = calculate_bia(inp)

    existing = await _get_bia_for_process(db, process_id)
    if existing:
        existing.impact_2h = result.impact_2h
        existing.impact_8h = result.impact_8h
        existing.impact_24h = result.impact_24h
        existing.sn_active = payload.sn_active
        existing.mtpd_hours = result.mtpd_hours
        existing.rto_hours = result.rto_hours
        existing.rpo_hours = result.rpo_hours
        existing.breakdown = result.breakdown
        bia = existing
    else:
        bia = BiaEstimate(
            process_id=process_id,
            impact_2h=result.impact_2h,
            impact_8h=result.impact_8h,
            impact_24h=result.impact_24h,
            sn_active=payload.sn_active,
            mtpd_hours=result.mtpd_hours,
            rto_hours=result.rto_hours,
            rpo_hours=result.rpo_hours,
            breakdown=result.breakdown,
        )
        db.add(bia)

    await db.flush()
    await db.refresh(bia)
    return BiaEstimateOut.model_validate(bia)


@router.get("/processes/{process_id}/bia", response_model=BiaEstimateOut)
async def get_bia(
    process_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    bia = await _get_bia_for_process(db, process_id)
    if not bia:
        raise HTTPException(status_code=404, detail="No hay estimación BIA para este proceso")
    return BiaEstimateOut.model_validate(bia)


@router.delete("/processes/{process_id}/bia", status_code=204)
async def delete_bia(
    process_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    bia = await _get_bia_for_process(db, process_id)
    if not bia:
        raise HTTPException(status_code=404, detail="No hay estimación BIA para este proceso")
    await db.delete(bia)
    await db.flush()


# ─── Asset-process links ──────────────────────────────────────────────────────


@router.get("/processes/{process_id}/asset-links", response_model=list[AssetProcessLinkOut])
async def list_asset_links(
    process_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    return await _load_asset_links(db, process_id)


@router.put(
    "/processes/{process_id}/asset-links/{asset_id}",
    response_model=AssetProcessLinkOut,
    status_code=200,
)
async def upsert_asset_link(
    process_id: uuid.UUID,
    asset_id: uuid.UUID,
    payload: AssetProcessLinkIn,
    db: DB,
    current_user: CurrentUser,
):
    process = await db.get(BusinessProcess, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Proceso de negocio no encontrado")

    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Activo no encontrado")

    result = await db.execute(
        select(AssetProcessLink).where(
            AssetProcessLink.process_id == process_id,
            AssetProcessLink.asset_id == asset_id,
        )
    )
    link = result.scalar_one_or_none()
    if link:
        link.weight = payload.weight
    else:
        link = AssetProcessLink(
            asset_id=asset_id,
            process_id=process_id,
            weight=payload.weight,
        )
        db.add(link)

    await db.flush()
    await db.refresh(link)

    out = AssetProcessLinkOut.from_orm(link)
    out.asset_name = asset.name
    out.asset_type = asset.asset_type
    out.asset_criticality = asset.criticality
    return out


@router.delete("/processes/{process_id}/asset-links/{asset_id}", status_code=204)
async def remove_asset_link(
    process_id: uuid.UUID,
    asset_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(AssetProcessLink).where(
            AssetProcessLink.process_id == process_id,
            AssetProcessLink.asset_id == asset_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Enlace no encontrado")
    await db.delete(link)
    await db.flush()


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _get_bia_for_process(db: AsyncSession, process_id: uuid.UUID) -> BiaEstimate | None:
    result = await db.execute(
        select(BiaEstimate).where(BiaEstimate.process_id == process_id).limit(1)
    )
    return result.scalar_one_or_none()


async def _load_asset_links(
    db: AsyncSession, process_id: uuid.UUID
) -> list[AssetProcessLinkOut]:
    result = await db.execute(
        select(AssetProcessLink, Asset)
        .join(Asset, AssetProcessLink.asset_id == Asset.id)
        .where(AssetProcessLink.process_id == process_id)
        .order_by(AssetProcessLink.weight.desc())
    )
    rows = result.all()
    links = []
    for link, asset in rows:
        out = AssetProcessLinkOut.from_orm(link)
        out.asset_name = asset.name
        out.asset_type = asset.asset_type
        out.asset_criticality = asset.criticality
        links.append(out)
    return links
