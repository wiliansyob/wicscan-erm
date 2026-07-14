"""
Risk Engine — ISO 31000 + OWASP Risk Rating Methodology

Implements the full risk lifecycle:
  1. Risk Identification (from findings)
  2. Risk Analysis (Likelihood × Impact using OWASP RRM)
  3. Risk Evaluation (against risk appetite)
  4. Treatment generation
  5. Residual risk calculation
"""

from __future__ import annotations

import hashlib
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

import structlog

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RiskAppetite(str, Enum):
    LOW = "low"        # Accept only LOW risks
    MEDIUM = "medium"  # Accept up to MEDIUM risks
    HIGH = "high"      # Accept up to HIGH risks


class TreatmentType(str, Enum):
    MITIGATE = "mitigate"
    AVOID = "avoid"
    TRANSFER = "transfer"
    ACCEPT = "accept"


class TreatmentPriority(str, Enum):
    IMMEDIATE = "immediate"      # < 7 days
    SHORT_TERM = "short_term"    # < 30 days
    MEDIUM_TERM = "medium_term"  # < 90 days
    LONG_TERM = "long_term"      # > 90 days


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class OWASPThreatFactors:
    """OWASP RRM Threat Agent factors (1-9 scale each)."""
    skill_level: float       # 1=No technical skills, 9=Security penetration skills
    motive: float            # 1=Low reward, 9=High reward
    opportunity: float       # 1=Full access required, 9=No access required
    population_size: float   # 1=Developer, 9=Unauthenticated users

    def average(self) -> float:
        return (self.skill_level + self.motive + self.opportunity + self.population_size) / 4


@dataclass
class OWASPVulnFactors:
    """OWASP RRM Vulnerability factors (1-9 scale each)."""
    ease_of_discovery: float  # 1=Practically impossible, 9=Automated tools available
    ease_of_exploit: float    # 1=Theoretical, 9=Automated tools available
    awareness: float          # 1=Unknown, 9=Publicly known
    ids_detection: float      # 1=Active detection, 9=Not logged

    def average(self) -> float:
        return (self.ease_of_discovery + self.ease_of_exploit + self.awareness + self.ids_detection) / 4


@dataclass
class OWASPTechnicalImpact:
    """OWASP RRM Technical Impact factors (1-9 scale each)."""
    confidentiality: float   # Loss of confidentiality
    integrity: float         # Loss of integrity
    availability: float      # Loss of availability
    accountability: float    # Loss of accountability

    def average(self) -> float:
        return (self.confidentiality + self.integrity + self.availability + self.accountability) / 4


@dataclass
class OWASPBusinessImpact:
    """OWASP RRM Business Impact factors (1-9 scale each)."""
    financial: float    # Financial damage
    reputation: float   # Reputation damage
    legal: float        # Legal/compliance exposure
    privacy: float      # Privacy violation

    def average(self) -> float:
        return (self.financial + self.reputation + self.legal + self.privacy) / 4


@dataclass
class FindingContext:
    """Normalized finding ready for risk analysis."""
    finding_id: str
    asset_id: str
    scanner: str
    category: str
    cwe: str | None
    owasp_category: str | None
    severity: str
    title: str
    description: str
    confidence: float
    asset_criticality: str
    asset_type: str
    data_classification: str
    business_context: str | None
    existing_controls: list[str]
    is_internet_facing: bool


@dataclass
class RiskAnalysisResult:
    """Complete risk analysis output."""
    finding_id: str
    asset_id: str
    project_id: str
    risk_title: str
    risk_description: str

    # OWASP RRM factors
    threat_factors: OWASPThreatFactors
    vuln_factors: OWASPVulnFactors
    technical_impact: OWASPTechnicalImpact
    business_impact: OWASPBusinessImpact

    # Composite scores
    likelihood_score: float
    impact_score: float
    risk_score: float
    risk_level: RiskLevel

    # CIA triad
    affected_cia: list[str]
    business_impact_desc: str

    # Recommended treatment
    recommended_treatment: TreatmentType
    treatment_priority: TreatmentPriority
    technical_actions: list[str]

    # Metadata
    methodology: str = "owasp_rrm"
    assessed_by: str = "engine"


# ─────────────────────────────────────────────────────────────────────────────
# Severity → OWASP factor mappings
# ─────────────────────────────────────────────────────────────────────────────

_SEVERITY_THREAT_MAP: dict[str, OWASPThreatFactors] = {
    "critical": OWASPThreatFactors(skill_level=6, motive=7, opportunity=7, population_size=6),
    "high":     OWASPThreatFactors(skill_level=5, motive=6, opportunity=5, population_size=5),
    "medium":   OWASPThreatFactors(skill_level=4, motive=4, opportunity=4, population_size=4),
    "low":      OWASPThreatFactors(skill_level=2, motive=2, opportunity=3, population_size=3),
    "info":     OWASPThreatFactors(skill_level=1, motive=1, opportunity=2, population_size=2),
}

