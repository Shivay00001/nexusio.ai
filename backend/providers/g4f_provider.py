"""
NexusAI — g4f (GPT4Free) provider adapter.
Multi-provider aggregator for free access to GPT-4o, Claude, DeepSeek, etc.
"""

import time
import asyncio
from typing import AsyncGenerator
from backend.providers.base import AIProvider
from backend.config import config


class G4FProvider(AIProvider):
    name = "g4f"
    provider_type = "aggregator"
    requires_api_key = False

    def __init__(self):
        self.default_model = config.G4F_DEFAULT_MODEL

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str | AsyncGenerator[str, None]:
        model = model or self.default_model

        if stream:
            return self._stream_chat(messages, model, temperature, max_tokens)

        # Run sync g4f in thread pool
        def _sync_call():
            from g4f.client import Client
            client = Client()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        return await asyncio.to_thread(_sync_call)

    async def _stream_chat(
        self, messages: list[dict], model: str, temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        def _sync_stream():
            from g4f.client import Client
            client = Client()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

        # Bridge sync generator to async
        gen = _sync_stream()
        loop = asyncio.get_event_loop()
        while True:
            try:
                chunk = await loop.run_in_executor(None, next, gen)
                yield chunk
            except StopIteration:
                break

    async def list_models(self) -> list[dict]:
        try:
            def _get_models():
                from g4f.models import ModelUtils
                models = []
                for name in list(ModelUtils.convert.keys())[:30]:
                    models.append({"id": name, "name": name, "provider": self.name})
                return models
            return await asyncio.to_thread(_get_models)
        except Exception:
            return [
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": self.name},
                {"id": "gpt-4o", "name": "GPT-4o", "provider": self.name},
                {"id": "gpt-4", "name": "GPT-4", "provider": self.name},
            ]

    async def health_check(self) -> dict:
        try:
            start = time.monotonic()
            result = await self.chat(
                [{"role": "user", "content": "Say OK"}],
                model=self.default_model,
                max_tokens=5,
            )
            latency = (time.monotonic() - start) * 1000
            return {
                "healthy": bool(result),
                "latency_ms": round(latency, 1),
                "detail": f"Responded with: {result[:50]}",
            }
        except Exception as e:
            return {"healthy": False, "latency_ms": 0, "detail": str(e)}
