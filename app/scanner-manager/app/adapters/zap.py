"""
OWASP ZAP Adapter — wraps the ZAP REST API.

Responsibility:
- Trigger Spider and Active Scan
- Poll for completion
- Fetch alerts
- Normalize to NormalizedFinding
"""

import asyncio
import hashlib
from urllib.parse import quote

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.normalizer.models import NormalizedFinding

log = structlog.get_logger(__name__)
settings = get_settings()

class ZapError(Exception):
    pass


class ZapAdapter:
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        # Using default ZAP API endpoints that don't strictly require API Key if disabled

    def _client(self) -> httpx.AsyncClient:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-ZAP-API-Key"] = self.api_key
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=120.0,
            headers=headers
        )

    @retry(stop=stop_after_attempt(240), wait=wait_exponential(min=5, max=15))
    async def wait_for_scan(self, scan_type: str, scan_id: str) -> None:
        async with self._client() as client:
            resp = await client.get(f"/JSON/{scan_type}/view/status/", params={"scanId": scan_id})
            resp.raise_for_status()
            status = resp.json().get("status")
            
            log.debug("zap_scan_poll", type=scan_type, scan_id=scan_id, status=status)
            if status == "100":
                return
            raise ZapError(f"{scan_type} scan still pending: {status}%")

    async def run_full_analysis_and_fetch(self, target_url: str) -> list[NormalizedFinding]:
        """
        Triggers a ZAP Spider followed by an Active Scan on the target_url.
        Returns normalized findings.
        """
        async with self._client() as client:
            # 1. Start Spider
            log.info("zap_starting_spider", url=target_url)
            spider_resp = await client.get("/JSON/spider/action/scan/", params={"url": target_url})
            spider_resp.raise_for_status()
            spider_id = spider_resp.json().get("scan")
            if not spider_id:
                raise ZapError("Failed to start ZAP Spider")
            
            await self.wait_for_scan("spider", spider_id)
            log.info("zap_spider_completed", url=target_url)

            # 2. Start Active Scan
            log.info("zap_starting_ascan", url=target_url)
            ascan_resp = await client.get("/JSON/ascan/action/scan/", params={"url": target_url, "recurse": "true", "inScopeOnly": "false"})
            ascan_resp.raise_for_status()
            ascan_id = ascan_resp.json().get("scan")
            if not ascan_id:
                raise ZapError("Failed to start ZAP Active Scan")
            
            await self.wait_for_scan("ascan", ascan_id)
            log.info("zap_ascan_completed", url=target_url)

            # 3. Fetch Alerts
            log.info("zap_fetching_alerts", url=target_url)
            alerts_resp = await client.get("/JSON/core/view/alerts/", params={"baseurl": target_url})
            alerts_resp.raise_for_status()
            alerts = alerts_resp.json().get("alerts", [])
        
        return self._normalize_alerts(alerts)

    def _normalize_alerts(self, alerts: list[dict]) -> list[NormalizedFinding]:
        findings = []
        for a in alerts:
            # Map ZAP Risk to WicScan Severity
            # High -> high/critical, Medium -> medium, Low -> low, Informational -> info
            risk = a.get("risk", "").lower()
            if "high" in risk:
                severity = "critical" if a.get("confidence") == "High" else "high"
            elif "medium" in risk:
                severity = "medium"
            elif "low" in risk:
                severity = "low"
            else:
                severity = "info"

            title = a.get("name", "Unknown Alert")
            desc = a.get("description", "")
            url = a.get("url", "")
            param = a.get("param", "")
            attack = a.get("attack", "")
            evidence_str = a.get("evidence", "")

            # Deduplication fingerprint
            fp_base = f"zap:{title}:{url}:{param}".encode("utf-8")
            fingerprint = hashlib.sha256(fp_base).hexdigest()

            evidence_dict = {
                "url": url,
                "param": param,
                "attack": attack,
                "evidence": evidence_str,
                "method": a.get("method", "")
            }

            findings.append(NormalizedFinding(
                scanner="zap",
                scanner_rule_id=str(a.get("pluginId", "")),
                finding_type="dast",
                category=title.lower().replace(" ", "_"),
                cwe=f"CWE-{a.get('cweid')}" if a.get("cweid") and str(a.get("cweid")) != "-1" else None,
                owasp_category=None,
                cvss_score=None,
                severity=severity,
                title=title,
                description=desc,
                remediation_guidance=a.get("solution"),
                file_path=url,
                line_start=None,
                line_end=None,
                component="web",
                effort="medium",
                confidence=0.9 if a.get("confidence") == "High" else 0.5,
                evidence=evidence_dict,
                fingerprint=fingerprint
            ))
        return findings

def get_zap_adapter(url: str | None = None, api_key: str | None = None) -> ZapAdapter:
    zap_url = url or "http://zap:8080"
    return ZapAdapter(base_url=zap_url, api_key=api_key)
