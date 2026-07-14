import hashlib
import json
import logging

import httpx

from app.normalizer.models import NormalizedFinding
from app.config import get_settings

log = logging.getLogger(__name__)

_SEVERITY_MAP: dict[str, str] = {
    "critical": "critical",
    "high":     "high",
    "medium":   "medium",
    "low":      "low",
    "info":     "info",
    "unknown":  "info",
}

_TYPE_MAP: dict[str, str] = {
    "http":       "dast",
    "network":    "network_scan",
    "dns":        "network_scan",
    "file":       "sast",
    "ssl":        "network_scan",
    "websocket":  "dast",
    "code":       "sast",
    "javascript": "dast",
    "tcp":        "network_scan",
}

# Tags → security category
_TAG_CATEGORY: list[tuple[set[str], str]] = [
    ({"sqli", "sql-injection"},          "sql_injection"),
    ({"xss"},                            "xss"),
    ({"rce"},                            "remote_code_execution"),
    ({"lfi", "path-traversal"},          "path_traversal"),
    ({"ssrf"},                           "ssrf"),
    ({"xxe"},                            "xxe"),
    ({"idor"},                           "broken_access_control"),
    ({"auth-bypass", "authentication"},  "broken_authentication"),
    ({"exposure", "disclosure"},         "sensitive_data_exposure"),
    ({"misconfig", "misconfiguration"},  "security_misconfiguration"),
    ({"ssl", "tls"},                     "security_misconfiguration"),
    ({"tech", "detect"},                 "information_disclosure"),
    ({"cve"},                            "known_vulnerability"),
]


def _category_from_tags(tags: list[str], template_id: str) -> str:
    tag_set = {t.lower() for t in tags}
    tpl = template_id.lower()
    for keywords, category in _TAG_CATEGORY:
        if tag_set & keywords or any(k in tpl for k in keywords):
            return category
    return "security_misconfiguration"


def _normalize(results: list[dict], asset_id: str) -> list[NormalizedFinding]:
    findings: list[NormalizedFinding] = []
    for r in results:
        try:
            info           = r.get("info", {})
            classification = info.get("classification", {})
            tags: list[str] = info.get("tags", [])

            severity     = _SEVERITY_MAP.get(info.get("severity", "unknown"), "info")
            finding_type = _TYPE_MAP.get(r.get("type", ""), "dast")
            template_id  = r.get("template-id", "")
            matched_at   = r.get("matched-at") or r.get("host", "")

            # CWE — field can be string or list
            cwe = None
            cwe_raw = classification.get("cwe-id")
            if cwe_raw:
                val = cwe_raw if isinstance(cwe_raw, str) else (cwe_raw[0] if cwe_raw else None)
                if val and str(val).upper().startswith("CWE-"):
                    cwe = str(val).split("-")[1]

            cvss = classification.get("cvss-score")
            owasp_category = next((t for t in tags if t.lower().startswith("owasp")), None)

            evidence: dict = {"template_id": template_id, "matched_at": matched_at}
            cve_id = classification.get("cve-id")
            if cve_id:
                evidence["cve_id"] = cve_id
            if r.get("matcher-name"):
                evidence["matcher"] = r["matcher-name"]
            extracted = r.get("extracted-values")
            if extracted:
                evidence["extracted"] = extracted[:5]

            fingerprint = hashlib.sha256(
                json.dumps(["nuclei", template_id, matched_at], sort_keys=True).encode()
            ).hexdigest()

            confidence = 0.9 if severity in ("critical", "high") else 0.75 if severity == "medium" else 0.6
            effort     = "high" if severity in ("critical", "high") else "medium" if severity == "medium" else "low"

            findings.append(NormalizedFinding(
                scanner=           "nuclei",
                scanner_rule_id=   template_id or None,
                finding_type=      finding_type,
                category=          _category_from_tags(tags, template_id),
                cwe=               cwe,
                owasp_category=    owasp_category,
                cvss_score=        float(cvss) if cvss is not None else None,
                severity=          severity,
                title=             info.get("name") or template_id,
                description=       info.get("description") or None,
                remediation_guidance= info.get("remediation") or None,
                file_path=         None,
                line_start=        None,
                line_end=          None,
                component=         matched_at or None,
                effort=            effort,
                confidence=        confidence,
                evidence=          evidence,
                fingerprint=       fingerprint,
            ))
        except Exception as exc:
            log.warning("nuclei_normalize_error: %s | raw=%s", exc, r)

    return findings


class NucleiAdapter:
    def __init__(self, base_url: str):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=600.0)

    async def run_full_analysis_and_fetch(
        self,
        target: str,
        asset_id: str,
        severity: list[str] | None = None,
        templates: list[str] | None = None,
        custom_headers: list[str] | None = None,
    ) -> list[NormalizedFinding]:
        payload: dict = {
            "target":   target,
            "severity": severity or ["low", "medium", "high", "critical"],
            "timeout":  540,
        }
        if templates:
            payload["templates"] = templates
        if custom_headers:
            payload["custom_headers"] = custom_headers

        resp = await self._client.post("/scan", json=payload)
        resp.raise_for_status()
        return _normalize(resp.json().get("results", []), asset_id)


def get_nuclei_adapter() -> NucleiAdapter:
    return NucleiAdapter(base_url=get_settings().NUCLEI_URL)
