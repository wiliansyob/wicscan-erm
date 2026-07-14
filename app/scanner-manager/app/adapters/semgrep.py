import json
import asyncio
import structlog
from app.normalizer.models import NormalizedFinding

log = structlog.get_logger(__name__)

class SemgrepAdapter:
    async def scan(self, code_path: str) -> list[NormalizedFinding]:
        log.info("semgrep_scan_started", path=code_path)
        
        # Run semgrep via subprocess
        cmd = [
            "semgrep",
            "scan",
            "--json",
            "--config=p/default",
            "--config=p/security-audit",
            "--config=p/owasp-top-ten",
            code_path
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Semgrep exits with 0 if no findings, 1 if findings, >1 if error.
            # So we check if output is valid JSON instead of relying purely on returncode.
            if not stdout:
                log.error("semgrep_scan_failed", error=stderr.decode()[:500])
                raise RuntimeError("Semgrep scan failed or returned no output")
                
            try:
                report = json.loads(stdout)
            except json.JSONDecodeError:
                log.error("semgrep_json_parse_failed", error=stdout.decode()[:500])
                raise RuntimeError("Failed to parse Semgrep JSON output")
                
            return self.get_findings(report)
            
        except Exception as e:
            log.exception("semgrep_execution_error", error=str(e))
            raise

    def get_findings(self, report: dict) -> list[NormalizedFinding]:
        findings = []
        
        results = report.get("results", [])
        for issue in results:
            extra = issue.get("extra", {})
            metadata = extra.get("metadata", {})
            
            # Map severity
            semgrep_severity = extra.get("severity", "INFO").upper()
            if semgrep_severity == "ERROR":
                severity = "high"
            elif semgrep_severity == "WARNING":
                severity = "medium"
            else:
                severity = "low"
                
            # Extract CWE / OWASP if available in metadata
            cwe = ""
            owasp = ""
            if "cwe" in metadata:
                cwe_data = metadata["cwe"]
                if isinstance(cwe_data, list) and len(cwe_data) > 0:
                    cwe = str(cwe_data[0])
                else:
                    cwe = str(cwe_data)
            
            if "owasp" in metadata:
                owasp_data = metadata["owasp"]
                if isinstance(owasp_data, list) and len(owasp_data) > 0:
                    owasp = str(owasp_data[0])
                else:
                    owasp = str(owasp_data)
                    
            cwe = cwe[:50]
            owasp = owasp[:100]
            
            findings.append(NormalizedFinding(
                scanner="semgrep",
                scanner_rule_id=issue.get("check_id", "unknown"),
                finding_type="vulnerability",
                category="code_analysis",
                cwe=cwe,
                owasp_category=owasp,
                cvss_score=None,
                severity=severity,
                title=metadata.get("shortlink", issue.get("check_id")),
                description=extra.get("message", ""),
                remediation_guidance=None,
                file_path=issue.get("path", ""),
                line_start=issue.get("start", {}).get("line"),
                line_end=issue.get("end", {}).get("line"),
                component="code",
                effort="low",
                evidence={"lines": extra.get("lines", "")[:500]}
            ))
            
        return findings

def get_semgrep_adapter() -> SemgrepAdapter:
    return SemgrepAdapter()
