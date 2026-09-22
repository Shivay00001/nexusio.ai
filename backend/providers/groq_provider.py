"""
NexusAI — Groq provider adapter.
Ultra-fast inference on free-tier models using Groq's LPU hardware.
"""

import time
import asyncio
from typing import AsyncGenerator
from backend.providers.base import AIProvider
from backend.config import config


class GroqProvider(AIProvider):
    name = "groq"
    provider_type = "cloud"
    requires_api_key = True  # Free key

    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        self.default_model = config.GROQ_DEFAULT_MODEL

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str | AsyncGenerator[str, None]:
        if not self.api_key:
            raise ValueError("Groq API key not configured")

        model = model or self.default_model

        if stream:
            return self._stream_chat(messages, model, temperature, max_tokens)

        def _sync_call():
            from groq import Groq
            client = Groq(api_key=self.api_key)
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
            from groq import Groq
            client = Groq(api_key=self.api_key)
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

        gen = _sync_stream()
        loop = asyncio.get_event_loop()
        while True:
            try:
                chunk = await loop.run_in_executor(None, next, gen)
                yield chunk
            except StopIteration:
                break

    async def list_models(self) -> list[dict]:
        if not self.api_key:
            return []
        try:
            def _get():
                from groq import Groq
                client = Groq(api_key=self.api_key)
                models = client.models.list()
                return [
                    {
                        "id": m.id,
                        "name": m.id,
                        "provider": self.name,
                        "owned_by": m.owned_by,
                    }
                    for m in models.data
                ]
            return await asyncio.to_thread(_get)
        except Exception:
            return [
                {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B",
                 "provider": self.name},
                {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B",
                 "provider": self.name},
                {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B",
                 "provider": self.name},
            ]

    async def health_check(self) -> dict:
        if not self.api_key:
            return {"healthy": False, "latency_ms": 0,
                    "detail": "No API key configured"}
        try:
            start = time.monotonic()
            def _check():
                from groq import Groq
                client = Groq(api_key=self.api_key)
                client.models.list()
                return True
            await asyncio.to_thread(_check)
            latency = (time.monotonic() - start) * 1000
            return {
                "healthy": True,
                "latency_ms": round(latency, 1),
                "detail": "Groq API reachable",
            }
        except Exception as e:
            return {"healthy": False, "latency_ms": 0, "detail": str(e)}
