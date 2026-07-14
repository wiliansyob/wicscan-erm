"""
Normalization pipeline — takes raw scanner output, produces NormalizedFinding[].

Each adapter calls pipeline.normalize(raw_findings, scanner_name).
The pipeline applies:
  1. Field mapping (severity, type, etc.)
  2. CWE/OWASP enrichment
  3. Category resolution
  4. Fingerprint generation
"""

from __future__ import annotations

import hashlib
import json

import structlog

from app.normalizer.mappings import (
    CWE_CATEGORY_MAP,
    SONARQUBE_RULE_CWE_MAP,
    SONARQUBE_RULE_OWASP_MAP,
    SONARQUBE_SEVERITY_MAP,
    SONARQUBE_TYPE_MAP,
    normalize_effort,
)
from app.normalizer.models import NormalizedFinding

log = structlog.get_logger(__name__)


def _make_fingerprint(scanner: str, rule_id: str | None, file_path: str | None, line: int | None, title: str) -> str:
    canonical = json.dumps(
        {
            "scanner": scanner,
            "rule": rule_id or "",
            "file": file_path or "",
            "line": line or 0,
            "title": title[:100],
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _resolve_category(cwe: str | None, rule_id: str | None, title: str) -> str:
    if cwe and cwe in CWE_CATEGORY_MAP:
        return CWE_CATEGORY_MAP[cwe]
    if rule_id:
        cwe_from_rule = SONARQUBE_RULE_CWE_MAP.get(rule_id)
        if cwe_from_rule and cwe_from_rule in CWE_CATEGORY_MAP:
            return CWE_CATEGORY_MAP[cwe_from_rule]
    # Heuristic from title keywords
    title_lower = title.lower()
    # Accessibility keywords — UX issues, NOT security
    accessibility_keywords = [
        "keyboard listener", "keyboard event", "aria-", "aria ",
        "accessible", "accessibility", "a11y", "screen reader",
        "interactive element", "non-interactive", "click handler",
        "focus", "tabindex", "alt text", "alt attribute",
        "heading order", "label element",
    ]
    for kw in accessibility_keywords:
        if kw in title_lower:
            return "accessibility"

    # Code quality keywords — technical debt, NOT security issues
    quality_keywords = [
        "cognitive complexity", "complexity", "refactor", "duplicate",
        "redundant", "unused", "naming", "formatting", "comment",
        "nesting", "nest function", "compare function", "alphabetically",
        "await on a non-promise", "code smell",
    ]
    for kw in quality_keywords:
        if kw in title_lower:
            return "code_quality"

    keyword_map = {
        # Comunicación insegura
        "http protocol": "insecure_transport",
        "using http": "insecure_transport",
        "insecure. use https": "insecure_transport",
        # Seguridad de contenedores / Dockerfile
        "dockerfile": "container_security",
        "ignore-scripts": "container_security",
        "copying recursively": "container_security",
        "copying using a glob": "container_security",
        "write permissions": "container_security",
        "sensitive data to the container": "container_security",
        # Vulnerabilidades de aplicación
        "sql injection": "sql_injection",
        "sql": "sql_injection",
        "xss": "xss",
        "cross-site scripting": "xss",
        "command injection": "command_injection",
        "path traversal": "path_traversal",
        "xxe": "xxe",
        "ssrf": "ssrf",
        "authentication": "broken_auth",
        "authorization": "broken_access_control",
        "hardcoded": "hardcoded_credentials",
        "password": "hardcoded_credentials",
        "secret": "hardcoded_credentials",
        "crypto": "weak_crypto",
        "encryption": "weak_crypto",
        "hash": "weak_crypto",
        "random": "insecure_random",
        "deserialization": "insecure_deserialization",
        "csrf": "csrf",
        "redirect": "open_redirect",
        "injection": "injection",
    }
    for keyword, category in keyword_map.items():
        if keyword in title_lower:
            return category
    return "security_misconfiguration"


class NormalizationPipeline:
    def normalize_sonarqube_issues(self, issues: list[dict], asset_id: str) -> list[NormalizedFinding]:
        normalized: list[NormalizedFinding] = []

        for issue in issues:
            try:
                rule_id = issue.get("rule", "")
                raw_severity = issue.get("severity", "MINOR")
                raw_type = issue.get("type", "BUG")

                severity = SONARQUBE_SEVERITY_MAP.get(raw_severity, "info")
                finding_type = SONARQUBE_TYPE_MAP.get(raw_type, "bug")

                # CWE resolution: from tags > rule map
                cwe: str | None = None
                tags = issue.get("tags", [])
                for tag in tags:
                    if tag.upper().startswith("CWE-"):
                        cwe = tag.upper()
                        break
                if not cwe:
                    cwe = SONARQUBE_RULE_CWE_MAP.get(rule_id)

                owasp = SONARQUBE_RULE_OWASP_MAP.get(rule_id)

                title = issue.get("message", f"Finding: {rule_id}")
                file_path = issue.get("component", "")
                # Strip project prefix: "project:src/file.py" -> "src/file.py"
                if ":" in file_path:
                    file_path = file_path.split(":", 1)[1]

                text_range = issue.get("textRange", {})
                line_start = text_range.get("startLine") or issue.get("line")
                line_end = text_range.get("endLine")

                effort = normalize_effort(issue.get("effort") or issue.get("debt"))
                category = _resolve_category(cwe, rule_id, title)

                # Descartar hallazgos que no son riesgos de seguridad
                if category in ("code_quality", "accessibility"):
                    continue

                # Confidence based on type and severity
                confidence = 0.9 if finding_type == "vulnerability" else 0.75
                if severity == "info":
                    confidence = 0.5

                fingerprint = _make_fingerprint("sonarqube", rule_id, file_path, line_start, title)

                evidence = {
                    "sonarqube_key": issue.get("key"),
                    "rule_id": rule_id,
                    "tags": tags,
                    "flows": issue.get("flows", [])[:3],  # Limit evidence size
                }

                nf = NormalizedFinding(
                    scanner="sonarqube",
                    scanner_rule_id=rule_id,
                    finding_type=finding_type,
                    category=category,
                    cwe=cwe,
                    owasp_category=owasp,
                    cvss_score=None,
                    severity=severity,
                    title=title,
                    description=issue.get("message"),
                    remediation_guidance=None,
                    file_path=file_path or None,
                    line_start=line_start,
                    line_end=line_end,
                    component=issue.get("component"),
                    effort=effort,
                    confidence=confidence,
                    evidence=evidence,
                    fingerprint=fingerprint,
                )
                normalized.append(nf)

            except Exception as exc:
                log.warning("normalization_failed", rule=issue.get("rule"), error=str(exc))
                continue

        log.info("normalization_complete", input=len(issues), output=len(normalized))
        return normalized


pipeline = NormalizationPipeline()
