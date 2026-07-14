"""
Scanner Manager API

Endpoints:
  POST /api/v1/scan                    — trigger scan for an asset
  GET  /api/v1/scan/{scan_id}/status   — poll scan status
  GET  /api/v1/scan/{scan_id}/findings — fetch normalized findings
"""

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.responses import ORJSONResponse

from app.adapters.sonarqube import SonarQubeAdapter
from app.adapters.zap import ZapAdapter, get_zap_adapter
from app.adapters.nuclei import NucleiAdapter, get_nuclei_adapter
from app.adapters.openvas import OpenVASAdapter, get_openvas_adapter
from app.adapters.mobsf import MobSFAdapter, get_mobsf_adapter
from app.adapters.semgrep import SemgrepAdapter, get_semgrep_adapter
from app.config import get_settings
from app.normalizer.models import NormalizedFinding

log = structlog.get_logger(__name__)
settings = get_settings()

_redis: aioredis.Redis | None = None
_sonar_token: str = ""


async def _bootstrap_sonar_token() -> str:
    """
    Auto-generate a global SonarQube token using admin credentials.
    Called at startup if SONARQUBE_TOKEN is not set in env.
    Revokes any previous wicscan-scanner token first (idempotent).
    """
    token_name = "wicscan-scanner-manager"
    auth = (settings.SONARQUBE_ADMIN_USER, settings.SONARQUBE_ADMIN_PASSWORD)

    # Attempt to change the default password if this is a fresh instance
    if settings.SONARQUBE_ADMIN_PASSWORD != "admin":
        async with httpx.AsyncClient(base_url=settings.SONARQUBE_URL, auth=(settings.SONARQUBE_ADMIN_USER, "admin"), timeout=30.0) as setup_client:
            try:
                resp = await setup_client.post(
                    "/api/users/change_password",
                    data={
                        "login": settings.SONARQUBE_ADMIN_USER,
                        "previousPassword": "admin",
                        "password": settings.SONARQUBE_ADMIN_PASSWORD
                    }
                )
                if resp.status_code in (200, 204):
                    log.info("sonarqube_default_password_changed")
            except Exception as e:
                log.debug("sonarqube_password_change_skipped", reason=str(e))

    async with httpx.AsyncClient(base_url=settings.SONARQUBE_URL, timeout=30.0) as client:
        # Intenta revocar con el auth configurado y con el por defecto
        await client.post("/api/user_tokens/revoke", data={"name": token_name}, auth=auth)
        await client.post("/api/user_tokens/revoke", data={"name": token_name}, auth=(settings.SONARQUBE_ADMIN_USER, "admin"))
            
        resp = await client.post(
            "/api/user_tokens/generate",
            data={"name": token_name, "type": "USER_TOKEN"},
            auth=auth
        )
        
        # Si falló con 401, puede que SonarQube siga con admin:admin
        if resp.status_code == 401:
            log.info("sonarqube_auth_failed_trying_default_admin")
            resp = await client.post(
                "/api/user_tokens/generate",
                data={"name": token_name, "type": "USER_TOKEN"},
                auth=(settings.SONARQUBE_ADMIN_USER, "admin")
            )

        if resp.status_code == 400 and "already exists" in resp.text:
            # If it STILL exists, try to revoke again with explicitly providing login
            await client.post("/api/user_tokens/revoke", data={"name": token_name, "login": settings.SONARQUBE_ADMIN_USER}, auth=auth)
            await client.post("/api/user_tokens/revoke", data={"name": token_name, "login": settings.SONARQUBE_ADMIN_USER}, auth=(settings.SONARQUBE_ADMIN_USER, "admin"))
            resp = await client.post(
                "/api/user_tokens/generate",
                data={"name": token_name, "type": "USER_TOKEN"},
                auth=(settings.SONARQUBE_ADMIN_USER, "admin")
            )
            if resp.status_code != 200 and resp.status_code != 201:
                resp = await client.post(
                    "/api/user_tokens/generate",
                    data={"name": token_name, "type": "USER_TOKEN"},
                    auth=auth
                )

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"SonarQube token bootstrap failed ({resp.status_code}): {resp.text[:200]}"
            )
        token = resp.json()["token"]
        log.info("sonarqube_token_bootstrapped", token_name=token_name)
        return token


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _sonar_token

    _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    if settings.SONARQUBE_TOKEN:
        try:
            async with httpx.AsyncClient(base_url=settings.SONARQUBE_URL, timeout=10.0) as client:
                resp = await client.get("/api/authentication/validate", auth=(settings.SONARQUBE_TOKEN, ""))
                if resp.status_code == 200 and resp.json().get("valid") is True:
                    _sonar_token = settings.SONARQUBE_TOKEN
                    log.info("sonarqube_using_env_token")
                else:
                    log.warning("sonarqube_env_token_invalid_bootstrapping_new")
                    _sonar_token = await _bootstrap_sonar_token()
        except Exception as exc:
            log.warning("sonarqube_token_validation_failed", error=str(exc))
            _sonar_token = await _bootstrap_sonar_token()
    else:
        try:
            _sonar_token = await _bootstrap_sonar_token()
        except Exception as exc:
            log.warning("sonarqube_bootstrap_failed", error=str(exc))
            _sonar_token = ""

    log.info("scanner_manager_startup")
    yield
    if _redis:
        await _redis.aclose()


