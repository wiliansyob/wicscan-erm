"""
Nuclei scanner adapter.

Facade over the scanner-manager HTTP API for Nuclei analysis.
Nuclei only needs a target (target_url or ip_address).
"""
from __future__ import annotations

from app.modules.identification.scanners.base import ScannerAdapter, ScanRequest


class NucleiAdapter(ScannerAdapter):
    scanner_type = "nuclei"

    def _build_payload(self, request: ScanRequest) -> dict:
        return {
            "scan_id": request.scan_id,
            "scanner_type": self.scanner_type,
            "asset_id": request.asset_id,
            "target_url": request.target_url,
            "url": request.target_url,
            "ip_address": request.ip_address,
            "scanner_url": request.scanner_url,
            "scanner_api_key": request.scanner_api_key,
            "config": request.config,
            "severity": request.config.get("severity", ["info", "low", "medium", "high", "critical"]),
            "templates": request.config.get("templates"),
        }
