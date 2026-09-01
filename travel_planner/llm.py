"""
llm.py — provider-agnostic model router with schema-guaranteed output.

Two problems this module solves:

1. **Provider lock-in.** ``get_chat_model()`` returns a LangChain chat model for
   any of six providers from one call signature. Provider SDKs are imported
   lazily so a missing optional dependency never breaks startup.

2. **Unreliable JSON.** ``invoke_structured()`` asks for native structured
   output first (``with_structured_output``). If the provider or the model
   can't honour that, it degrades to a JSON-schema-instructed prompt, then to a
   brace-matching salvage parser, and finally to a caller-supplied fallback.
   The caller always receives a valid Pydantic model — never a raw string.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from travel_planner.config import Settings, get_settings

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


class LLMUnavailableError(RuntimeError):
    """Raised when no configured provider could be reached."""


# ─────────────────────────────────────────────────────────────
#  Response cache — identical prompts are answered instantly
# ─────────────────────────────────────────────────────────────


def install_cache(settings: Settings | None = None) -> None:
    """Enable LangChain's SQLite response cache (idempotent, best-effort)."""
    settings = settings or get_settings()
    if not settings.enable_llm_cache:
        return
    try:
        from langchain_community.cache import SQLiteCache
        from langchain_core.globals import get_llm_cache, set_llm_cache

        if get_llm_cache() is not None:
            return
        path = Path(settings.cache_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        set_llm_cache(SQLiteCache(database_path=str(path)))
    except Exception as exc:  # pragma: no cover - cache is a nicety, not a need
        logger.debug("LLM cache unavailable: %s", exc)


# ─────────────────────────────────────────────────────────────
#  Model factory
# ─────────────────────────────────────────────────────────────


def _build_model(provider: str, model: str, settings: Settings) -> Any:
    """Instantiate one provider's chat model. Raises ImportError if uninstalled."""
    temperature = settings.llm_temperature
    timeout = settings.llm_timeout_seconds

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            client_kwargs={"timeout": timeout},
        )

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model,
            api_key=settings.api_key_for("groq"),
            temperature=temperature,
            timeout=timeout,
            max_retries=0,
        )

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.api_key_for("google"),
            temperature=temperature,
            timeout=timeout,
            max_retries=0,
        )

    if provider in ("openai", "openrouter"):
        from langchain_openai import ChatOpenAI

        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "timeout": timeout,
            "max_retries": 0,
            "api_key": settings.api_key_for(provider),
        }
        if provider == "openrouter":
            kwargs["base_url"] = settings.openrouter_base_url
        return ChatOpenAI(**kwargs)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            api_key=settings.api_key_for("anthropic"),
            temperature=temperature,
            timeout=timeout,
            max_retries=0,
        )

    raise ValueError(f"Unknown provider: {provider!r}")


def get_chat_model(
    provider: str | None = None,
    model: str | None = None,
    settings: Settings | None = None,
) -> Any:
    """Return a ready-to-use chat model for ``provider``."""
    settings = settings or get_settings()
    provider = (provider or settings.llm_provider).lower()
    model = model or settings.default_model_for(provider)

    if not settings.is_provider_configured(provider):
        raise LLMUnavailableError(
            f"Provider '{provider}' has no API key configured. "
            f"Set it in .env or pick another provider."
        )

    install_cache(settings)
    return _build_model(provider, model, settings)


# ─────────────────────────────────────────────────────────────
#  Resilient JSON salvage (last line of defence)
# ─────────────────────────────────────────────────────────────


def salvage_json(text: str) -> Any | None:
    """Recover a JSON value from noisy LLM prose. Returns ``None`` on failure."""
    if not text or not text.strip():
        return None

    candidates = [text.strip(), re.sub(r"```(?:json)?\s*|```", "", text).strip()]
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # Balanced-delimiter scan, string-literal aware so braces inside quoted
    # values do not corrupt the depth counter.
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        if start == -1:
            continue
        depth, in_string, escaped = 0, False, False
        for index in range(start, len(text)):
            char = text[index]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == open_ch:
                depth += 1
            elif char == close_ch:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : index + 1])
                    except json.JSONDecodeError:
                        break
    return None


