"""
NexusAI Tool — Data Extractor (extract text and data from URLs).
"""

import httpx
from backend.agents.base_agent import Tool


async def _extract_url(url: str, max_chars: int = 5000) -> str:
    """Extract readable text content from a URL."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 NexusAI/1.0"},
            )
            resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")

        if "json" in content_type:
            return resp.text[:max_chars]

        if "html" in content_type:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")

            # Remove scripts, styles, nav, footer
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            # Get title
            title = soup.title.string.strip() if soup.title else "No title"

            # Get main text
            text = soup.get_text(separator="\n", strip=True)
            lines = [line for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)

            if len(text) > max_chars:
                text = text[:max_chars] + "\n... [truncated]"

            return f"Title: {title}\n\n{text}"

        # Plain text
        return resp.text[:max_chars]

    except Exception as e:
        return f"Extraction error: {str(e)}"


extract_url_tool = Tool(
    name="extract_url",
    description="Extract readable text content from a URL. Removes HTML boilerplate and returns clean text.",
    parameters={
        "url": {"type": "string", "description": "The URL to extract content from"},
        "max_chars": {"type": "integer", "description": "Max characters to return (default 5000)"},
    },
    func=_extract_url,
)
