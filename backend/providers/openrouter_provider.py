"""
NexusAI — OpenRouter provider adapter.
Access free (:free suffix) models via OpenAI-compatible API.
"""

import time
import json
from typing import AsyncGenerator
import httpx
from backend.providers.base import AIProvider
from backend.config import config


class OpenRouterProvider(AIProvider):
    name = "openrouter"
    provider_type = "cloud"
    requires_api_key = True  # Free key, but required

    def __init__(self):
        self.api_key = config.OPENROUTER_API_KEY
        self.base_url = config.OPENROUTER_BASE_URL
        self.default_model = config.OPENROUTER_DEFAULT_MODEL

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "NexusAI",
        }
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

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
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if stream:
            return self._stream_chat(payload)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            return (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

    async def _stream_chat(self, payload: dict) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            content = (
                                data.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def list_models(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/models", headers=self._headers()
                )
                resp.raise_for_status()
                models = resp.json().get("data", [])
                # Filter free models
                free_models = [
                    {
                        "id": m["id"],
                        "name": m.get("name", m["id"]),
                        "provider": self.name,
                        "context_length": m.get("context_length", 0),
                    }
                    for m in models
                    if ":free" in m.get("id", "")
                    or m.get("pricing", {}).get("prompt", "1") == "0"
                ]
                return free_models[:20]
        except Exception:
            return [
                {"id": "google/gemma-3-27b-it:free", "name": "Gemma 3 27B",
                 "provider": self.name},
                {"id": "meta-llama/llama-3.3-70b-instruct:free",
                 "name": "Llama 3.3 70B", "provider": self.name},
            ]

    async def health_check(self) -> dict:
        if not self.api_key:
            return {"healthy": False, "latency_ms": 0,
                    "detail": "No API key configured"}
        try:
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/models", headers=self._headers()
                )
                latency = (time.monotonic() - start) * 1000
                return {
                    "healthy": resp.status_code == 200,
                    "latency_ms": round(latency, 1),
                    "detail": "OpenRouter API reachable",
                }
        except Exception as e:
            return {"healthy": False, "latency_ms": 0, "detail": str(e)}
