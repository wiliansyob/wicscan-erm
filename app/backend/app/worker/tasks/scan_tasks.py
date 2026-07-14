"""
Celery tasks for scan lifecycle management.

Flow:
  trigger_scan_task(scan_id)
    → load Scan → ScanSession → CodeSource → Project
    → call Scanner Manager with code snapshot path
    → poll for completion
    → fetch normalized findings
    → save findings (fingerprint dedup per project)
    → update Scan + ScanSession status
"""

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from celery import Task
from sqlalchemy import func, select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.asset import Asset
from app.models.code_source import CodeSource
from app.models.finding import Finding
from app.models.project import Project
from app.models.scan import Scan, ScanSession
from app.modules.identification.scanners.base import ScanRequest
from app.modules.identification.scanners.registry import get_adapter
from app.worker.celery_app import celery_app

log = structlog.get_logger(__name__)
settings = get_settings()


class ScanTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        scan_id = args[0] if args else None
        if scan_id:
            asyncio.get_event_loop().run_until_complete(
                _mark_scan_failed(uuid.UUID(scan_id), str(exc))
            )


async def _mark_scan_failed(scan_id: uuid.UUID, error: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        if scan:
            scan.status = "failed"
            scan.error_message = error[:1000]
            scan.completed_at = datetime.now(timezone.utc)
            await db.flush()
            await _maybe_complete_session(db, scan.session_id, 0, 0)
            await db.commit()


@celery_app.task(bind=True, base=ScanTask, name="app.worker.tasks.scan_tasks.trigger_scan_task", max_retries=3)
def trigger_scan_task(self, scan_id: str) -> dict:
    return asyncio.get_event_loop().run_until_complete(_run_scan(uuid.UUID(scan_id)))


async def _run_scan(scan_id: uuid.UUID) -> dict:
    log.info("scan_started", scan_id=str(scan_id))

    async with AsyncSessionLocal() as db:
        scan_result = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = scan_result.scalar_one_or_none()
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        session_result = await db.execute(select(ScanSession).where(ScanSession.id == scan.session_id))
        session = session_result.scalar_one()

        cs_result = await db.execute(select(CodeSource).where(CodeSource.id == session.code_source_id))
        code_source = cs_result.scalar_one()

        project_result = await db.execute(select(Project).where(Project.id == session.project_id))
        project = project_result.scalar_one()

        asset = None
        if code_source.asset_id:
            asset_result = await db.execute(select(Asset).where(Asset.id == code_source.asset_id))
            asset = asset_result.scalar_one_or_none()

        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        session.status = "running"
        await db.commit()

    try:
        scanner_config: dict = {}
        if project.scanner_config:
            scanner_config = project.scanner_config.get(scan.scanner_type, {})

        # Fetch dynamic scanner credentials
        scanner_url = None
        scanner_api_key = None
        from app.models.scanner import ScannerEngine
        from app.models.workspace import Workspace
        async with AsyncSessionLocal() as db_session:
            workspace_id = session.workspace_id if hasattr(session, 'workspace_id') else project.workspace_id
            engine_res = await db_session.execute(
                select(ScannerEngine).where(
                    ScannerEngine.workspace_id == workspace_id,
                    ScannerEngine.engine_type == scan.scanner_type,
                    ScannerEngine.is_active == True
                )
            )
            engine = engine_res.scalars().first()
            if engine:
                scanner_url = engine.url
                scanner_api_key = engine.api_key
                
            workspace_res = await db_session.execute(
                select(Workspace).where(Workspace.id == workspace_id)
            )
            workspace = workspace_res.scalar_one_or_none()
            if workspace and workspace.ai_config:
                scanner_config["ai_config"] = workspace.ai_config

        # Use demo-transportes URL for ZAP if not configured (since it's a demo)
        target_url = asset.url if asset and asset.url else "http://demo-transportes:3000"

        adapter = get_adapter(scan.scanner_type)
        scan_request = ScanRequest(
            scan_id=str(scan_id),
            project_key=f"wicscan-{str(project.id)[:8]}",
            project_name=project.name,
            asset_id=str(code_source.asset_id) if code_source.asset_id else "",
            code_path=code_source.local_snapshot_path,
            target_url=target_url,
            github_url=code_source.github_url,
            github_branch=code_source.github_branch,
            github_token=code_source.github_token,
            scanner_url=scanner_url,
            scanner_api_key=scanner_api_key,
            ip_address=asset.ip_address if asset and hasattr(asset, "ip_address") else None,
            config={**scanner_config, **(scan.config or {})},
        )
        normalized_findings: list[dict] = await adapter.run(
            scan_request, settings.SCANNER_MANAGER_URL
        )

        saved_count = 0
        new_count = 0

        async with AsyncSessionLocal() as db:
            # Obtener el siguiente número de secuencia de hallazgo para este proyecto
            count_result = await db.execute(
                select(func.count(Finding.id))
                .join(Scan, Finding.scan_id == Scan.id)
                .join(ScanSession, Scan.session_id == ScanSession.id)
                .where(ScanSession.project_id == project.id)
            )
            next_seq = (count_result.scalar() or 0) + 1

            for nf in normalized_findings:
                fingerprint = nf.get("fingerprint")

                existing = None
                if fingerprint:
                    existing_result = await db.execute(
                        select(Finding)
                        .join(Scan, Finding.scan_id == Scan.id)
                        .join(ScanSession, Scan.session_id == ScanSession.id)
                        .where(
                            ScanSession.project_id == project.id,
                            Finding.fingerprint == fingerprint,
                            Finding.asset_id == code_source.asset_id,
                        )
                    )
                    existing = existing_result.scalars().first()

                if existing:
                    existing.last_seen_at = datetime.now(timezone.utc)
                    if existing.status == "resolved":
                        existing.status = "open"
                    existing.is_deduplicated = True
                else:
                    now = datetime.now(timezone.utc)
                    finding = Finding(
                        scan_id=scan_id,
                        asset_id=code_source.asset_id,
                        scanner=nf["scanner"],
                        scanner_rule_id=nf.get("scanner_rule_id"),
                        finding_type=nf["finding_type"],
                        category=nf["category"],
                        cwe=nf.get("cwe"),
                        owasp_category=nf.get("owasp_category"),
                        cvss_score=nf.get("cvss_score"),
                        severity=nf["severity"],
                        title=nf["title"],
                        description=nf.get("description"),
                        remediation_guidance=nf.get("remediation_guidance"),
                        file_path=nf.get("file_path"),
                        line_start=nf.get("line_start"),
                        line_end=nf.get("line_end"),
                        component=nf.get("component"),
                        effort=nf.get("effort"),
                        confidence=nf.get("confidence", 0.8),
                        evidence=nf.get("evidence"),
                        fingerprint=fingerprint,
                        finding_code=f"F-{next_seq:04d}",
                        first_detected_at=now,
                        last_seen_at=now,
                    )
                    db.add(finding)
                    await db.flush()
                    next_seq += 1
                    new_count += 1

                saved_count += 1

            scan_result = await db.execute(select(Scan).where(Scan.id == scan_id))
            scan_obj = scan_result.scalar_one()
            scan_obj.status = "completed"
            scan_obj.completed_at = datetime.now(timezone.utc)
            scan_obj.findings_count = saved_count

            await db.flush()
            await _maybe_complete_session(db, scan.session_id, saved_count, new_count)
            await db.commit()

        log.info("scan_completed", scan_id=str(scan_id), total=saved_count, new=new_count)
        return {"scan_id": str(scan_id), "findings": saved_count, "new": new_count}

    except Exception as exc:
        await _mark_scan_failed(scan_id, str(exc))
        raise


async def _maybe_complete_session(db, session_id: uuid.UUID, saved_count: int, new_count: int) -> None:
    """Mark session completed only when all its scans are done."""
    from sqlalchemy import and_
    pending_result = await db.execute(
        select(func.count(Scan.id)).where(
            Scan.session_id == session_id,
            Scan.status.notin_(["completed", "failed", "cancelled"]),
        )
    )
    pending = pending_result.scalar() or 0
    if pending == 0:
        session_result = await db.execute(select(ScanSession).where(ScanSession.id == session_id))
        session = session_result.scalar_one_or_none()
        if session:
            all_scans = (await db.execute(
                select(func.count(Scan.id)).where(Scan.session_id == session_id, Scan.status == "failed")
            )).scalar() or 0
            all_count = (await db.execute(
                select(func.count(Scan.id)).where(Scan.session_id == session_id)
            )).scalar() or 1
            session.status = "failed" if all_scans == all_count else "completed"
            session.completed_at = datetime.now(timezone.utc)
            session.total_findings_count = (session.total_findings_count or 0) + saved_count
            session.new_findings_count = (session.new_findings_count or 0) + new_count
