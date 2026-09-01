"""
config.py — typed, environment-driven configuration.

Every knob in the system is declared here exactly once. Secrets are read from
the environment (or a local ``.env``) and are never logged or serialised.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["ollama", "groq", "google", "openai", "anthropic", "openrouter"]

#: Human-facing labels for the provider picker in the UI.
PROVIDER_LABELS: dict[str, str] = {
    "ollama": "Ollama — local & free",
    "groq": "Groq — fastest cloud inference",
    "google": "Google Gemini",
    "openai": "OpenAI",
    "anthropic": "Anthropic Claude",
    "openrouter": "OpenRouter — any model",
}

#: Suggested models per provider. Purely advisory: any string is accepted.
SUGGESTED_MODELS: dict[str, list[str]] = {
    "ollama": ["llama3.2", "llama3.1", "qwen2.5", "mistral", "phi3", "gemma2"],
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
    ],
    "google": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    "openai": ["gpt-4o-mini", "gpt-4o", "o3-mini"],
    "anthropic": ["claude-sonnet-4-5", "claude-3-5-haiku-latest"],
    "openrouter": ["meta-llama/llama-3.3-70b-instruct", "google/gemini-2.0-flash-001"],
}


class Settings(BaseSettings):
    """Runtime configuration resolved from environment variables / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Which brain to use ───────────────────────────────────────────────
    llm_provider: Provider = "ollama"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_timeout_seconds: int = Field(default=180, ge=10, le=900)
    llm_max_retries: int = Field(default=2, ge=0, le=5)

    #: Providers tried, in order, when the primary one fails.
    llm_fallback_providers: str = "ollama"

    # ── Ollama (local) ───────────────────────────────────────────────────
    ollama_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"

    # ── Cloud providers ──────────────────────────────────────────────────
    groq_api_key: SecretStr | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    google_api_key: SecretStr | None = None
    google_model: str = "gemini-2.0-flash"

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-sonnet-4-5"

    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # ── Grounding: real-world data instead of hallucinations ─────────────
    enable_live_data: bool = True
    live_data_timeout_seconds: float = Field(default=8.0, ge=1.0, le=60.0)

    # ── Performance ──────────────────────────────────────────────────────
    enable_llm_cache: bool = True
    cache_path: str = ".cache/llm_cache.sqlite"
    checkpoint_path: str = ".cache/checkpoints.sqlite"

    # ── Observability (LangSmith is entirely optional) ───────────────────
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "ai-travel-planner"
    langsmith_tracing: bool = False

    # ── Derived helpers ──────────────────────────────────────────────────

    def default_model_for(self, provider: str) -> str:
        """Return the configured default model name for ``provider``."""
        return {
            "ollama": self.ollama_model,
            "groq": self.groq_model,
            "google": self.google_model,
            "openai": self.openai_model,
            "anthropic": self.anthropic_model,
            "openrouter": self.openrouter_model,
        }.get(provider, self.ollama_model)

    def api_key_for(self, provider: str) -> str | None:
        """Return the plaintext API key for ``provider``, or ``None``."""
        secret: SecretStr | None = {
            "groq": self.groq_api_key,
            "google": self.google_api_key,
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "openrouter": self.openrouter_api_key,
        }.get(provider)
        return secret.get_secret_value() if secret else None

    def is_provider_configured(self, provider: str) -> bool:
        """Ollama needs no key; every cloud provider does."""
        if provider == "ollama":
            return True
        return bool(self.api_key_for(provider))

    def configured_providers(self) -> list[str]:
        """All providers that could actually be called right now."""
        return [p for p in PROVIDER_LABELS if self.is_provider_configured(p)]

    def fallback_chain(self, primary: str) -> list[str]:
        """Ordered, de-duplicated list of providers to attempt."""
        raw = [primary, *self.llm_fallback_providers.split(",")]
        chain: list[str] = []
        for name in (p.strip().lower() for p in raw):
            if name in PROVIDER_LABELS and name not in chain:
                chain.append(name)
        return chain

    def apply_tracing(self) -> None:
        """Wire LangSmith tracing into the process environment, if enabled."""
        if self.langsmith_tracing and self.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.langsmith_api_key.get_secret_value()
            os.environ["LANGCHAIN_PROJECT"] = self.langsmith_project


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide singleton so ``.env`` is parsed exactly once."""
    settings = Settings()
    settings.apply_tracing()
    return settings
