"""
Canonical normalized finding model.
Every scanner adapter must produce this structure.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NormalizedFinding:
    """Universal finding model — scanner-agnostic."""

    # Source
    scanner: str           # sonarqube | zap | trivy
    scanner_rule_id: str | None

    # Classification
    finding_type: str      # vulnerability | code_smell | bug | security_hotspot
    category: str          # sql_injection | xss | ... (lowercase snake_case)
    cwe: str | None        # CWE-89
    owasp_category: str | None  # A03:2021
    cvss_score: float | None

    # Severity (normalized)
    severity: str          # critical | high | medium | low | info

    # Content
    title: str
    description: str | None
    remediation_guidance: str | None

    # Location
    file_path: str | None
    line_start: int | None
    line_end: int | None
    component: str | None  # module/package path

    # Quality attributes
    effort: str | None     # low | medium | high
    confidence: float = 0.8

    # Evidence
    evidence: dict = field(default_factory=dict)

    # Deduplication fingerprint (sha256 of canonical fields)
    fingerprint: str | None = None

    def to_dict(self) -> dict:
        return {
            "scanner": self.scanner,
            "scanner_rule_id": self.scanner_rule_id,
            "finding_type": self.finding_type,
            "category": self.category,
            "cwe": self.cwe,
            "owasp_category": self.owasp_category,
            "cvss_score": self.cvss_score,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "remediation_guidance": self.remediation_guidance,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "component": self.component,
            "effort": self.effort,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "fingerprint": self.fingerprint,
        }
