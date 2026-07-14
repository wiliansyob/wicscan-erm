"""
Scanner Adapter contract (F1).

Each scanner is a thin facade that:
  1. run()  — triggers the scanner (via scanner-manager HTTP or locally) and returns raw output
  2. parse() — normalises raw output to a list of finding dicts

For HTTP-backed scanners (sonarqube, zap) the scanner-manager already normalises;
parse() is a pass-through. Local scanners (ai_review, future) will override parse().
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

import httpx
import structlog

log = structlog.get_logger(__name__)

MAX_POLL_ATTEMPTS = 180
POLL_INTERVAL_SECONDS = 10

# A finding dict as returned/expected by the scanner-manager and scan_tasks.py
RawOutput = list[dict]


@dataclass
class ScanRequest:
    scan_id: str
    project_key: str
    project_name: str
    asset_id: str
    code_path: str | None = None
    target_url: str | None = None
    github_url: str | None = None
    github_branch: str | None = None
    github_token: str | None = None
    scanner_url: str | None = None
    scanner_api_key: str | None = None
    ip_address: str | None = None
    config: dict = field(default_factory=dict)


class ScannerAdapter(ABC):
    """Common contract for every scanner source (tool, service, or AI agent)."""

    scanner_type: ClassVar[str]

    @abstractmethod
    def _build_payload(self, request: ScanRequest) -> dict:
        """Build the scanner-specific JSON body for the scanner-manager POST."""
        ...

    async def run(self, request: ScanRequest, scanner_manager_url: str) -> RawOutput:
        """
        Trigger + poll + fetch findings from the scanner-manager.
        HTTP-backed adapters share this implementation.
        Local adapters (ai_review) override the whole method.
        """
        payload = self._build_payload(request)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{scanner_manager_url}/api/v1/scan", json=payload)
            resp.raise_for_status()

        for _ in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    status_resp = await client.get(
                        f"{scanner_manager_url}/api/v1/scan/{request.scan_id}/status"
                    )
                    status_resp.raise_for_status()
                    status_data = status_resp.json()

                if status_data["status"] == "completed":
                    break
                if status_data["status"] == "failed":
                    raise RuntimeError(status_data.get("error", "Scanner failed"))
            except httpx.RequestError as e:
                log.warning("Transient network error during poll", error=str(e))
                continue
        else:
            raise TimeoutError("Scan did not complete within expected time")

        async with httpx.AsyncClient(timeout=30.0) as client:
            findings_resp = await client.get(
                f"{scanner_manager_url}/api/v1/scan/{request.scan_id}/findings"
            )
            findings_resp.raise_for_status()
            raw: RawOutput = findings_resp.json()

        return raw

    def parse(self, raw: RawOutput) -> RawOutput:
        """
        Normalise raw output to finding dicts.
        Default: pass-through (scanner-manager already normalises HTTP responses).
        Local adapters (ai_review) override this to map LLM output → finding dicts.
        """
        return raw