_SEVERITY_VULN_MAP: dict[str, OWASPVulnFactors] = {
    "critical": OWASPVulnFactors(ease_of_discovery=8, ease_of_exploit=8, awareness=7, ids_detection=7),
    "high":     OWASPVulnFactors(ease_of_discovery=6, ease_of_exploit=6, awareness=6, ids_detection=6),
    "medium":   OWASPVulnFactors(ease_of_discovery=4, ease_of_exploit=4, awareness=5, ids_detection=5),
    "low":      OWASPVulnFactors(ease_of_discovery=2, ease_of_exploit=2, awareness=3, ids_detection=4),
    "info":     OWASPVulnFactors(ease_of_discovery=1, ease_of_exploit=1, awareness=2, ids_detection=3),
}

_CRITICALITY_IMPACT_MAP: dict[str, dict[str, float]] = {
    "critical": {"confidentiality": 8, "integrity": 7, "availability": 8, "accountability": 7,
                 "financial": 8, "reputation": 8, "legal": 7, "privacy": 8},
    "high":     {"confidentiality": 6, "integrity": 6, "availability": 6, "accountability": 5,
                 "financial": 6, "reputation": 6, "legal": 5, "privacy": 6},
    "medium":   {"confidentiality": 4, "integrity": 4, "availability": 4, "accountability": 3,
                 "financial": 4, "reputation": 4, "legal": 3, "privacy": 4},
    "low":      {"confidentiality": 2, "integrity": 2, "availability": 2, "accountability": 2,
                 "financial": 2, "reputation": 2, "legal": 2, "privacy": 2},
}

_CIA_BY_CATEGORY: dict[str, list[str]] = {
    "sql_injection":          ["C", "I"],
    "xss":                    ["C", "I"],
    "command_injection":      ["C", "I", "A"],
    "path_traversal":         ["C"],
    "xxe":                    ["C", "A"],
    "ssrf":                   ["C", "I"],
    "broken_auth":            ["C", "I"],
    "sensitive_data":         ["C"],
    "security_misconfiguration": ["C", "I", "A"],
    "insecure_deserialization": ["C", "I", "A"],
    "hardcoded_credentials":  ["C"],
    "insecure_random":        ["C"],
    "weak_crypto":            ["C", "I"],
    "csrf":                   ["I"],
    "open_redirect":          ["C"],
    "default": ["C", "I"],
}

_TREATMENT_BY_LEVEL: dict[RiskLevel, TreatmentType] = {
    RiskLevel.CRITICAL: TreatmentType.MITIGATE,
    RiskLevel.HIGH:     TreatmentType.MITIGATE,
    RiskLevel.MEDIUM:   TreatmentType.MITIGATE,
    RiskLevel.LOW:      TreatmentType.ACCEPT,
    RiskLevel.INFO:     TreatmentType.ACCEPT,
}

_PRIORITY_BY_LEVEL: dict[RiskLevel, TreatmentPriority] = {
    RiskLevel.CRITICAL: TreatmentPriority.IMMEDIATE,
    RiskLevel.HIGH:     TreatmentPriority.SHORT_TERM,
    RiskLevel.MEDIUM:   TreatmentPriority.MEDIUM_TERM,
    RiskLevel.LOW:      TreatmentPriority.LONG_TERM,
    RiskLevel.INFO:     TreatmentPriority.LONG_TERM,
}


# ─────────────────────────────────────────────────────────────────────────────
# Risk scoring helpers
# ─────────────────────────────────────────────────────────────────────────────


def _score_to_level(score: float) -> RiskLevel:
    """Map OWASP RRM score (0-9) to risk level."""
    if score >= 7:
        return RiskLevel.CRITICAL
    if score >= 5:
        return RiskLevel.HIGH
    if score >= 3:
        return RiskLevel.MEDIUM
    if score >= 1:
        return RiskLevel.LOW
    return RiskLevel.INFO


def _apply_exposure_modifier(base_score: float, is_internet_facing: bool, data_class: str) -> float:
    """Adjust score based on exposure and data sensitivity."""
    modifier = 1.0
    if is_internet_facing:
        modifier += 0.15
    if data_class in ("confidential", "restricted"):
        modifier += 0.10
    return min(9.0, base_score * modifier)


