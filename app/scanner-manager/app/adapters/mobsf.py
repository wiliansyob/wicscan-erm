import httpx
import structlog
from app.config import get_settings
from app.normalizer.models import NormalizedFinding

log = structlog.get_logger(__name__)

class MobSFAdapter:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        settings = get_settings()
        self.base_url = base_url or settings.MOBSF_URL
        self.token = token or settings.MOBSF_API_KEY
        self.headers = {"Authorization": self.token}

    async def upload_file(self, file_path: str) -> str:
        url = f"{self.base_url}/api/v1/upload"
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(file_path, "rb") as f:
                files = {"file": f}
                resp = await client.post(url, headers=self.headers, files=files)
            resp.raise_for_status()
            data = resp.json()
            return data.get("hash")

    async def scan(self, scan_hash: str, scan_type: str = "apk") -> dict:
        url = f"{self.base_url}/api/v1/scan"
        data = {"hash": scan_hash, "scan_type": scan_type}
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(url, headers=self.headers, data=data)
            resp.raise_for_status()
            
            # API might return a report directly, or we might need to fetch it via /api/v1/report/json
            report_url = f"{self.base_url}/api/v1/report/json"
            report_resp = await client.post(report_url, headers=self.headers, data={"hash": scan_hash})
            if report_resp.status_code == 200:
                return report_resp.json()
            return resp.json()

    def get_findings(self, report: dict) -> list[NormalizedFinding]:
        findings = []
        
        def map_severity(mobsf_severity: str) -> str:
            mobsf_severity = str(mobsf_severity).lower()
            if mobsf_severity in ("high", "critical", "error"):
                return "high"
            if mobsf_severity in ("warning", "medium"):
                return "medium"
            if mobsf_severity in ("info", "low"):
                return "low"
            return "info"
            
        # Manifest Analysis
        manifest_issues = report.get("manifest_analysis", [])
        if isinstance(manifest_issues, dict):
            # Sometimes it's a dict depending on MobSF version
            manifest_issues = manifest_issues.get("manifest_findings", [])
            
        if isinstance(manifest_issues, list):
            for issue in manifest_issues:
                findings.append(NormalizedFinding(
                    scanner="mobsf",
                    scanner_rule_id=issue.get("rule_id") or issue.get("id"),
                    finding_type="vulnerability",
                    category="manifest",
                    cwe=None,
                    owasp_category=None,
                    cvss_score=None,
                    severity=map_severity(issue.get("severity", "info")),
                    title=issue.get("title") or issue.get("name", "Manifest Finding"),
                    description=issue.get("description") or issue.get("desc", ""),
                    remediation_guidance=None,
                    file_path="AndroidManifest.xml",
                    line_start=None,
                    line_end=None,
                    component="manifest",
                    effort="low",
                    evidence={"raw": issue}
                ))

        # Code Analysis
        code_analysis = report.get("code_analysis", {})
        if isinstance(code_analysis, dict):
            # MobSF v3.4+ nests issues under "findings"
            code_analysis_issues = code_analysis.get("findings", code_analysis) if isinstance(code_analysis, dict) else code_analysis
            
            # Format: {"issue_name": {"metadata": {...}, "files": {...}}}
            for issue_name, issue_data in code_analysis_issues.items():
                if not isinstance(issue_data, dict):
                    continue
                metadata = issue_data.get("metadata", {})
                severity = map_severity(metadata.get("severity", "info"))
                desc = metadata.get("description", "")
                cwe = str(metadata.get("cwe", ""))[:50] if metadata.get("cwe") else ""
                owasp = str(metadata.get("owasp", ""))[:100] if metadata.get("owasp") else ""
                
                for file_path, lines in issue_data.get("files", {}).items():
                    findings.append(NormalizedFinding(
                        scanner="mobsf",
                        scanner_rule_id=issue_name,
                        finding_type="vulnerability",
                        category="code_analysis",
                        cwe=cwe,
                        owasp_category=owasp,
                        cvss_score=None,
                        severity=severity,
                        title=issue_name,
                        description=desc,
                        remediation_guidance=metadata.get("ref", ""),
                        file_path=file_path,
                        line_start=None,
                        line_end=None,
                        component="code",
                        effort="low",
                        evidence={"lines": lines}
                    ))

        return findings

def get_mobsf_adapter(url: str | None = None, api_key: str | None = None) -> MobSFAdapter:
    return MobSFAdapter(base_url=url, token=api_key)
