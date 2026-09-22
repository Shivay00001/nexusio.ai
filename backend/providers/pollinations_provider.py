"""
NexusAI — Pollinations AI provider adapter.
Free text & image generation with no API key required.
"""

import time
import json
from typing import AsyncGenerator
import httpx
from backend.providers.base import AIProvider
from backend.config import config


class PollinationsProvider(AIProvider):
    name = "pollinations"
    provider_type = "cloud"
    requires_api_key = False

    def __init__(self):
        self.text_url = config.POLLINATIONS_TEXT_URL
        self.image_url = config.POLLINATIONS_IMAGE_URL
        self.default_model = config.POLLINATIONS_DEFAULT_MODEL

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
                self.text_url,
                json=payload,
                headers={"Content-Type": "application/json"},
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
                "POST", self.text_url, json=payload,
                headers={"Content-Type": "application/json"},
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

    async def generate_image(self, prompt: str, **kwargs) -> str:
        """Generate an image and return the URL."""
        import urllib.parse
        encoded = urllib.parse.quote(prompt)
        return f"{self.image_url}{encoded}"

    async def list_models(self) -> list[dict]:
        return [
            {"id": "openai", "name": "OpenAI (Pollinations)", "provider": self.name},
            {"id": "mistral", "name": "Mistral (Pollinations)", "provider": self.name},
            {"id": "llama", "name": "Llama (Pollinations)", "provider": self.name},
        ]

    async def health_check(self) -> dict:
        try:
            start = time.monotonic()
            result = await self.chat(
                [{"role": "user", "content": "Say OK"}],
                max_tokens=5,
            )
            latency = (time.monotonic() - start) * 1000
            return {
                "healthy": bool(result),
                "latency_ms": round(latency, 1),
                "detail": "Pollinations API reachable",
            }
        except Exception as e:
            return {"healthy": False, "latency_ms": 0, "detail": str(e)}
