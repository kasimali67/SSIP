import asyncio
import io

import cv2
import numpy as np

from app.schemas.ocr import OcrExtractResponse, OcrField
from app.services.ocr import run_ocr
from app.services.structuring import structure_document


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


async def extract_fields(image_bytes: bytes) -> OcrExtractResponse:
    if not image_bytes:
        raise ValueError("Empty image payload")

    buffer = io.BytesIO(image_bytes)
    try:
        png_bytes = await asyncio.to_thread(_preprocess, buffer)
        ocr_text = await run_ocr(png_bytes)
        document = await structure_document(ocr_text)
        return OcrExtractResponse(
            name=OcrField(
                value=document.name.value, confidence=document.name.confidence
            ),
            dob=OcrField(
                value=document.dob.value, confidence=document.dob.confidence
            ),
            id_number=OcrField(
                value=document.id_masked.value,
                confidence=document.id_masked.confidence,
            ),
            gender=OcrField(
                value=document.gender.value, confidence=document.gender.confidence
            ),
            ocr_provider=document.ocr_provider,
            extraction_method=document.extraction_method,
            is_demo=document.is_demo,
        )
    finally:
        _clear_buffer(buffer)
