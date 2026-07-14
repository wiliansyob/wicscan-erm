"""
SonarQube Adapter — wraps the SonarQube Web API.

Responsibilities:
- Trigger analysis (via sonar-scanner CLI or API task)
- Poll task status
- Fetch all issues with pagination
- Pass raw issues to NormalizationPipeline
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlencode

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.normalizer.models import NormalizedFinding
from app.normalizer.pipeline import pipeline

log = structlog.get_logger(__name__)
settings = get_settings()

PAGE_SIZE = 500
MAX_RESULTS = 10_000  # SonarQube CE limit


class SonarQubeError(Exception):
    pass


class SonarQubeAdapter:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.auth = (token, "")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            auth=self.auth,
            timeout=30.0,
            headers={"Accept": "application/json"},
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def get_project_status(self, project_key: str) -> dict:
        async with self._client() as client:
            resp = await client.get(
                "/api/qualitygates/project_status",
                params={"projectKey": project_key},
            )
            resp.raise_for_status()
            return resp.json()

    async def ensure_project_exists(self, project_key: str, project_name: str) -> dict:
        async with self._client() as client:
            # Check if project exists
            search_resp = await client.get(
                "/api/projects/search",
                params={"projects": project_key},
            )
            search_resp.raise_for_status()
            components = search_resp.json().get("components", [])
            if components:
                return components[0]

            # Create project
            create_resp = await client.post(
                "/api/projects/create",
                data={"name": project_name, "project": project_key, "visibility": "private"},
            )
            if create_resp.status_code not in (200, 201):
                raise SonarQubeError(f"Failed to create project: {create_resp.text}")
            return create_resp.json().get("project", {})

    async def generate_token(self, token_name: str, project_key: str) -> str:
        async with self._client() as client:
            resp = await client.post(
                "/api/user_tokens/generate",
                data={"name": token_name, "type": "PROJECT_ANALYSIS_TOKEN", "projectKey": project_key},
            )
            resp.raise_for_status()
            return resp.json()["token"]

    @retry(stop=stop_after_attempt(60), wait=wait_exponential(min=5, max=15))
    async def wait_for_analysis(self, task_id: str) -> dict:
        async with self._client() as client:
            resp = await client.get("/api/ce/task", params={"id": task_id})
            resp.raise_for_status()
            task = resp.json().get("task", {})
            status = task.get("status")

            log.debug("sonarqube_task_poll", task_id=task_id, status=status)
            if status in ("SUCCESS", "FAILED", "CANCELLED"):
                return task
            raise SonarQubeError(f"Task still pending: {status}")

    async def fetch_all_issues(self, project_key: str) -> list[dict]:
        """Fetch only security-relevant issues (VULNERABILITY, BUG, SECURITY_HOTSPOT).
        CODE_SMELL is excluded — it's technical debt, not a security risk."""
        issues: list[dict] = []
        page = 1

        async with self._client() as client:
            while True:
                params = {
                    "componentKeys": project_key,
                    "types": "VULNERABILITY,BUG",
                    "ps": PAGE_SIZE,
                    "p": page,
                    "additionalFields": "rules",
                }
                resp = await client.get("/api/issues/search", params=params)
                resp.raise_for_status()
                data = resp.json()

                batch = data.get("issues", [])
                issues.extend(batch)

                total = data.get("paging", {}).get("total", 0)
                log.debug("sonarqube_issues_page", project=project_key, page=page, batch=len(batch), total=total)

                if len(issues) >= total or len(issues) >= MAX_RESULTS or not batch:
                    break
                page += 1

        log.info("sonarqube_security_issues_fetched", project=project_key, total=len(issues))
        return issues

    async def fetch_security_hotspots(self, project_key: str) -> list[dict]:
        """Security hotspots use a separate API endpoint."""
        hotspots: list[dict] = []
        page = 1

        async with self._client() as client:
            while True:
                resp = await client.get(
                    "/api/hotspots/search",
                    params={"projectKey": project_key, "ps": PAGE_SIZE, "p": page},
                )
                if resp.status_code == 404:
                    break
                resp.raise_for_status()
                data = resp.json()

                batch = data.get("hotspots", [])
                # Normalize hotspot format to match issues format
                for h in batch:
                    h["type"] = "SECURITY_HOTSPOT"
                    h["severity"] = h.get("vulnerabilityProbability", "MINOR")
                hotspots.extend(batch)

                total = data.get("paging", {}).get("total", 0)
                if len(hotspots) >= total or not batch:
                    break
                page += 1

        return hotspots

    async def fetch_source_lines(self, component_key: str, line_start: int, line_end: int) -> list[dict]:
        """Fetch source code lines from SonarQube."""
        async with self._client() as client:
            resp = await client.get(
                "/api/sources/lines",
                params={
                    "key": component_key,
                    "from": max(1, line_start),
                    "to": line_end
                }
            )
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            return resp.json().get("sources", [])

    async def run_full_analysis_and_fetch(
        self,
        project_key: str,
        asset_id: str,
    ) -> list[NormalizedFinding]:
        """
        Fetch existing analysis results (assumes sonar-scanner was already run externally
        via CI/CD or will be run via the scanner-manager CLI trigger).
        """
        issues = await self.fetch_all_issues(project_key)
        hotspots = await self.fetch_security_hotspots(project_key)
        all_raw = issues + hotspots

        return pipeline.normalize_sonarqube_issues(all_raw, asset_id)

    async def get_analysis_status(self, project_key: str) -> dict:
        async with self._client() as client:
            resp = await client.get(
                "/api/ce/component",
                params={"component": project_key},
            )
            resp.raise_for_status()
            data = resp.json()
            queue = data.get("queue", [])
            current = data.get("current", {})
            return {
                "has_analysis": bool(current),
                "current_status": current.get("status"),
                "task_id": current.get("id"),
                "queued": len(queue),
            }


def get_sonarqube_adapter() -> SonarQubeAdapter:
    return SonarQubeAdapter(
        base_url=settings.SONARQUBE_URL,
        token=settings.SONARQUBE_TOKEN,
    )