app = FastAPI(
    title=settings.APP_NAME,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)


def get_redis() -> aioredis.Redis:
    return _redis


def get_sonarqube_adapter(url: str | None = None, token: str | None = None) -> SonarQubeAdapter:
    return SonarQubeAdapter(
        base_url=url or settings.SONARQUBE_URL,
        token=token or _sonar_token
    )


SCAN_STATE_PREFIX = "scan_state:"
SCAN_FINDINGS_PREFIX = "scan_findings:"
FINDINGS_TTL = 3600  # 1 hour


async def _execute_sonarqube_scan(
    scan_id: str,
    project_key: str,
    project_name: str,
    asset_id: str,
    code_path: str | None,
    github_url: str | None,
    github_branch: str | None,
    github_token: str | None,
    adapter: SonarQubeAdapter,
    redis: aioredis.Redis,
) -> None:
    await redis.hset(f"{SCAN_STATE_PREFIX}{scan_id}", mapping={"status": "running", "error": ""})

    work_dir = None
    try:
        # 1. Ensure SonarQube project exists (created automatically if missing)
        log.info("sonarqube_ensure_project", project_key=project_key)
        await adapter.ensure_project_exists(project_key, project_name or project_key)

        # 2. Generate a per-scan project analysis token (no manual setup needed)
        analysis_token = await adapter.generate_token(f"scan-{scan_id[:8]}", project_key)

        # 3. Prepare local code directory
        work_dir = tempfile.mkdtemp(prefix=f"wicscan-{scan_id[:8]}-")

        if code_path and code_path.endswith(".zip") and os.path.exists(code_path):
            log.info("sonarqube_extracting_zip", path=code_path)
            with zipfile.ZipFile(code_path, "r") as zf:
                zf.extractall(work_dir)
        elif github_url:
            branch = github_branch.strip() if github_branch else ""
            clone_url = github_url
            if github_token and clone_url.startswith("https://"):
                clone_url = clone_url.replace("https://", f"https://{github_token}@")
            log.info("sonarqube_cloning_repo", url=github_url, branch=branch or "default")
            
            git_args = ["git", "clone", "--depth=1"]
            if branch:
                git_args.extend(["-b", branch])
            git_args.extend([clone_url, work_dir])
            
            result = subprocess.run(
                git_args,
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                err_msg = result.stderr[-300:]
                if github_token:
                    err_msg = err_msg.replace(github_token, "***")
                raise RuntimeError(f"git clone failed: {err_msg}")
        else:
            raise RuntimeError(
                f"No accessible code source (code_path={code_path!r}, github_url={github_url!r})"
            )

        # 4. Run sonar-scanner CLI
        log.info("sonarqube_running_scanner", project_key=project_key)
        sonar_cmd = [
            "sonar-scanner",
            f"-Dsonar.projectKey={project_key}",
            f"-Dsonar.projectName={project_name or project_key}",
            "-Dsonar.sources=.",
            f"-Dsonar.host.url={settings.SONARQUBE_URL}",
            f"-Dsonar.token={analysis_token}",
            "-Dsonar.scm.disabled=true",
            "-Dsonar.sourceEncoding=UTF-8",
        ]

        loop = asyncio.get_event_loop()
        proc_result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                sonar_cmd, cwd=work_dir,
                capture_output=True, text=True, timeout=600,
            ),
        )

        if proc_result.returncode != 0:
            raise RuntimeError(
                f"sonar-scanner exited {proc_result.returncode}: {proc_result.stderr[-500:]}"
            )

        # 5. Extract CE task ID from scanner stdout and wait for SonarQube to process it
        task_id = None
        for line in proc_result.stdout.splitlines():
            if "ceTaskId=" in line:
                task_id = line.split("ceTaskId=")[-1].strip()
                break

        if task_id:
            log.info("sonarqube_waiting_ce_task", task_id=task_id)
            await adapter.wait_for_analysis(task_id)
        else:
            await asyncio.sleep(15)

        # 6. Fetch and normalize findings
        findings: list[NormalizedFinding] = await adapter.run_full_analysis_and_fetch(
            project_key=project_key,
            asset_id=asset_id,
        )

        findings_payload = json.dumps([f.to_dict() for f in findings])
        await redis.setex(f"{SCAN_FINDINGS_PREFIX}{scan_id}", FINDINGS_TTL, findings_payload)
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "completed", "count": len(findings), "error": ""},
        )
        log.info("scan_completed", scan_id=scan_id, findings=len(findings))

    except Exception as exc:
        log.error("scan_failed", scan_id=scan_id, error=str(exc))
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "failed", "error": str(exc)[:500]},
        )
    finally:
        if work_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)


