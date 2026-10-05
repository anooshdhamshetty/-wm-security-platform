"""
Application configuration.

All secrets and environment-specific values are loaded from environment
variables (see .env.example). Nothing is hardcoded.
"""
import os
from functools import lru_cache
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Settings:
    # --- GitHub ---
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./security_platform.db")

    # --- LLM ---
    # LLM_PROVIDER selects which API the evidence-analysis reasoning layer calls.
    # "groq"      -> Groq's OpenAI-compatible chat completions API (fast, cheap, good default)
    # "anthropic" -> Anthropic's Messages API
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", os.getenv("LLM_API_KEY", ""))
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # --- Target / scope safety ---
    # Comma-separated list of base URLs that the platform is allowed to
    # actively test against. Anything not in this list is refused by the
    # httpx test runner regardless of what the user requests.
    ALLOWED_TARGET_HOSTS: List[str] = [
        h.strip()
        for h in os.getenv("ALLOWED_TARGET_HOSTS", "localhost,127.0.0.1").split(",")
        if h.strip()
    ]
    TARGET_BASE_URL: str = os.getenv("TARGET_BASE_URL", "http://localhost:8080")

    # --- Safety limits ---
    MAX_REQUESTS_PER_ASSESSMENT: int = int(os.getenv("MAX_REQUESTS_PER_ASSESSMENT", "200"))
    REQUEST_RATE_LIMIT_PER_SEC: float = float(os.getenv("REQUEST_RATE_LIMIT_PER_SEC", "2"))
    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))

    # --- CORS ---
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
