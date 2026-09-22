"""
NexusAI — Abstract base class for all AI providers.
Every provider adapter implements this interface for uniform access.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class AIProvider(ABC):
    """Uniform interface for all AI providers."""

    name: str = "base"
    provider_type: str = "unknown"  # "local" | "cloud" | "aggregator"
    requires_api_key: bool = False

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str | AsyncGenerator[str, None]:
        """
        Send a chat completion request.
        Returns full text when stream=False, or an async generator of chunks when stream=True.
        """
        ...

    @abstractmethod
    async def list_models(self) -> list[dict]:
        """Return available models as [{"id": ..., "name": ...}, ...]."""
        ...

    @abstractmethod
    async def health_check(self) -> dict:
        """
        Check provider health.
        Returns {"healthy": bool, "latency_ms": float, "detail": str}.
        """
        ...

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name}>"
