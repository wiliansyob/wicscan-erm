"""AiReviewAdapter — IA-escáner (F1), Etapa 1 estática.

Overrides run() entirely: reads local code snapshot → calls AI Gateway
/api/v1/scan/code → parses findings → returns normalized finding dicts.

No scanner-manager involved; _build_payload() is intentionally unreachable.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import ClassVar

import httpx
import structlog
import tempfile
import zipfile

from app.config import get_settings
from app.modules.identification.scanners.base import RawOutput, ScanRequest, ScannerAdapter
from app.modules.identification.scanners.ai_review.config import (
    AI_REVIEW_CONFIDENCE,
    AI_REVIEW_MAX_CHUNK_LINES,
    AI_REVIEW_OVERLAP_LINES,
    AI_REVIEW_PROMPT_VERSION,
    _MAX_FILE_BYTES,
    _SOURCE_EXTENSIONS,
)
from app.modules.identification.scanners.ai_review.prompts import (
    AI_REVIEW_SYSTEM_PROMPT,
    build_code_scan_prompt,
)

log = structlog.get_logger(__name__)

_SKIP_DIRS: frozenset[str] = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "env",
    "node_modules", "__pycache__", "vendor", "dist", "build",
    ".tox", ".mypy_cache", ".pytest_cache",
})

_VALID_SEVERITIES: frozenset[str] = frozenset({"critical", "high", "medium", "low", "info"})


class AiReviewAdapter(ScannerAdapter):
    """IA-escáner: local static analysis via LLM (F1 source)."""

    scanner_type: ClassVar[str] = "ai_review"

    # ── ABC requirement ───────────────────────────────────────────────────────

    def _build_payload(self, request: ScanRequest) -> dict:
        raise NotImplementedError("ai_review does not use scanner-manager; run() is overridden")

    # ── Main entry point ──────────────────────────────────────────────────────

    async def run(self, request: ScanRequest, scanner_manager_url: str) -> RawOutput:
        """Read code_path, call AI Gateway per file, return normalized findings."""
        if not request.code_path:
            log.warning("ai_review_no_code_path", scan_id=request.scan_id)
            return []

        settings = get_settings()
        files = self._collect_files(request.code_path)
        if not files:
            log.info("ai_review_no_files", scan_id=request.scan_id, code_path=request.code_path)
            return []

        all_findings: RawOutput = []

        ai_config = request.config.get("ai_config", {})
        providers_conf = ai_config.get("providers", {})
        
        # Determine the enabled provider
        active_provider = None
        selected_provider = request.config.get("ai_provider")
        
        if selected_provider and selected_provider in providers_conf and providers_conf[selected_provider].get("enabled"):
            active_provider = selected_provider
        else:
            # Fallback: first enabled provider
            for prov_name, prov_data in providers_conf.items():
                if prov_data.get("enabled"):
                    active_provider = prov_name
                    break
                
        provider_name = None
        api_key = None
        api_url = None
        model = None
        
        if active_provider:
            prov = providers_conf[active_provider]
            provider_name = active_provider
            api_key = prov.get("api_key")
            api_url = prov.get("url")
            model = prov.get("model")

        custom_scanner_prompt = ai_config.get("scanner_prompt", "").strip()
        system_prompt = custom_scanner_prompt if custom_scanner_prompt else AI_REVIEW_SYSTEM_PROMPT

        for rel_path, code in files:
            chunks = self._chunk_code(code, AI_REVIEW_MAX_CHUNK_LINES, AI_REVIEW_OVERLAP_LINES)
            for chunk_idx, chunk in enumerate(chunks):
                user_prompt = build_code_scan_prompt(rel_path, chunk)
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        resp = await client.post(
                            f"{settings.AI_GATEWAY_URL}/api/v1/scan/code",
                            json={
                                "file_path": rel_path,
                                "code_snippet": chunk,
                                "system_prompt_text": system_prompt,
                                "user_prompt_text": user_prompt,
                                "prompt_version": AI_REVIEW_PROMPT_VERSION,
                                "provider": provider_name,
                                "api_key": api_key,
                                "api_url": api_url,
                                "model": model,
                            },
                        )
                        resp.raise_for_status()
                        data = resp.json()
                except Exception as exc:
                    log.error(
                        "ai_review_chunk_failed",
                        file=rel_path,
                        chunk=chunk_idx,
                        error=repr(exc),
                    )
                    raise RuntimeError(f"AI Review failed on {rel_path} chunk {chunk_idx}: {repr(exc)}")

                for raw_finding in data.get("findings", []):
                    normalised = self._normalise_finding(raw_finding, rel_path)
                    if normalised is not None:
                        all_findings.append(normalised)

        log.info(
            "ai_review_completed",
            scan_id=request.scan_id,
            files_scanned=len(files),
            findings=len(all_findings),
        )
        return all_findings

    # ── Pure helpers (testable without DB / HTTP) ─────────────────────────────

    @staticmethod
    def _collect_files(code_path: str) -> list[tuple[str, str]]:
        """Return (relative_path, source_code) for every scannable file under code_path."""
        root = Path(code_path)
        if not root.exists():
            return []

        result: list[tuple[str, str]] = []
        
        # If it's a zip file, extract to a temporary directory
        temp_dir = None
        try:
            if root.is_file() and root.suffix.lower() == ".zip":
                temp_dir = tempfile.TemporaryDirectory()
                with zipfile.ZipFile(root, "r") as zip_ref:
                    zip_ref.extractall(temp_dir.name)
                root = Path(temp_dir.name)
            elif not root.is_dir():
                return []

            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                if any(part in _SKIP_DIRS or part.startswith(".") for part in path.parts):
                    continue
                if path.suffix.lower() not in _SOURCE_EXTENSIONS:
                    continue
                if path.stat().st_size > _MAX_FILE_BYTES:
                    continue
                try:
                    code = path.read_text(encoding="utf-8", errors="replace")
                    result.append((str(path.relative_to(root)), code))
                except OSError:
                    continue
        finally:
            if temp_dir:
                temp_dir.cleanup()

        return result

    @staticmethod
    def _chunk_code(code: str, max_lines: int, overlap: int = 50) -> list[str]:
        """Split code into overlapping chunks of at most max_lines lines."""
        lines = code.splitlines()
        if len(lines) <= max_lines:
            return [code]

        chunks: list[str] = []
        start = 0
        while start < len(lines):
            end = min(start + max_lines, len(lines))
            chunks.append("\n".join(lines[start:end]))
            if end >= len(lines):
                break
            start = end - overlap

        return chunks

    @staticmethod
    def _compute_fingerprint(file_path: str, rule_id: str, line: int | None) -> str:
        """Stable 19-char fingerprint for deduplication against SAST findings."""
        key = f"ai_review:{file_path}:{rule_id}:{line or 0}"
        return "ar-" + hashlib.sha256(key.encode()).hexdigest()[:16]

    @classmethod
    def _normalise_finding(cls, raw: dict, file_path: str) -> dict | None:
        """Map LLM JSON element → normalized finding dict expected by scan_tasks."""
        if not isinstance(raw, dict):
            return None

        severity = (raw.get("severity") or "medium").lower()
        if severity not in _VALID_SEVERITIES:
            severity = "medium"

        rule_id: str = (raw.get("rule_id") or raw.get("category") or "unknown").strip()

        line: int | None = None
        raw_line = raw.get("line")
        if raw_line is not None:
            try:
                line = int(raw_line)
            except (ValueError, TypeError):
                line = None

        return {
            "scanner": "ai_review",
            "scanner_rule_id": f"ai_review/{rule_id}",
            "finding_type": "vulnerability",
            "category": (raw.get("category") or rule_id).strip(),
            "cwe": raw.get("cwe"),
            "owasp_category": raw.get("owasp"),
            "severity": severity,
            "title": (raw.get("title") or rule_id).strip(),
            "description": raw.get("description"),
            "remediation_guidance": raw.get("remediation"),
            "file_path": file_path,
            "line_start": line,
            "confidence": AI_REVIEW_CONFIDENCE,
            "evidence": {
                "prompt_version": AI_REVIEW_PROMPT_VERSION,
                "snippet": (raw.get("snippet") or "")[:200],
            },
            "fingerprint": cls._compute_fingerprint(file_path, rule_id, line),
        }