async def _execute_nuclei_scan(
    scan_id: str,
    target: str,
    asset_id: str,
    severity: list[str] | None,
    templates: list[str] | None,
    custom_headers: list[str] | None,
    adapter: NucleiAdapter,
    redis: aioredis.Redis,
) -> None:
    await redis.hset(f"{SCAN_STATE_PREFIX}{scan_id}", mapping={"status": "running", "error": ""})
    try:
        if not target:
            raise RuntimeError("Nuclei scan requires a target (URL or host)")

        findings = await adapter.run_full_analysis_and_fetch(
            target=target,
            asset_id=asset_id,
            severity=severity,
            templates=templates,
            custom_headers=custom_headers,
        )

        findings_payload = json.dumps([f.to_dict() for f in findings])
        await redis.setex(f"{SCAN_FINDINGS_PREFIX}{scan_id}", FINDINGS_TTL, findings_payload)
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "completed", "count": len(findings), "error": ""},
        )
        log.info("nuclei_scan_completed", scan_id=scan_id, findings=len(findings))

    except Exception as exc:
        log.error("nuclei_scan_failed", scan_id=scan_id, error=str(exc))
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "failed", "error": str(exc)[:500]},
        )


async def _execute_openvas_scan(
    scan_id: str,
    target: str,
    asset_id: str,
    scan_config: str,
    adapter: OpenVASAdapter,
    redis: aioredis.Redis,
) -> None:
    await redis.hset(f"{SCAN_STATE_PREFIX}{scan_id}", mapping={"status": "running", "error": ""})
    try:
        if not target:
            raise RuntimeError("OpenVAS scan requires a target (IP, hostname or CIDR)")

        findings = await adapter.run_full_analysis_and_fetch(
            target=target,
            asset_id=asset_id,
            scan_config=scan_config,
        )

        findings_payload = json.dumps([f.to_dict() for f in findings])
        await redis.setex(f"{SCAN_FINDINGS_PREFIX}{scan_id}", FINDINGS_TTL, findings_payload)
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "completed", "count": len(findings), "error": ""},
        )
        log.info("openvas_scan_completed", scan_id=scan_id, findings=len(findings))

    except Exception as exc:
        log.error("openvas_scan_failed", scan_id=scan_id, error=str(exc))
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "failed", "error": str(exc)[:500]},
        )


