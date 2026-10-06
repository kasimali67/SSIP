"""Pluggable OCR providers with an ordered fallback chain.

OCR_PROVIDER_CHAIN=["google_vision","tesseract"]               normal
OCR_PROVIDER_CHAIN=["google_vision","tesseract","demo_fixture"] offline pitch

Every provider receives already-preprocessed PNG bytes (from the existing
OpenCV step) and returns lines with 0.00-1.00 confidence. Nothing touches
disk and no recognised text is ever logged.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OcrLine:
    text: str
    confidence: float  # 0.00 - 1.00


@dataclass(frozen=True)
class OcrText:
    lines: list[OcrLine] = field(default_factory=list)
    provider: str = ""
    is_demo: bool = False


class OcrUnavailable(RuntimeError):
    """Raised when no configured provider could read the document."""


class OcrProvider(Protocol):
    name: str

    async def extract(self, image_png: bytes) -> OcrText: ...


class GoogleVisionProvider:
    name = "google_vision"

    def __init__(self) -> None:
        from google.cloud import vision  # lazy: missing creds must not break imports

        self._vision = vision
        self._client = vision.ImageAnnotatorClient()  # raises if credentials are missing

    async def extract(self, image_png: bytes) -> OcrText:
        return await asyncio.to_thread(self._extract_sync, image_png)

    def _extract_sync(self, image_png: bytes) -> OcrText:
        vision = self._vision
        response = self._client.document_text_detection(
            image=vision.Image(content=image_png),
            image_context=vision.ImageContext(language_hints=["en", "hi", "gu"]),
        )
        if response.error.message:
            raise OcrUnavailable("vision_api_error")
        lines: list[OcrLine] = []
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    words = ["".join(symbol.text for symbol in word.symbols) for word in paragraph.words]
                    text = " ".join(words).strip()
                    if text:
                        lines.append(OcrLine(text=text, confidence=round(float(paragraph.confidence), 2)))
        return OcrText(lines=lines, provider=self.name)


class TesseractProvider:
    """Offline fallback. Needs the tesseract binary plus hin/guj traineddata."""

    name = "tesseract"

    def __init__(self) -> None:
        import pytesseract

        settings = get_settings()
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        pytesseract.get_tesseract_version()  # raises if the binary is missing
        self._pytesseract = pytesseract
        self._langs = settings.tesseract_langs

    async def extract(self, image_png: bytes) -> OcrText:
        return await asyncio.to_thread(self._extract_sync, image_png)

    def _extract_sync(self, image_png: bytes) -> OcrText:
        import cv2
        import numpy as np

        image = cv2.imdecode(np.frombuffer(image_png, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise OcrUnavailable("undecodable_image")
        data = self._pytesseract.image_to_data(
            image, lang=self._langs, output_type=self._pytesseract.Output.DICT
        )
        grouped: dict[tuple[int, int, int], list[tuple[str, float]]] = {}
        for index, word in enumerate(data["text"]):
            confidence = float(data["conf"][index])
            if not str(word).strip() or confidence < 0:
                continue
            key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
            grouped.setdefault(key, []).append((str(word), confidence / 100.0))
        del image
        lines = [
            OcrLine(
                text=" ".join(word for word, _ in words),
                confidence=round(sum(conf for _, conf in words) / len(words), 2),
            )
            for _, words in sorted(grouped.items())
        ]
        return OcrText(lines=lines, provider=self.name)


# Synthetic sample only. The ID uses a leading 0, which real Aadhaar numbers never have.
_DEMO_LINES = [
    OcrLine("GOVERNMENT OF INDIA", 0.97),
    OcrLine("Ramesh Kumar Patel", 0.93),
    OcrLine("DOB: 15/08/1985", 0.71),
    OcrLine("Male", 0.95),
    OcrLine("0000 0000 4821", 0.96),
]


class DemoFixtureProvider:
    """Last-resort provider for offline pitches. Always flagged is_demo=True."""

    name = "demo_fixture"

    async def extract(self, image_png: bytes) -> OcrText:
        return OcrText(lines=list(_DEMO_LINES), provider=self.name, is_demo=True)


_REGISTRY: dict[str, type] = {
    GoogleVisionProvider.name: GoogleVisionProvider,
    TesseractProvider.name: TesseractProvider,
    DemoFixtureProvider.name: DemoFixtureProvider,
}


@lru_cache
def _build_chain(names: tuple[str, ...]) -> tuple[OcrProvider, ...]:
    """Built once per process. Restart the server after fixing credentials."""
    providers: list[OcrProvider] = []
    for name in names:
        provider_cls = _REGISTRY.get(name)
        if provider_cls is None:
            logger.warning("ocr_provider_unknown", extra={"provider": name})
            continue
        try:
            providers.append(provider_cls())
        except Exception as exc:  # noqa: BLE001 - any init failure means "skip this provider"
            logger.warning("ocr_provider_unavailable", extra={"provider": name, "reason": type(exc).__name__})
    return tuple(providers)


async def run_ocr(image_png: bytes) -> OcrText:
    settings = get_settings()
    for provider in _build_chain(tuple(settings.ocr_provider_chain)):
        try:
            result = await asyncio.wait_for(provider.extract(image_png), timeout=settings.ocr_timeout_seconds)
        except Exception as exc:  # noqa: BLE001 - fall through to the next provider
            logger.warning("ocr_provider_failed", extra={"provider": provider.name, "reason": type(exc).__name__})
            continue
        if result.lines:
            return result
    raise OcrUnavailable("all_ocr_providers_failed")
