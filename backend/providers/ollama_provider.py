"""
NexusAI — Ollama provider adapter.
Connects to a local Ollama server for private, unlimited inference.
"""

import time
from typing import AsyncGenerator
import httpx
from backend.providers.base import AIProvider
from backend.config import config


class OllamaProvider(AIProvider):
    name = "ollama"
    provider_type = "local"
    requires_api_key = False

    def __init__(self):
        self.base_url = config.OLLAMA_BASE_URL
        self.default_model = config.OLLAMA_DEFAULT_MODEL

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
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if stream:
            return self._stream_chat(payload)

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    async def _stream_chat(self, payload: dict) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content

    async def list_models(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = resp.json().get("models", [])
                return [
                    {
                        "id": m["name"],
                        "name": m["name"],
                        "size": m.get("size", 0),
                        "provider": self.name,
                    }
                    for m in models
                ]
        except Exception:
            return []

    async def health_check(self) -> dict:
        try:
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                latency = (time.monotonic() - start) * 1000
                return {
                    "healthy": resp.status_code == 200,
                    "latency_ms": round(latency, 1),
                    "detail": f"{len(resp.json().get('models', []))} models available",
                }
        except Exception as e:
            return {"healthy": False, "latency_ms": 0, "detail": str(e)}
