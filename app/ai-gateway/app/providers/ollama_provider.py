from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.providers.base import BaseProvider, LLMResponse

log = structlog.get_logger(__name__)


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://ollama:11434", model: str = "llama3.2"):
        self._base_url = base_url.rstrip("/")
        self._model = model

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=10))
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "format": "json",
        }

        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("message", {}).get("content", "")
        tokens = data.get("eval_count")

        return LLMResponse(
            content=content,
            model=self._model,
            provider=self.name,
            tokens_used=tokens,
            finish_reason=data.get("done_reason"),
        )

    async def ensure_model_pulled(self) -> None:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/pull",
                json={"name": self._model, "stream": False},
            )
            if resp.status_code not in (200, 201):
                log.warning("ollama_pull_failed", model=self._model, status=resp.status_code)

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
