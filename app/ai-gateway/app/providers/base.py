"""
Base provider contract — all LLM providers must implement this.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_used: int | None
    finish_reason: str | None


class BaseProvider(ABC):
    name: str

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        ...
