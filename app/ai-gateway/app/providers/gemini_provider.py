from __future__ import annotations

import json
import structlog
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.providers.base import BaseProvider, LLMResponse

log = structlog.get_logger(__name__)


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-flash-latest", base_url: str | None = None):
        # The Gemini SDK handles the default endpoint internally.
        # Only set api_endpoint if the user is explicitly pointing to a custom proxy/gateway.
        if base_url and "generativelanguage.googleapis.com" not in base_url:
            genai.configure(api_key=api_key, client_options={'api_endpoint': base_url})
        else:
            genai.configure(api_key=api_key)
        self._model_name = model
        self._model = genai.GenerativeModel(model_name=model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> LLMResponse:
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = await self._model.generate_content_async(
            combined_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        content = response.text or ""
        tokens = None
        if hasattr(response, "usage_metadata"):
            tokens = getattr(response.usage_metadata, "total_token_count", None)

        return LLMResponse(
            content=content,
            model=self._model_name,
            provider=self.name,
            tokens_used=tokens,
            finish_reason=None,
        )

    async def is_available(self) -> bool:
        try:
            models = genai.list_models()
            return len(list(models)) > 0
        except Exception:
            return False
