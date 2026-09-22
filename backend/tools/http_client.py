"""
NexusAI Tool — HTTP Client for making API calls.
"""

import httpx
import json
from backend.agents.base_agent import Tool


async def _http_get(url: str, headers: str = "{}") -> str:
    """Make an HTTP GET request."""
    try:
        h = json.loads(headers) if isinstance(headers, str) else headers
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers=h)
            content_type = resp.headers.get("content-type", "")
            body = resp.text
            if len(body) > 5000:
                body = body[:5000] + "\n... [truncated]"
            return f"Status: {resp.status_code}\nContent-Type: {content_type}\n\n{body}"
    except Exception as e:
        return f"HTTP GET error: {str(e)}"


async def _http_post(url: str, data: str = "{}", headers: str = "{}") -> str:
    """Make an HTTP POST request with JSON body."""
    try:
        h = json.loads(headers) if isinstance(headers, str) else headers
        d = json.loads(data) if isinstance(data, str) else data
        h.setdefault("Content-Type", "application/json")
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.post(url, json=d, headers=h)
            body = resp.text
            if len(body) > 5000:
                body = body[:5000] + "\n... [truncated]"
            return f"Status: {resp.status_code}\n\n{body}"
    except Exception as e:
        return f"HTTP POST error: {str(e)}"


http_get_tool = Tool(
    name="http_get",
    description="Make an HTTP GET request to a URL. Useful for fetching API data, checking endpoints, etc.",
    parameters={
        "url": {"type": "string", "description": "The URL to request"},
        "headers": {"type": "string", "description": "JSON string of headers (optional)"},
    },
    func=_http_get,
)

http_post_tool = Tool(
    name="http_post",
    description="Make an HTTP POST request with a JSON body. Useful for calling APIs.",
    parameters={
        "url": {"type": "string", "description": "The URL to request"},
        "data": {"type": "string", "description": "JSON string of the request body"},
        "headers": {"type": "string", "description": "JSON string of headers (optional)"},
    },
    func=_http_post,
)
