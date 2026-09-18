import pytest

from app.services import ocr_engine
from app.services.ocr_engine import extract_fields, mask_id_number

VISION_TEXT = (
    "Government of India\n"
    "Name: Asha Kumari\n"
    "DOB: 01/02/1990\n"
    "Aadhaar No: 1234 5678 9012\n"
)


def _detected_text(*, confidence: float = 0.92) -> ocr_engine._DetectedText:
    words = tuple(
        ocr_engine._DetectedWord(text=token, confidence=confidence)
        for token in (
            "Name:",
            "Asha",
            "Kumari",
            "DOB:",
            "01/02/1990",
            "1234",
            "5678",
            "9012",
        )
    )
    return ocr_engine._DetectedText(text=VISION_TEXT, words=words)


@pytest.fixture
def mock_vision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr_engine, "_preprocess", lambda buffer: b"preprocessed")
    monkeypatch.setattr(
        ocr_engine, "_detect_document_text", lambda data: _detected_text()
    )


def test_extract_fields_masks_id_number(mock_vision: None) -> None:
    result = extract_fields(b"raw-image-bytes")

    assert result.id_number.value == "XXXXXXXX9012"


def test_extract_fields_confidence_in_range(mock_vision: None) -> None:
    result = extract_fields(b"raw-image-bytes")

    for field in (result.name, result.dob, result.id_number):
        assert 0.0 <= field.confidence <= 1.0
        assert field.confidence == pytest.approx(0.92)


def test_extract_fields_parses_name_and_dob(mock_vision: None) -> None:
    result = extract_fields(b"raw-image-bytes")

    assert result.name.value == "Asha Kumari"
    assert result.dob.value == "01/02/1990"


def test_confidence_is_clamped_to_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr_engine, "_preprocess", lambda buffer: b"preprocessed")
    monkeypatch.setattr(
        ocr_engine, "_detect_document_text", lambda data: _detected_text(confidence=1.4)
    )

    result = extract_fields(b"raw-image-bytes")

    assert result.id_number.confidence == 1.0


def test_mask_id_number_keeps_last_four() -> None:
    assert mask_id_number("1234 5678 9012") == "XXXXXXXX9012"
    assert mask_id_number("123") == "XXX"
    assert mask_id_number("") == ""


def test_extract_fields_rejects_empty_payload() -> None:
    with pytest.raises(ValueError):
        extract_fields(b"")
