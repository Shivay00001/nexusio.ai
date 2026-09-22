"""
NexusAI Configuration
Loads settings from environment variables and .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Config:
    """Central configuration for NexusAI."""

    # ── Server ──────────────────────────────────────────────
    HOST: str = os.getenv("NEXUS_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("NEXUS_PORT", "8000"))
    DEBUG: bool = os.getenv("NEXUS_DEBUG", "true").lower() == "true"

    # ── Database ────────────────────────────────────────────
    DB_PATH: str = os.getenv(
        "NEXUS_DB_PATH",
        str(Path(__file__).resolve().parent / "storage" / "nexus.db"),
    )

    # ── Workspace (for file tools) ──────────────────────────
    WORKSPACE_DIR: str = os.getenv(
        "NEXUS_WORKSPACE",
        str(Path(__file__).resolve().parent.parent / "workspace"),
    )

    # ── Provider: Ollama ────────────────────────────────────
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_DEFAULT_MODEL: str = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")

    # ── Provider: g4f (GPT4Free) ────────────────────────────
    G4F_DEFAULT_MODEL: str = os.getenv("G4F_DEFAULT_MODEL", "gpt-4o-mini")

    # ── Provider: Pollinations ──────────────────────────────
    POLLINATIONS_TEXT_URL: str = os.getenv(
        "POLLINATIONS_TEXT_URL",
        "https://text.pollinations.ai/openai",
    )
    POLLINATIONS_IMAGE_URL: str = os.getenv(
        "POLLINATIONS_IMAGE_URL",
        "https://image.pollinations.ai/prompt/",
    )
    POLLINATIONS_DEFAULT_MODEL: str = os.getenv(
        "POLLINATIONS_DEFAULT_MODEL", "openai"
    )

    # ── Provider: OpenRouter ────────────────────────────────
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = os.getenv(
        "OPENROUTER_DEFAULT_MODEL", "google/gemma-3-27b-it:free"
    )

    # ── Provider: Groq ──────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_DEFAULT_MODEL: str = os.getenv(
        "GROQ_DEFAULT_MODEL", "llama-3.3-70b-versatile"
    )

    # ── Provider: HuggingFace ───────────────────────────────
    HF_API_KEY: str = os.getenv("HF_API_KEY", "")
    HF_DEFAULT_MODEL: str = os.getenv(
        "HF_DEFAULT_MODEL", "mistralai/Mistral-7B-Instruct-v0.3"
    )

    # ── Agent ───────────────────────────────────────────────
    AGENT_MAX_ITERATIONS: int = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))
    AGENT_DEFAULT_PROVIDER: str = os.getenv("AGENT_DEFAULT_PROVIDER", "ollama")

    # ── Provider Priority (for smart routing) ───────────────
    # Comma-separated list; first = highest priority
    PROVIDER_PRIORITY: list[str] = os.getenv(
        "PROVIDER_PRIORITY",
        "ollama,groq,g4f,pollinations,openrouter,huggingface",
    ).split(",")

    @classmethod
    def to_dict(cls) -> dict:
        """Return all non-sensitive config as a dictionary."""
        return {
            k: v
            for k, v in vars(cls).items()
            if not k.startswith("_")
            and k.isupper()
            and "KEY" not in k
            and "SECRET" not in k
        }


config = Config()