async def _execute_zap_scan(
    scan_id: str,
    target_url: str,
    adapter: ZapAdapter,
    redis: aioredis.Redis,
) -> None:
    await redis.hset(f"{SCAN_STATE_PREFIX}{scan_id}", mapping={"status": "running", "error": ""})
    try:
        if not target_url:
            raise RuntimeError("ZAP scan requires a target_url")

        findings = await adapter.run_full_analysis_and_fetch(target_url=target_url)

        findings_payload = json.dumps([f.to_dict() for f in findings])
        await redis.setex(f"{SCAN_FINDINGS_PREFIX}{scan_id}", FINDINGS_TTL, findings_payload)
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "completed", "count": len(findings), "error": ""},
        )
        log.info("zap_scan_completed", scan_id=scan_id, findings=len(findings))

    except Exception as exc:
        err_str = str(exc)
        if "RetryError" in err_str or "ConnectError" in err_str:
            err_str = "Error de conexión con el escáner ZAP. Es posible que el servicio se haya caído o reiniciado por falta de memoria."
        elif "ReadTimeout" in repr(exc):
            err_str = "El escáner ZAP tardó demasiado en responder (ReadTimeout). Puede estar sobrecargado."
        elif not err_str:
            err_str = f"Error desconocido: {repr(exc)}"
        
        log.error("zap_scan_failed", scan_id=scan_id, error=err_str)
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "failed", "error": err_str[:500]},
        )

async def _execute_mobsf_scan(
    scan_id: str,
    code_path: str | None,
    github_url: str | None,
    github_branch: str | None,
    github_token: str | None,
    scan_type: str,
    adapter: MobSFAdapter,
    redis: aioredis.Redis,
) -> None:
    await redis.hset(f"{SCAN_STATE_PREFIX}{scan_id}", mapping={"status": "running", "error": ""})
    work_dir = None
    try:
        scan_hash = None
        if code_path and os.path.exists(code_path):
            log.info("mobsf_uploading_local_file", path=code_path)
            scan_hash = await adapter.upload_file(code_path)
        elif github_url:
            work_dir = tempfile.mkdtemp(prefix=f"wicscan-{scan_id[:8]}-")
            branch = github_branch.strip() if github_branch else ""
            clone_url = github_url
            if github_token and clone_url.startswith("https://"):
                clone_url = clone_url.replace("https://", f"https://{github_token}@")
            log.info("mobsf_cloning_repo", url=github_url, branch=branch or "default")
            
            git_args = ["git", "clone", "--depth=1"]
            if branch:
                git_args.extend(["-b", branch])
            git_args.extend([clone_url, work_dir])
            
            result = subprocess.run(
                git_args,
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed for MobSF: {result.stderr[-300:]}")
            
            # MobSF expects APK/IPA or ZIP. Since this is repo, we ZIP it.
            zip_path = os.path.join(work_dir, "source.zip")
            # Create zip natively using python to avoid subprocess dependency on 'zip' command
            import zipfile
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(work_dir):
                    for file in files:
                        if file == "source.zip": continue
                        f_path = os.path.join(root, file)
                        zipf.write(f_path, os.path.relpath(f_path, work_dir))
            
            log.info("mobsf_uploading_git_zip")
            scan_hash = await adapter.upload_file(zip_path)
        else:
            raise RuntimeError("No accessible code source for MobSF")

        if not scan_hash:
            raise RuntimeError("Failed to get scan_hash from MobSF upload")

        log.info("mobsf_running_scan", scan_hash=scan_hash)
        report = await adapter.scan(scan_hash, scan_type=scan_type)

        findings = adapter.get_findings(report)

        findings_payload = json.dumps([f.to_dict() for f in findings])
        await redis.setex(f"{SCAN_FINDINGS_PREFIX}{scan_id}", FINDINGS_TTL, findings_payload)
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "completed", "count": len(findings), "error": ""},
        )
        log.info("mobsf_scan_completed", scan_id=scan_id, findings=len(findings))

    except Exception as exc:
        log.error("mobsf_scan_failed", scan_id=scan_id, error=str(exc))
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "failed", "error": str(exc)[:500]},
        )
    finally:
        if work_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)


