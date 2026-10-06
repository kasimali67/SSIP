"""Thin client for any OpenAI-compatible chat endpoint (OpenRouter by default).

Retries transient failures with backoff and raises LLMUnavailable so callers
can fall back to deterministic logic. Prompt and response text are never logged.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx

from app.core.config import get_settings

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class LLMUnavailable(RuntimeError):
    """Raised when the LLM cannot produce a usable answer."""


async def _chat(messages: list[dict[str, str]], *, json_mode: bool, retries: int = 2) -> str:
    settings = get_settings()
    if not settings.llm_api_key:
        raise LLMUnavailable("llm_not_configured")

    payload: dict[str, Any] = {"model": settings.llm_model, "temperature": 0, "messages": messages}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    last_error = "unknown"
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        for attempt in range(retries + 1):
            try:
                response = await client.post(
                    f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json=payload,
                )
                if response.status_code in _RETRYABLE_STATUS:
                    last_error = f"http_{response.status_code}"
                elif response.is_error:
                    raise LLMUnavailable(f"http_{response.status_code}")
                else:
                    return str(response.json()["choices"][0]["message"]["content"])
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = type(exc).__name__
            except (KeyError, IndexError, ValueError) as exc:
                raise LLMUnavailable("malformed_response") from exc
            await asyncio.sleep(0.5 * 2**attempt)
    raise LLMUnavailable(last_error)


async def chat_json(system: str, user: str) -> dict[str, Any]:
    raw = await _chat([{"role": "system", "content": system}, {"role": "user", "content": user}], json_mode=True)
    try:
        parsed = json.loads(_FENCE.sub("", raw.strip()))
    except json.JSONDecodeError as exc:
        raise LLMUnavailable("invalid_json") from exc
    if not isinstance(parsed, dict):
        raise LLMUnavailable("json_not_object")
    return parsed


async def chat_text(system: str, user: str) -> str:
    return await _chat([{"role": "system", "content": system}, {"role": "user", "content": user}], json_mode=False)