def _coerce(schema: type[TModel], payload: Any) -> TModel | None:
    """Validate ``payload`` against ``schema``, tolerating a few shapes."""
    if payload is None:
        return None
    try:
        if isinstance(payload, schema):
            return payload
        if isinstance(payload, dict):
            return schema.model_validate(payload)
        if isinstance(payload, list):
            # A bare array where an object with one list field was expected.
            for name, field in schema.model_fields.items():
                if getattr(field.annotation, "__origin__", None) is list:
                    return schema.model_validate({name: payload})
    except ValidationError as exc:
        logger.debug("Schema coercion failed for %s: %s", schema.__name__, exc)
    return None


def _text_of(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):  # Anthropic-style content blocks
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)


# ─────────────────────────────────────────────────────────────
#  Structured invocation
# ─────────────────────────────────────────────────────────────


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _invoke_with_retry(runnable: Any, prompt: str) -> Any:
    return runnable.invoke(prompt)


def invoke_structured(
    prompt: str,
    schema: type[TModel],
    *,
    provider: str | None = None,
    model: str | None = None,
    fallback: TModel | None = None,
    settings: Settings | None = None,
) -> tuple[TModel, str | None]:
    """Run ``prompt`` and return ``(validated_model, error_or_None)``.

    Providers are attempted in the order given by
    :meth:`Settings.fallback_chain`. Within each provider three strategies are
    tried: native structured output, JSON-schema-instructed prompting, then
    brace-matching salvage.
    """
    settings = settings or get_settings()
    primary = (provider or settings.llm_provider).lower()
    schema_hint = json.dumps(schema.model_json_schema(), indent=None)[:4000]
    problems: list[str] = []

    for candidate in settings.fallback_chain(primary):
        if not settings.is_provider_configured(candidate):
            continue
        chosen_model = model if candidate == primary and model else None
        try:
            llm = get_chat_model(candidate, chosen_model, settings)
        except Exception as exc:
            problems.append(f"{candidate}: {exc}")
            continue

        # Strategy 1 — native structured output.
        try:
            structured = llm.with_structured_output(schema)
            result = _coerce(schema, _invoke_with_retry(structured, prompt))
            if result is not None:
                return result, None
            problems.append(f"{candidate}: structured output returned nothing usable")
        except Exception as exc:
            problems.append(f"{candidate}: structured output failed ({exc})")

        # Strategy 2 + 3 — instructed prompt, then salvage.
        try:
            json_prompt = (
                f"{prompt}\n\n"
                "Respond with a single JSON object and nothing else. "
                "No markdown fences, no commentary, no trailing text.\n"
                f"It must validate against this JSON Schema:\n{schema_hint}"
            )
            raw = _text_of(_invoke_with_retry(llm, json_prompt))
            result = _coerce(schema, salvage_json(raw))
            if result is not None:
                return result, None
            problems.append(f"{candidate}: response did not match schema")
        except Exception as exc:
            problems.append(f"{candidate}: {exc}")

    message = f"{schema.__name__}: " + " | ".join(problems[-3:] or ["no provider available"])
    if fallback is not None:
        return fallback, message
    raise LLMUnavailableError(message)


def invoke_text(
    prompt: str,
    *,
    provider: str | None = None,
    model: str | None = None,
    fallback: str = "",
    settings: Settings | None = None,
) -> tuple[str, str | None]:
    """Free-form generation with the same provider fallback chain."""
    settings = settings or get_settings()
    primary = (provider or settings.llm_provider).lower()
    problems: list[str] = []

    for candidate in settings.fallback_chain(primary):
        if not settings.is_provider_configured(candidate):
            continue
        try:
            llm = get_chat_model(
                candidate, model if candidate == primary else None, settings
            )
            text = _text_of(_invoke_with_retry(llm, prompt)).strip()
            if len(text) > 10:
                return text, None
            problems.append(f"{candidate}: response too short")
        except Exception as exc:
            problems.append(f"{candidate}: {exc}")

    return fallback, " | ".join(problems[-3:] or ["no provider available"])


def health_check(provider: str, model: str | None = None) -> tuple[bool, str]:
    """Cheap round-trip used by the UI to show a live provider status dot."""
    try:
        llm = get_chat_model(provider, model)
        text = _text_of(llm.invoke("Reply with the single word: ok"))
        return True, (text or "ok").strip()[:60]
    except Exception as exc:
        return False, str(exc)[:200]


__all__ = [
    "LLMUnavailableError",
    "get_chat_model",
    "health_check",
    "install_cache",
    "invoke_structured",
    "invoke_text",
    "salvage_json",
]