async def _execute_semgrep_scan(
    scan_id: str,
    code_path: str | None,
    github_url: str | None,
    github_branch: str | None,
    github_token: str | None,
    adapter: SemgrepAdapter,
    redis: aioredis.Redis,
) -> None:
    await redis.hset(f"{SCAN_STATE_PREFIX}{scan_id}", mapping={"status": "running", "error": ""})
    work_dir = None
    try:
        # Prepare code
        if github_url:
            work_dir = tempfile.mkdtemp(prefix=f"wicscan_semgrep_git_{scan_id}_")
            branch = github_branch or "default"
            log.info("semgrep_cloning_repo", url=github_url, branch=branch)
            git_cmd = ["git", "clone", "--depth", "1"]
            if github_branch and github_branch != "default":
                git_cmd.extend(["-b", github_branch])
            if github_token:
                auth_url = github_url.replace("https://", f"https://oauth2:{github_token}@")
                git_cmd.append(auth_url)
            else:
                git_cmd.append(github_url)
            git_cmd.append(work_dir)
            
            proc = await asyncio.create_subprocess_exec(
                *git_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"git clone failed for Semgrep: {stderr.decode()[:300]}")
            
            scan_path = work_dir
        elif code_path and os.path.exists(code_path):
            work_dir = tempfile.mkdtemp(prefix=f"wicscan_semgrep_zip_{scan_id}_")
            if code_path.endswith(".zip"):
                log.info("semgrep_extracting_zip", path=code_path)
                with zipfile.ZipFile(code_path, "r") as z:
                    z.extractall(work_dir)
                scan_path = work_dir
            else:
                scan_path = code_path
        else:
            raise RuntimeError("No accessible code source for Semgrep")

        findings = await adapter.scan(scan_path)
        
        findings_payload = json.dumps([f.to_dict() for f in findings])
        await redis.setex(f"{SCAN_FINDINGS_PREFIX}{scan_id}", FINDINGS_TTL, findings_payload)
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "completed", "count": len(findings), "error": ""},
        )
        log.info("semgrep_scan_completed", scan_id=scan_id, findings=len(findings))

    except Exception as exc:
        log.error("semgrep_scan_failed", scan_id=scan_id, error=str(exc))
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "failed", "error": str(exc)[:500]},
        )
    finally:
        if work_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)


