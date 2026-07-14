from __future__ import annotations

import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.providers.base import BaseProvider, LLMResponse

log = structlog.get_logger(__name__)


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str | None = None):
        if base_url:
            self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> LLMResponse:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            provider=self.name,
            tokens_used=response.usage.total_tokens if response.usage else None,
            finish_reason=choice.finish_reason,
        )

    async def is_available(self) -> bool:
        try:
            models = await self._client.models.list()
            return len(models.data) > 0
        except Exception:
            return False
