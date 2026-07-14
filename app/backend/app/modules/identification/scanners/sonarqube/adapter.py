"""
SonarQube scanner adapter.

Facade over the scanner-manager HTTP API for SAST analysis.
The scanner-manager owns the sonar-scanner CLI execution and normalisation;
this adapter only builds the request payload and delegates.
"""
from __future__ import annotations

from app.modules.identification.scanners.base import ScannerAdapter, ScanRequest


class SonarQubeAdapter(ScannerAdapter):
    scanner_type = "sonarqube"

    def _build_payload(self, request: ScanRequest) -> dict:
        return {
            "scan_id": request.scan_id,
            "scanner_type": self.scanner_type,
            "project_key": request.project_key,
            "project_name": request.project_name,
            "asset_id": request.asset_id,
            "code_path": request.code_path,
            "target_url": request.target_url,
            "github_url": request.github_url,
            "github_branch": request.github_branch,
            "github_token": request.github_token,
            "scanner_url": request.scanner_url,
            "scanner_api_key": request.scanner_api_key,
            "config": request.config,
        }
