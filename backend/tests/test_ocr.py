import asyncio

import pytest

from app.services import ocr_engine
from app.services.ocr import OcrText
from app.services.structuring import ExtractedField, StructuredDocument


def _document(*, is_demo: bool = False, provider: str = "test") -> StructuredDocument:
    return StructuredDocument(
        name=ExtractedField("Ramesh Kumar Patel", 0.93),
        dob=ExtractedField("1985-08-15", 0.90),
        gender=ExtractedField("M", 0.95),
        id_masked=ExtractedField("XXXX-XXXX-4821", 0.96),
        id_last4="4821",
        id_type="aadhaar",
        extraction_method="rules",
        ocr_provider=provider,
        is_demo=is_demo,
    )


@pytest.fixture
def mock_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr_engine, "_preprocess", lambda buffer: b"preprocessed-png")

    async def fake_run_ocr(png: bytes) -> OcrText:
        assert png == b"preprocessed-png"
        return OcrText(lines=[], provider="test")

    async def fake_structure(ocr_text: OcrText) -> StructuredDocument:
        return _document()

    monkeypatch.setattr(ocr_engine, "run_ocr", fake_run_ocr)
    monkeypatch.setattr(ocr_engine, "structure_document", fake_structure)


def test_extract_fields_builds_extended_response(mock_pipeline: None) -> None:
    result = asyncio.run(ocr_engine.extract_fields(b"raw-image-bytes"))

    assert result.name.value == "Ramesh Kumar Patel"
    assert result.dob.value == "1985-08-15"
    assert result.id_number.value == "XXXX-XXXX-4821"
    assert result.gender.value == "M"
    assert result.ocr_provider == "test"
    assert result.extraction_method == "rules"
    assert result.is_demo is False


def test_extract_fields_confidences_in_range(mock_pipeline: None) -> None:
    result = asyncio.run(ocr_engine.extract_fields(b"raw-image-bytes"))

    for field in (result.name, result.dob, result.id_number, result.gender):
        assert 0.0 <= field.confidence <= 1.0


def test_extract_fields_propagates_demo_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr_engine, "_preprocess", lambda buffer: b"preprocessed-png")

    async def fake_run_ocr(png: bytes) -> OcrText:
        return OcrText(lines=[], provider="demo_fixture", is_demo=True)

    async def fake_structure(ocr_text: OcrText) -> StructuredDocument:
        return _document(is_demo=True, provider="demo_fixture")

    monkeypatch.setattr(ocr_engine, "run_ocr", fake_run_ocr)
    monkeypatch.setattr(ocr_engine, "structure_document", fake_structure)

    result = asyncio.run(ocr_engine.extract_fields(b"raw-image-bytes"))

    assert result.is_demo is True
    assert result.ocr_provider == "demo_fixture"


def test_extract_fields_rejects_empty_payload() -> None:
    with pytest.raises(ValueError):
        asyncio.run(ocr_engine.extract_fields(b""))
