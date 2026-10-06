"""Pure unit tests: no database, no network, no API keys required."""
from __future__ import annotations

import asyncio

import pytest

from app.services.digilocker.client import DigiLockerError, OfficialRecord, SandboxDigiLockerClient
from app.services.ocr.providers import OcrLine, OcrText
from app.services.structuring import structure_document
from app.services.verification import (
    CrossVerificationService,
    FieldStatus,
    OcrFieldInput,
    OverallStatus,
    Reason,
)


def _record(persona: str) -> OfficialRecord:
    client = SandboxDigiLockerClient(consent_url="http://localhost:3000/digilocker/consent")
    return asyncio.run(client.fetch_record(f"sandbox:{persona}", "verifier", "aadhaar"))


def _verify(persona: str, name: str = "Ramesh Kumar Patel", dob: str = "1985-08-15", last4: str = "4821", conf: float = 0.95):
    service = CrossVerificationService()
    return asyncio.run(
        service.compare(
            name=OcrFieldInput(name, conf),
            dob=OcrFieldInput(dob, conf),
            id_last4=OcrFieldInput(last4, conf),
            record=_record(persona),
        )
    )


def _field(outcome, name: str):
    return next(item for item in outcome.fields if item.field == name)


def test_matching_record_is_verified() -> None:
    assert _verify("match").overall is OverallStatus.VERIFIED


def test_name_initial_needs_review() -> None:
    outcome = _verify("spelling_variant")
    assert _field(outcome, "name").status is FieldStatus.REVIEW
    assert outcome.overall is OverallStatus.NEEDS_REVIEW


def test_dob_mismatch_is_flagged() -> None:
    outcome = _verify("dob_mismatch")
    assert _field(outcome, "dob").reason is Reason.DATE_DIFFERS
    assert outcome.overall is OverallStatus.MISMATCH


def test_year_only_dob_needs_review() -> None:
    assert _field(_verify("match", dob="1985"), "dob").reason is Reason.YEAR_ONLY


def test_day_first_user_edit_is_parsed() -> None:
    assert _field(_verify("match", dob="15/08/1985"), "dob").status is FieldStatus.MATCH


def test_honorific_is_ignored() -> None:
    assert _field(_verify("match", name="Shri Ramesh Kumar Patel"), "name").reason is Reason.EXACT


def test_gujarati_name_without_transliterator_needs_review() -> None:
    assert _field(_verify("match", name="રમેશ કુમાર પટેલ"), "name").reason is Reason.DIFFERENT_SCRIPT


def test_low_confidence_is_reported_but_official_match_wins() -> None:
    name = _field(_verify("match", conf=0.6), "name")
    assert name.status is FieldStatus.MATCH and name.low_ocr_confidence


def test_unknown_sandbox_code_is_rejected() -> None:
    client = SandboxDigiLockerClient(consent_url="http://x")
    with pytest.raises(DigiLockerError):
        asyncio.run(client.fetch_record("forged-code", "verifier", "aadhaar"))


def test_rules_extraction_masks_id_and_normalizes_dob() -> None:
    ocr = OcrText(
        lines=[
            OcrLine("GOVERNMENT OF INDIA", 0.97),
            OcrLine("Ramesh Kumar Patel", 0.93),
            OcrLine("DOB: 15/08/1985", 0.90),
            OcrLine("Male", 0.95),
            OcrLine("2345 6789 4821", 0.96),
        ],
        provider="test",
    )
    doc = asyncio.run(structure_document(ocr, use_llm=False))
    assert doc.id_masked.value == "XXXX-XXXX-4821"
    assert doc.id_last4 == "4821"
    assert doc.dob.value == "1985-08-15"
    assert doc.name.value == "Ramesh Kumar Patel"
    assert doc.gender.value == "M"
    assert "2345" not in repr(doc)
