"""Multilingual layer: translation, transliteration, and the RAG language policy.

Why queries are translated *before* retrieval: the embedding model
(BAAI/bge-small-en-v1.5) is English-only. A Gujarati or Hindi question embedded
directly retrieves poorly, so the question is translated to English, retrieval
runs in English, and only the answer is localized.

RAG_OUTPUT_STRATEGY:
  translate (default) -> generate in English, translate with Sarvam Mayura
  native              -> instruct the LLM to answer directly in the target language
"""
from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Protocol

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class Language(str, Enum):
    EN = "en"
    HI = "hi"
    GU = "gu"


_SARVAM_CODES = {Language.EN: "en-IN", Language.HI: "hi-IN", Language.GU: "gu-IN"}
_LANGUAGE_NAMES = {Language.EN: "English", Language.HI: "Hindi (हिन्दी)", Language.GU: "Gujarati (ગુજરાતી)"}
_MAX_CHUNK_CHARS = 900

TranslationStatus = Literal["success", "skipped", "failed"]


@dataclass(frozen=True)
class TranslationResult:
    text: str
    status: TranslationStatus


class Translator(Protocol):
    async def translate(self, text: str, source: Language, target: Language) -> TranslationResult: ...


class PassthroughTranslator:
    """Used when no translation key is configured. Never raises."""

    async def translate(self, text: str, source: Language, target: Language) -> TranslationResult:
        return TranslationResult(text, "skipped" if source is target else "failed")


def _chunks(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?।])\s+", text.strip())
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > _MAX_CHUNK_CHARS:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks or [text]


class SarvamTranslator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def _translate_chunk(self, client: httpx.AsyncClient, chunk: str, source: Language, target: Language) -> str:
        payload: dict[str, Any] = {
            "input": chunk,
            "source_language_code": _SARVAM_CODES[source],
            "target_language_code": _SARVAM_CODES[target],
            "model": self._settings.sarvam_translate_model,
        }
        if self._settings.sarvam_translate_mode:
            payload["mode"] = self._settings.sarvam_translate_mode
        last_error: Exception | None = None
        for _ in range(2):  # one retry
            try:
                response = await client.post(
                    self._settings.sarvam_translate_url,
                    headers={"api-subscription-key": self._settings.sarvam_api_key},
                    json=payload,
                )
                response.raise_for_status()
                return str(response.json()["translated_text"])
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                last_error = exc
        raise RuntimeError("translation_failed") from last_error

    async def translate(self, text: str, source: Language, target: Language) -> TranslationResult:
        if source is target or not text.strip():
            return TranslationResult(text, "skipped")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                parts = [await self._translate_chunk(client, chunk, source, target) for chunk in _chunks(text)]
        except RuntimeError as exc:
            logger.warning("translation_failed", extra={"reason": type(exc.__cause__).__name__})
            return TranslationResult(text, "failed")
        return TranslationResult(" ".join(parts), "success")


def detect_script_language(text: str) -> Language:
    if any("\u0a80" <= char <= "\u0aff" for char in text):
        return Language.GU
    if any("\u0900" <= char <= "\u097f" for char in text):
        return Language.HI
    return Language.EN


class SarvamTransliterator:
    """Converts Devanagari/Gujarati names to Latin script for cross-verification."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def to_latin(self, text: str) -> str | None:
        source = detect_script_language(text)
        if source is Language.EN:
            return text
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self._settings.sarvam_transliterate_url,
                    headers={"api-subscription-key": self._settings.sarvam_api_key},
                    json={
                        "input": text,
                        "source_language_code": _SARVAM_CODES[source],
                        "target_language_code": "en-IN",
                    },
                )
                response.raise_for_status()
                return str(response.json()["transliterated_text"])
        except (httpx.HTTPError, KeyError, ValueError):
            return None


def get_translator(settings: Settings) -> Translator:
    return SarvamTranslator(settings) if settings.sarvam_api_key else PassthroughTranslator()


def get_transliterator(settings: Settings) -> SarvamTransliterator | None:
    return SarvamTransliterator(settings) if settings.sarvam_api_key else None


def rag_system_prompt(language: Language, strategy: str) -> str:
    output_language = language if strategy == "native" else Language.EN
    return (
        "You help citizens in Gujarat understand government services. Answer only from the "
        "provided context. If the context does not contain the answer, say so plainly. "
        "Use short sentences and everyday words a first-time applicant understands. "
        "List required documents as a numbered list. "
        f"Write the answer in {_LANGUAGE_NAMES[output_language]}. "
        "Keep official document names in English inside brackets, e.g. (Ration Card)."
    )


AnswerFn = Callable[[str, str], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class LocalizedAnswer:
    answer: str
    sources: list[str]
    language: Language
    translation_status: TranslationStatus


async def answer_in_language(
    question: str,
    language: Language,
    *,
    translator: Translator,
    answer_fn: AnswerFn,
    strategy: str,
) -> LocalizedAnswer:
    """answer_fn(question_in_english, system_prompt) -> {"answer": str, "sources": list[str]}."""
    query = await translator.translate(question, language, Language.EN)
    english_question = query.text  # on failure, the original question is still attempted
    result = await answer_fn(english_question, rag_system_prompt(language, strategy))
    answer, sources = str(result["answer"]), list(result.get("sources", []))

    if language is Language.EN:
        return LocalizedAnswer(answer, sources, language, "skipped")
    if strategy == "native":
        status: TranslationStatus = "failed" if query.status == "failed" else "success"
        return LocalizedAnswer(answer, sources, language, status)
    localized = await translator.translate(answer, Language.EN, language)
    return LocalizedAnswer(localized.text, sources, language, localized.status)