@app.post("/api/v1/scan", status_code=202)
async def trigger_scan(
    payload: dict,
    background_tasks: BackgroundTasks,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    scan_id = payload["scan_id"]
    scanner_type = payload.get("scanner_type", "sonarqube")
    project_key = payload.get("project_key") or payload.get("project_id") or scan_id
    project_name = payload.get("project_name") or project_key
    asset_id = payload.get("asset_id", "")
    ip_address = payload.get("ip_address")
    url = payload.get("url")
    code_path = payload.get("code_path")
    github_url = payload.get("github_url")
    github_branch = payload.get("github_branch", "main")
    github_token = payload.get("github_token")
    scanner_url = payload.get("scanner_url")
    scanner_api_key = payload.get("scanner_api_key")
    mobsf_scan_type = payload.get("mobsf_scan_type", "apk")

    await redis.hset(f"{SCAN_STATE_PREFIX}{scan_id}", mapping={"status": "pending", "error": ""})

    if scanner_type == "sonarqube":
        adapter = get_sonarqube_adapter(url=scanner_url, token=scanner_api_key)
        background_tasks.add_task(
            _execute_sonarqube_scan,
            scan_id, project_key, project_name, asset_id,
            code_path, github_url, github_branch, github_token,
            adapter, redis,
        )
    elif scanner_type == "zap":
        target_url = url or payload.get("target_url")
        adapter = get_zap_adapter(url=scanner_url, api_key=scanner_api_key)
        background_tasks.add_task(
            _execute_zap_scan,
            scan_id, target_url, adapter, redis,
        )
    elif scanner_type == "nuclei":
        target = ip_address or url or payload.get("target_url") or payload.get("target")
        severity = payload.get("severity")
        templates = payload.get("templates")
        config = payload.get("config", {})
        custom_headers = config.get("custom_headers")
        adapter = get_nuclei_adapter()
        background_tasks.add_task(
            _execute_nuclei_scan,
            scan_id, target, asset_id, severity, templates, custom_headers, adapter, redis,
        )
    elif scanner_type == "openvas":
        target = ip_address or url or payload.get("target") or payload.get("target_url")
        scan_config = payload.get("scan_config", "full")
        adapter = get_openvas_adapter()
        background_tasks.add_task(
            _execute_openvas_scan,
            scan_id, target, asset_id, scan_config, adapter, redis,
        )
    elif scanner_type == "mobsf":
        adapter = get_mobsf_adapter(url=scanner_url, api_key=scanner_api_key)
        background_tasks.add_task(
            _execute_mobsf_scan,
            scan_id, code_path, github_url, github_branch, github_token, mobsf_scan_type,
            adapter, redis,
        )
    elif scanner_type == "semgrep":
        adapter = get_semgrep_adapter()
        background_tasks.add_task(
            _execute_semgrep_scan,
            scan_id, code_path, github_url, github_branch, github_token,
            adapter, redis,
        )
    else:
        await redis.hset(
            f"{SCAN_STATE_PREFIX}{scan_id}",
            mapping={"status": "failed", "error": f"Unsupported scanner: {scanner_type}"},
        )
        return {"error": f"Unsupported scanner type: {scanner_type}"}

    return {"scan_id": scan_id, "status": "pending"}


@app.get("/api/v1/scan/{scan_id}/status")
async def get_scan_status(
    scan_id: str,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    state = await redis.hgetall(f"{SCAN_STATE_PREFIX}{scan_id}")
    if not state:
        return {"scan_id": scan_id, "status": "not_found"}
    return {
        "scan_id": scan_id,
        "status": state.get("status", "unknown"),
        "findings_count": int(state.get("count", 0)),
        "error": state.get("error") or None,
    }


@app.get("/api/v1/scan/{scan_id}/findings")
async def get_scan_findings(
    scan_id: str,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    raw = await redis.get(f"{SCAN_FINDINGS_PREFIX}{scan_id}")
    if raw is None:
        state = await redis.hgetall(f"{SCAN_STATE_PREFIX}{scan_id}")
        if not state or state.get("status") != "completed":
            return []
    return json.loads(raw) if raw else []


@app.get("/api/v1/scanners/sonarqube/snippet")
async def get_sonarqube_snippet(
    project_key: str,
    file_path: str,
    line_start: int,
    line_end: int,
):
    # The component key in SonarQube is typically project_key:file_path
    import re as _re
    def _strip_html(text: str) -> str:
        return _re.sub(r"<[^>]+>", "", text or "")

    component_key = f"{project_key}:{file_path}"
    adapter = get_sonarqube_adapter()
    try:
        lines = await adapter.fetch_source_lines(component_key, line_start, line_end)
        # SonarQube devuelve el código con HTML de syntax highlighting — lo limpiamos
        clean = [{"line": ln.get("line"), "code": _strip_html(ln.get("code", ""))} for ln in lines]
        return {"snippet": clean}
    except Exception as e:
        log.error("snippet_fetch_failed", error=str(e), component=component_key)
        return {"error": str(e), "snippet": []}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "scanner-manager"}
