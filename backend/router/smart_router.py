"""
NexusAI — Smart Router.
Intelligent routing with priority-based fallback, health awareness,
and model-specific provider selection.
"""

import asyncio
import logging
import time
from typing import AsyncGenerator

from backend.providers.base import AIProvider
from backend.providers.ollama_provider import OllamaProvider
from backend.providers.g4f_provider import G4FProvider
from backend.providers.pollinations_provider import PollinationsProvider
from backend.providers.openrouter_provider import OpenRouterProvider
from backend.providers.groq_provider import GroqProvider
from backend.providers.huggingface_provider import HuggingFaceProvider
from backend.config import config

logger = logging.getLogger("nexus.router")


# Model → Provider mapping hints
MODEL_HINTS: dict[str, list[str]] = {
    "gpt-4": ["g4f"],
    "gpt-4o": ["g4f"],
    "gpt-4o-mini": ["g4f", "pollinations"],
    "gpt-3.5": ["g4f"],
    "claude": ["g4f"],
    "llama": ["ollama", "groq", "openrouter"],
    "llama3": ["ollama", "groq"],
    "mistral": ["ollama", "huggingface", "openrouter"],
    "mixtral": ["groq"],
    "gemma": ["ollama", "openrouter"],
    "phi": ["ollama", "huggingface"],
    "deepseek": ["g4f", "openrouter"],
}


class SmartRouter:
    """
    Intelligent AI provider router with:
    - Priority-based provider selection
    - Automatic fallback on failure
    - Health-aware routing (skip unhealthy providers)
    - Model-specific routing hints
    - Provider health caching
    """

    def __init__(self):
        self.providers: dict[str, AIProvider] = {}
        self.priority: list[str] = config.PROVIDER_PRIORITY
        self._health_cache: dict[str, dict] = {}
        self._health_ttl = 60  # seconds
        self._health_timestamps: dict[str, float] = {}
        self._init_providers()

    def _init_providers(self):
        """Initialize all provider instances."""
        self.providers = {
            "ollama": OllamaProvider(),
            "g4f": G4FProvider(),
            "pollinations": PollinationsProvider(),
            "openrouter": OpenRouterProvider(),
            "groq": GroqProvider(),
            "huggingface": HuggingFaceProvider(),
        }

    def get_provider(self, name: str) -> AIProvider | None:
        return self.providers.get(name)

    def list_providers(self) -> list[dict]:
        """Return summary info for each provider."""
        result = []
        for name, p in self.providers.items():
            result.append({
                "name": name,
                "type": p.provider_type,
                "requires_api_key": p.requires_api_key,
                "health": self._health_cache.get(name, {}),
            })
        return result

    async def refresh_health(self, force: bool = False):
        """Run health checks on all providers (parallel)."""
        now = time.monotonic()
        tasks = {}
        for name, provider in self.providers.items():
            last = self._health_timestamps.get(name, 0)
            if force or (now - last) > self._health_ttl:
                tasks[name] = provider.health_check()

        if tasks:
            results = await asyncio.gather(
                *tasks.values(), return_exceptions=True
            )
            for name, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    self._health_cache[name] = {
                        "healthy": False, "latency_ms": 0, "detail": str(result)
                    }
                else:
                    self._health_cache[name] = result
                self._health_timestamps[name] = now

    def _resolve_providers(
        self, preferred_provider: str | None, model: str | None
    ) -> list[str]:
        """
        Build an ordered list of providers to try.
        1. User-specified provider (if given)
        2. Model-hinted providers
        3. Priority-ordered healthy providers
        """
        order = []

        # 1) Explicit preference
        if preferred_provider and preferred_provider in self.providers:
            order.append(preferred_provider)

        # 2) Model hints
        if model:
            model_lower = model.lower()
            for hint_key, hint_providers in MODEL_HINTS.items():
                if hint_key in model_lower:
                    for p in hint_providers:
                        if p not in order and p in self.providers:
                            order.append(p)

        # 3) Priority fallback
        for p in self.priority:
            if p not in order and p in self.providers:
                order.append(p)

        # Filter out unhealthy (but keep if no healthy ones exist)
        healthy = [
            p for p in order
            if self._health_cache.get(p, {}).get("healthy", True)
        ]
        return healthy if healthy else order

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        provider: str | None = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> tuple[str | AsyncGenerator[str, None], str, str]:
        """
        Route a chat request through the best available provider.

        Returns:
            (response, provider_name, model_used)
        """
        providers_to_try = self._resolve_providers(provider, model)
        last_error = None

        for pname in providers_to_try:
            p = self.providers[pname]

            # Skip providers needing API keys if none configured
            if p.requires_api_key:
                key_check = {
                    "openrouter": config.OPENROUTER_API_KEY,
                    "groq": config.GROQ_API_KEY,
                    "huggingface": config.HF_API_KEY,
                }.get(pname, "")
                if not key_check:
                    continue

            # Determine model for this provider
            model_to_use = model
            if not model_to_use:
                model_to_use = {
                    "ollama": config.OLLAMA_DEFAULT_MODEL,
                    "g4f": config.G4F_DEFAULT_MODEL,
                    "pollinations": config.POLLINATIONS_DEFAULT_MODEL,
                    "openrouter": config.OPENROUTER_DEFAULT_MODEL,
                    "groq": config.GROQ_DEFAULT_MODEL,
                    "huggingface": config.HF_DEFAULT_MODEL,
                }.get(pname, "auto")

            try:
                logger.info(f"Routing to {pname} with model {model_to_use}")
                result = await p.chat(
                    messages=messages,
                    model=model_to_use,
                    stream=stream,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                return result, pname, model_to_use

            except Exception as e:
                last_error = e
                logger.warning(f"Provider {pname} failed: {e}")
                # Mark as unhealthy temporarily
                self._health_cache[pname] = {
                    "healthy": False,
                    "latency_ms": 0,
                    "detail": f"Failed: {str(e)[:100]}",
                }
                continue

        raise RuntimeError(
            f"All providers failed. Last error: {last_error}"
        )

    async def list_all_models(self) -> dict[str, list[dict]]:
        """List models from all providers."""
        tasks = {
            name: provider.list_models()
            for name, provider in self.providers.items()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        output = {}
        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                output[name] = []
            else:
                output[name] = result
        return output


# Singleton
router = SmartRouter()
