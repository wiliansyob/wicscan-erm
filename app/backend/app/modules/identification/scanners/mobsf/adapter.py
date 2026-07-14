"""
MobSF scanner adapter.
"""
from __future__ import annotations

from app.modules.identification.scanners.base import ScannerAdapter, ScanRequest

class MobSFAdapter(ScannerAdapter):
    scanner_type = "mobsf"

    def _build_payload(self, request: ScanRequest) -> dict:
        config = request.config or {}
        scan_type = config.get("scan_type", "apk")
        
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
            "mobsf_scan_type": scan_type,
            "ip_address": request.ip_address,
        }