def _apply_control_modifier(base_score: float, existing_controls: list[str]) -> float:
    """Reduce score for each meaningful compensating control."""
    reductions = {
        "waf": 0.05,
        "input_validation": 0.08,
        "parameterized_queries": 0.12,
        "content_security_policy": 0.05,
        "mfa": 0.10,
        "encryption_at_rest": 0.07,
        "network_segmentation": 0.06,
        "ids_ips": 0.05,
        "sast": 0.03,
        "dast": 0.03,
    }
    total_reduction = sum(reductions.get(c.lower().replace(" ", "_"), 0.0) for c in existing_controls)
    return max(0.1, base_score * (1.0 - min(0.5, total_reduction)))


# ─────────────────────────────────────────────────────────────────────────────
# Core Risk Engine
# ─────────────────────────────────────────────────────────────────────────────


class RiskEngine:
    """
    Implements OWASP Risk Rating Methodology for automated risk scoring.

    Score = Likelihood × Impact / 9  (normalized to 0-9)
    Likelihood = (ThreatAgent + Vulnerability) / 2
    Impact = (TechnicalImpact + BusinessImpact) / 2
    """

    def analyze(self, ctx: FindingContext, project_id: str) -> RiskAnalysisResult:
        severity = ctx.severity.lower()

        threat = _SEVERITY_THREAT_MAP.get(severity, _SEVERITY_THREAT_MAP["medium"])
        vuln = _SEVERITY_VULN_MAP.get(severity, _SEVERITY_VULN_MAP["medium"])
        criticality = ctx.asset_criticality.lower()
        impact_vals = _CRITICALITY_IMPACT_MAP.get(criticality, _CRITICALITY_IMPACT_MAP["medium"])

        tech_impact = OWASPTechnicalImpact(
            confidentiality=impact_vals["confidentiality"],
            integrity=impact_vals["integrity"],
            availability=impact_vals["availability"],
            accountability=impact_vals["accountability"],
        )
        biz_impact = OWASPBusinessImpact(
            financial=impact_vals["financial"],
            reputation=impact_vals["reputation"],
            legal=impact_vals["legal"],
            privacy=impact_vals["privacy"],
        )

        raw_likelihood = (threat.average() + vuln.average()) / 2
        raw_impact = (tech_impact.average() + biz_impact.average()) / 2

        likelihood = _apply_exposure_modifier(raw_likelihood, ctx.is_internet_facing, ctx.data_classification)
        likelihood = _apply_control_modifier(likelihood, ctx.existing_controls)
        impact = _apply_exposure_modifier(raw_impact, ctx.is_internet_facing, ctx.data_classification)

        risk_score = (likelihood * impact) / 9
        risk_level = _score_to_level(risk_score)

        cat_key = ctx.category.lower().replace("-", "_").replace(" ", "_")
        affected_cia = _CIA_BY_CATEGORY.get(cat_key, _CIA_BY_CATEGORY["default"])

        treatment = _TREATMENT_BY_LEVEL[risk_level]
        priority = _PRIORITY_BY_LEVEL[risk_level]

        if risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH) and ctx.asset_criticality == "low":
            treatment = TreatmentType.MITIGATE
            priority = TreatmentPriority.MEDIUM_TERM

        log.info(
            "risk_analyzed",
            finding_id=ctx.finding_id,
            severity=severity,
            likelihood=round(likelihood, 2),
            impact=round(impact, 2),
            risk_score=round(risk_score, 2),
            risk_level=risk_level.value,
        )

        return RiskAnalysisResult(
            finding_id=ctx.finding_id,
            asset_id=ctx.asset_id,
            project_id=project_id,
            risk_title=f"{ctx.category.replace('_', ' ').title()} in {ctx.title[:80]}",
            risk_description=ctx.description or f"Risk identified by {ctx.scanner}: {ctx.title}",
            threat_factors=threat,
            vuln_factors=vuln,
            technical_impact=tech_impact,
            business_impact=biz_impact,
            likelihood_score=round(likelihood, 2),
            impact_score=round(impact, 2),
            risk_score=round(risk_score, 2),
            risk_level=risk_level,
            affected_cia=affected_cia,
            business_impact_desc=self._describe_business_impact(ctx, risk_level, biz_impact),
            recommended_treatment=treatment,
            treatment_priority=priority,
            technical_actions=self._suggest_actions(ctx),
        )

    def _describe_business_impact(
        self, ctx: FindingContext, level: RiskLevel, biz: OWASPBusinessImpact
    ) -> str:
        parts = []
        if biz.financial >= 6:
            parts.append("potential financial loss")
        if biz.reputation >= 6:
            parts.append("reputational damage")
        if biz.legal >= 6:
            parts.append("regulatory/legal exposure")
        if biz.privacy >= 6:
            parts.append("privacy breach risk")
        if ctx.data_classification in ("confidential", "restricted"):
            parts.append(f"exposure of {ctx.data_classification} data")
        if not parts:
            return f"Operational risk to {ctx.asset_type} asset"
        return f"{level.value.title()} risk: " + ", ".join(parts) + f" in {ctx.asset_type} asset."

    def _suggest_actions(self, ctx: FindingContext) -> list[str]:
        actions_map: dict[str, list[str]] = {
            "sql_injection": [
                "Replace string concatenation with parameterized queries",
                "Use ORM layer for all database interactions",
                "Add input validation and sanitization",
                "Enable database activity monitoring (DAM)",
            ],
            "xss": [
                "Apply output encoding for all user-supplied data",
                "Implement Content Security Policy (CSP) headers",
                "Use framework-native templating engines with auto-escaping",
                "Add X-XSS-Protection and X-Content-Type-Options headers",
            ],
            "broken_auth": [
                "Implement multi-factor authentication (MFA)",
                "Enforce strong password policies",
                "Use short-lived JWT tokens with refresh token rotation",
                "Implement account lockout after failed attempts",
            ],
            "hardcoded_credentials": [
                "Move secrets to a secrets manager (Vault, AWS Secrets Manager)",
                "Rotate all exposed credentials immediately",
                "Implement secret scanning in CI/CD pipeline",
                "Use environment variables with proper access controls",
            ],
            "security_misconfiguration": [
                "Review and harden security headers",
                "Disable debug mode in production",
                "Remove default credentials and example configurations",
                "Implement automated configuration scanning",
            ],
            "weak_crypto": [
                "Upgrade to AES-256 or ChaCha20-Poly1305 for symmetric encryption",
                "Use RSA-4096 or ECC P-384 for asymmetric operations",
                "Replace MD5/SHA-1 with SHA-256 or SHA-3 for hashing",
                "Use bcrypt/Argon2 for password hashing",
            ],
        }
        cat_key = ctx.category.lower().replace("-", "_").replace(" ", "_")
        default = [
            f"Review and remediate {ctx.category} vulnerability",
            "Apply vendor security patches",
            "Conduct security code review for affected module",
            "Add security test coverage for this vulnerability class",
        ]
        return actions_map.get(cat_key, default)

    def calculate_residual_risk(
        self, original_score: float, treatment_type: TreatmentType, actions_count: int
    ) -> tuple[float, RiskLevel]:
        reductions = {
            TreatmentType.MITIGATE: 0.6,
            TreatmentType.AVOID: 0.9,
            TreatmentType.TRANSFER: 0.4,
            TreatmentType.ACCEPT: 0.0,
        }
        base_reduction = reductions[treatment_type]
        action_bonus = min(0.1, actions_count * 0.02)
        total_reduction = base_reduction + action_bonus
        residual = round(original_score * (1.0 - total_reduction), 2)
        return residual, _score_to_level(residual)

    def build_matrix_data(self, risk_assessments: list[dict]) -> dict:
        """Build 5×5 risk matrix data for heatmap rendering."""
        matrix = [[0] * 5 for _ in range(5)]
        risk_positions: list[dict] = []

        for ra in risk_assessments:
            l_idx = min(4, max(0, int(ra["likelihood_score"] / 9 * 4)))
            i_idx = min(4, max(0, int(ra["impact_score"] / 9 * 4)))
            matrix[4 - l_idx][i_idx] += 1
            risk_positions.append({
                "id": ra["id"],
                "title": ra["risk_title"],
                "level": ra["risk_level"],
                "likelihood_idx": l_idx,
                "impact_idx": i_idx,
                "asset_name": ra.get("asset_name", ""),
            })

        level_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for ra in risk_assessments:
            level = ra.get("risk_level", "info")
            level_counts[level] = level_counts.get(level, 0) + 1

        return {
            "matrix": matrix,
            "risks": risk_positions,
            "summary": {
                **level_counts,
                "total": len(risk_assessments),
            },
        }


def apply_coverage_bonus(probability: int, finding_count: int) -> int:
    """Ajusta la probabilidad según la cantidad de hallazgos que respaldan el riesgo.

    ISO 31000: más evidencia del mismo vector = mayor probabilidad de explotación.
    - 1 hallazgo:    sin bonus
    - 2-4 hallazgos: +1 (mayor superficie de ataque confirmada)
    - 5+ hallazgos:  +2 (problema sistémico)
    Máximo: 5.
    """
    if finding_count <= 1:
        return probability
    bonus = 1 if finding_count <= 4 else 2
    return min(5, probability + bonus)


# Singleton
risk_engine = RiskEngine()
