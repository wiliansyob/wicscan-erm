"""IA-escáner (F1) — static configuration.

These values are separate from the IA-redactor config (shared/ai_gateway)
so each role has its own prompt_version, confidence, and tuning knobs.
"""

AI_REVIEW_PROMPT_VERSION = "ai_review_v1"
AI_REVIEW_CONFIDENCE = 0.4          # low confidence: findings require human triage
AI_REVIEW_MAX_CHUNK_LINES = 300     # split large files into overlapping 300-line chunks
AI_REVIEW_OVERLAP_LINES = 50        # overlap between consecutive chunks

_SOURCE_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".go", ".php", ".rb", ".cs",
    ".cpp", ".c", ".cc", ".h", ".hpp",
    ".kt", ".swift", ".rs", ".scala",
})
_MAX_FILE_BYTES: int = 50_000       # skip files larger than 50 KB
