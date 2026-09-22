"""
NexusAI — HuggingFace Inference provider adapter.
Uses the free serverless inference API for smaller open-source models.
"""

import time
import asyncio
from typing import AsyncGenerator
import httpx
from backend.providers.base import AIProvider
from backend.config import config


class HuggingFaceProvider(AIProvider):
    name = "huggingface"
    provider_type = "cloud"
    requires_api_key = True  # Free key

    def __init__(self):
        self.api_key = config.HF_API_KEY
        self.default_model = config.HF_DEFAULT_MODEL
        self.api_url = "https://api-inference.huggingface.co/models"

    def _headers(self) -> dict:
        h = {}
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
        if not self.api_key:
            raise ValueError("HuggingFace API key not configured")

        model = model or self.default_model

        # HuggingFace Inference API uses OpenAI-compatible chat format
        # for instruct models
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": min(max_tokens, 2048),  # HF free tier limit
            "stream": False,  # Serverless doesn't always support streaming
        }

        async with httpx.AsyncClient(timeout=60) as client:
            # Try the chat completions endpoint first
            resp = await client.post(
                "https://api-inference.huggingface.co/v1/chat/completions",
                json=payload,
                headers=self._headers(),
            )

            if resp.status_code == 200:
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                if stream:
                    async def _fake_stream():
                        yield content
                    return _fake_stream()
                return content

            # Fallback: simple text generation API
            prompt = self._messages_to_prompt(messages)
            resp2 = await client.post(
                f"{self.api_url}/{model}",
                json={
                    "inputs": prompt,
                    "parameters": {
                        "temperature": temperature,
                        "max_new_tokens": min(max_tokens, 1024),
                        "return_full_text": False,
                    },
                },
                headers=self._headers(),
            )
            resp2.raise_for_status()
            data = resp2.json()
            if isinstance(data, list) and data:
                text = data[0].get("generated_text", "")
            else:
                text = str(data)

            if stream:
                async def _fake_stream2():
                    yield text
                return _fake_stream2()
            return text

    @staticmethod
    def _messages_to_prompt(messages: list[dict]) -> str:
        """Convert chat messages to a simple prompt string."""
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"[System]: {content}")
            elif role == "assistant":
                parts.append(f"[Assistant]: {content}")
            else:
                parts.append(f"[User]: {content}")
        parts.append("[Assistant]:")
        return "\n".join(parts)

    async def list_models(self) -> list[dict]:
        return [
            {"id": "mistralai/Mistral-7B-Instruct-v0.3",
             "name": "Mistral 7B Instruct", "provider": self.name},
            {"id": "microsoft/Phi-3-mini-4k-instruct",
             "name": "Phi-3 Mini 4K", "provider": self.name},
            {"id": "google/gemma-2-2b-it",
             "name": "Gemma 2 2B", "provider": self.name},
            {"id": "HuggingFaceH4/zephyr-7b-beta",
             "name": "Zephyr 7B", "provider": self.name},
        ]

    async def health_check(self) -> dict:
        if not self.api_key:
            return {"healthy": False, "latency_ms": 0,
                    "detail": "No API key configured"}
        try:
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.api_url}/{self.default_model}",
                    headers=self._headers(),
                )
                latency = (time.monotonic() - start) * 1000
                healthy = resp.status_code in (200, 503)  # 503 = model loading
                detail = "Model ready" if resp.status_code == 200 else "Model loading"
                return {
                    "healthy": healthy,
                    "latency_ms": round(latency, 1),
                    "detail": detail,
                }
        except Exception as e:
            return {"healthy": False, "latency_ms": 0, "detail": str(e)}
