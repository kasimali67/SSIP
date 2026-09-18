import io
import re
from dataclasses import dataclass

import cv2
import numpy as np
from google.cloud import vision

from app.schemas.ocr import OcrExtractResponse, OcrField

MASK_VISIBLE_DIGITS = 4

_ID_PATTERN = re.compile(
    r"\b(\d{4}\s?\d{4}\s?\d{4}|[A-Z]{5}\s?\d{4}\s?[A-Z])\b"
)
_DOB_PATTERN = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})\b")
_NAME_PATTERN = re.compile(r"(?:name|नाम)\s*[:\-]\s*(.+)", re.IGNORECASE)


@dataclass(frozen=True)
class _DetectedWord:
    text: str
    confidence: float


@dataclass(frozen=True)
class _DetectedText:
    text: str
    words: tuple[_DetectedWord, ...]


def mask_id_number(value: str) -> str:
    """Return only the last four characters of an identifier, masked otherwise."""
    cleaned = re.sub(r"\s", "", value.strip())
    if not cleaned:
        return ""
    if len(cleaned) <= MASK_VISIBLE_DIGITS:
        return "X" * len(cleaned)
    hidden = len(cleaned) - MASK_VISIBLE_DIGITS
    return "X" * hidden + cleaned[-MASK_VISIBLE_DIGITS:]


def _clear_buffer(buffer: io.BytesIO) -> None:
    try:
        buffer.seek(0)
        buffer.truncate(0)
    finally:
        buffer.close()


def _deskew(gray: np.ndarray) -> np.ndarray:
    dark_pixels = np.column_stack(np.where(gray < 200))
    if dark_pixels.shape[0] < 10:
        return gray
    angle = cv2.minAreaRect(dark_pixels.astype(np.float32))[-1]
    if angle < -45:
        angle = 90.0 + angle
    if abs(angle) < 0.1:
        return gray
    height, width = gray.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(
        gray,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _enhance_contrast(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _preprocess(buffer: io.BytesIO) -> bytes:
    encoded = np.frombuffer(buffer.getvalue(), dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("Unsupported or corrupt image data")
    processed = _enhance_contrast(_deskew(image))
    success, output = cv2.imencode(".png", processed)
    if not success:
        raise ValueError("Failed to encode preprocessed image")
    return output.tobytes()


def _detect_document_text(image_bytes: bytes) -> _DetectedText:
    client = vision.ImageAnnotatorClient()
    response = client.document_text_detection(image=vision.Image(content=image_bytes))
    if response.error.message:
        raise RuntimeError("Cloud Vision request failed")

    annotation = response.full_text_annotation
    words: list[_DetectedWord] = []
    for page in annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    text = "".join(symbol.text for symbol in word.symbols)
                    words.append(
                        _DetectedWord(text=text, confidence=float(word.confidence))
                    )
    return _DetectedText(text=annotation.text or "", words=tuple(words))


def _field_confidence(match: str, words: tuple[_DetectedWord, ...]) -> float:
    matched = [
        word.confidence for word in words if word.text and word.text in match
    ]
    if not matched:
        return 0.0
    return min(max(sum(matched) / len(matched), 0.0), 1.0)


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    found = pattern.search(text)
    return found.group(1).strip() if found else None


def _build_field(
    value: str | None,
    words: tuple[_DetectedWord, ...],
    *,
    mask: bool,
) -> OcrField:
    if not value:
        return OcrField(value=None, confidence=0.0)
    return OcrField(
        value=mask_id_number(value) if mask else value,
        confidence=_field_confidence(value, words),
    )


def _parse_fields(detected: _DetectedText) -> OcrExtractResponse:
    text = detected.text
    return OcrExtractResponse(
        name=_build_field(_first_match(_NAME_PATTERN, text), detected.words, mask=False),
        dob=_build_field(_first_match(_DOB_PATTERN, text), detected.words, mask=False),
        id_number=_build_field(
            _first_match(_ID_PATTERN, text), detected.words, mask=True
        ),
    )


def extract_fields(image_bytes: bytes) -> OcrExtractResponse:
    if not image_bytes:
        raise ValueError("Empty image payload")

    buffer = io.BytesIO(image_bytes)
    try:
        preprocessed = _preprocess(buffer)
        detected = _detect_document_text(preprocessed)
        return _parse_fields(detected)
    finally:
        _clear_buffer(buffer)
