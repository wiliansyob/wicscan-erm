import asyncio
import hashlib
import json
import logging

import httpx

from app.normalizer.models import NormalizedFinding
from app.config import get_settings

log = logging.getLogger(__name__)

_THREAT_SEVERITY: dict[str, str] = {
    "critical": "critical",
    "high":     "high",
    "medium":   "medium",
    "low":      "low",
    "log":      "info",
}

_POLL_INTERVAL = 30   # seconds between status checks
_POLL_TIMEOUT  = 7200 # max 2 hours


def _severity_from_cvss(cvss: float | None, threat: str) -> str:
    if cvss is not None:
        if cvss >= 9.0: return "critical"
        if cvss >= 7.0: return "high"
        if cvss >= 4.0: return "medium"
        if cvss > 0:    return "low"
    return _THREAT_SEVERITY.get(threat.lower(), "info")


def _normalize(results: list[dict], asset_id: str) -> list[NormalizedFinding]:
    findings: list[NormalizedFinding] = []
    for r in results:
        try:
            threat   = r.get("threat", "")
            cvss     = r.get("cvss_base") or r.get("severity")
            severity = _severity_from_cvss(cvss, threat)

            # Extract CVE from refs
            cve = next(
                (ref["id"] for ref in r.get("refs", []) if ref.get("type") == "cve"),
                None,
            )

            host = r.get("host", "")
            port = r.get("port", "")
            component = f"{host}:{port}" if port and port != "general" else host

            fingerprint = hashlib.sha256(
                json.dumps(
                    ["openvas", r.get("oid", ""), host, port],
                    sort_keys=True,
                ).encode()
            ).hexdigest()

            evidence: dict = {
                "oid":    r.get("oid"),
                "host":   host,
                "port":   port,
                "threat": threat,
            }
            if cve:
                evidence["cve_id"] = cve

            confidence = 0.9 if severity in ("critical", "high") else 0.75
            effort     = "high" if severity in ("critical", "high") else "medium" if severity == "medium" else "low"

            findings.append(NormalizedFinding(
                scanner=              "openvas",
                scanner_rule_id=      r.get("oid") or None,
                finding_type=         "network_scan",
                category=             "known_vulnerability" if cve else "security_misconfiguration",
                cwe=                  None,
                owasp_category=       None,
                cvss_score=           float(cvss) if cvss is not None else None,
                severity=             severity,
                title=                r.get("name") or "OpenVAS finding",
                description=          r.get("description") or None,
                remediation_guidance= None,
                file_path=            None,
                line_start=           None,
                line_end=             None,
                component=            component or None,
                effort=               effort,
                confidence=           confidence,
                evidence=             evidence,
                fingerprint=          fingerprint,
            ))
        except Exception as exc:
            log.warning("openvas_normalize_error: %s | raw=%s", exc, r)

    return findings


class OpenVASAdapter:
    def __init__(self, base_url: str):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    async def start_scan(self, target: str, scan_config: str = "full") -> str:
        resp = await self._client.post(
            "/scan",
            json={"target": target, "scan_config": scan_config},
        )
        resp.raise_for_status()
        return resp.json()["task_id"]

    async def wait_for_completion(self, task_id: str) -> None:
        elapsed = 0
        while elapsed < _POLL_TIMEOUT:
            await asyncio.sleep(_POLL_INTERVAL)
            elapsed += _POLL_INTERVAL
            resp = await self._client.get(f"/scan/{task_id}/status")
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "")
            if status == "done":
                return
            if status in ("stopped", "failed"):
                raise RuntimeError(f"OpenVAS scan ended with status: {status}")
        raise RuntimeError("OpenVAS scan timed out after 2 hours")

    async def get_findings(self, task_id: str, asset_id: str) -> list[NormalizedFinding]:
        resp = await self._client.get(f"/scan/{task_id}/results", timeout=120.0)
        resp.raise_for_status()
        return _normalize(resp.json().get("results", []), asset_id)

    async def run_full_analysis_and_fetch(
        self,
        target: str,
        asset_id: str,
        scan_config: str = "full",
    ) -> list[NormalizedFinding]:
        task_id = await self.start_scan(target, scan_config)
        log.info("openvas_scan_started", task_id=task_id, target=target)
        await self.wait_for_completion(task_id)
        return await self.get_findings(task_id, asset_id)


def get_openvas_adapter() -> OpenVASAdapter:
    return OpenVASAdapter(base_url=get_settings().OPENVAS_URL)
