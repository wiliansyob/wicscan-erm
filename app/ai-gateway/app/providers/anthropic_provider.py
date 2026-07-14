from __future__ import annotations

import structlog
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.providers.base import BaseProvider, LLMResponse

log = structlog.get_logger(__name__)


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", base_url: str | None = None):
        if base_url:
            self._client = AsyncAnthropic(api_key=api_key, base_url=base_url)
        else:
            self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> LLMResponse:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        tokens_used = None
        if response.usage:
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

        return LLMResponse(
            content=content,
            model=response.model,
            provider=self.name,
            tokens_used=tokens_used,
            finish_reason=response.stop_reason,
        )

    async def is_available(self) -> bool:
        try:
            await self._client.messages.create(
                model=self._model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False
