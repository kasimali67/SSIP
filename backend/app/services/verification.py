"""Cross-verification of OCR fields against an official DigiLocker record.

Pure comparison logic: no database, no network (except an optional injected
transliterator), no logging of values. Callers store only statuses.

Rule of precedence: an exact match with the official record outranks low OCR
confidence (the government record has confirmed the value). Low confidence is
still reported per field so the UI can show it.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Protocol

from rapidfuzz import fuzz

from app.services.digilocker.client import OfficialRecord

LOW_CONFIDENCE_THRESHOLD = 0.75
NAME_MATCH_SCORE = 90.0
NAME_REVIEW_SCORE = 75.0
_HONORIFICS = {"SHRI", "SHREE", "SMT", "KUMARI", "KU", "MR", "MRS", "MS", "DR"}
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")


class FieldStatus(str, Enum):
    MATCH = "match"
    REVIEW = "review"
    MISMATCH = "mismatch"
    MISSING = "missing"


class Reason(str, Enum):
    EXACT = "exact"
    MINOR_SPELLING = "minor_spelling_difference"
    NAME_DIFFERS = "name_differs"
    DIFFERENT_SCRIPT = "different_script"
    YEAR_ONLY = "year_only"
    DATE_DIFFERS = "date_differs"
    UNREADABLE_DATE = "unreadable_date"
    ID_DIFFERS = "id_differs"
    NOT_FOUND = "not_found"


class OverallStatus(str, Enum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    MISMATCH = "mismatch"


@dataclass(frozen=True)
class OcrFieldInput:
    value: str | None
    confidence: float


@dataclass(frozen=True)
class FieldComparison:
    field: str
    status: FieldStatus
    reason: Reason
    score: float
    low_ocr_confidence: bool


@dataclass(frozen=True)
class CrossVerificationOutcome:
    overall: OverallStatus
    fields: list[FieldComparison]


class Transliterator(Protocol):
    async def to_latin(self, text: str) -> str | None: ...


def normalize_name(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw).upper()
    text = re.sub(r"[^A-Z0-9\s]", " ", text)
    return " ".join(token for token in text.split() if token not in _HONORIFICS)


def _is_latin(text: str) -> bool:
    return all(ord(char) < 128 for char in text)


def parse_dob(raw: str) -> tuple[date | None, int | None]:
    cleaned = raw.strip()
    if re.fullmatch(r"\d{4}", cleaned):
        return None, int(cleaned)
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(cleaned, fmt).date()  # noqa: DTZ007
        except ValueError:
            continue
        return parsed, parsed.year
    return None, None


class CrossVerificationService:
    def __init__(self, transliterator: Transliterator | None = None) -> None:
        self._transliterator = transliterator

    async def compare(
        self,
        *,
        name: OcrFieldInput,
        dob: OcrFieldInput,
        id_last4: OcrFieldInput,
        record: OfficialRecord,
    ) -> CrossVerificationOutcome:
        fields = [
            await self._compare_name(name, record.name),
            self._compare_dob(dob, record.dob),
            self._compare_id(id_last4, record.id_last4),
        ]
        return CrossVerificationOutcome(overall=self._overall(fields), fields=fields)

    async def _comparable(self, text: str) -> str | None:
        if _is_latin(text):
            return normalize_name(text)
        if self._transliterator is None:
            return None
        latin = await self._transliterator.to_latin(text)
        return normalize_name(latin) if latin else None

    async def _compare_name(self, ocr: OcrFieldInput, official: str) -> FieldComparison:
        low = ocr.confidence < LOW_CONFIDENCE_THRESHOLD
        if not ocr.value or not ocr.value.strip():
            return FieldComparison("name", FieldStatus.MISSING, Reason.NOT_FOUND, 0.0, low)
        left, right = await self._comparable(ocr.value), await self._comparable(official)
        if not left or not right:
            return FieldComparison("name", FieldStatus.REVIEW, Reason.DIFFERENT_SCRIPT, 0.0, low)
        score = float(fuzz.token_sort_ratio(left, right))
        if score >= NAME_MATCH_SCORE:
            reason = Reason.EXACT if score == 100.0 else Reason.MINOR_SPELLING
            return FieldComparison("name", FieldStatus.MATCH, reason, round(score / 100, 2), low)
        if score >= NAME_REVIEW_SCORE:
            return FieldComparison("name", FieldStatus.REVIEW, Reason.MINOR_SPELLING, round(score / 100, 2), low)
        return FieldComparison("name", FieldStatus.MISMATCH, Reason.NAME_DIFFERS, round(score / 100, 2), low)

    def _compare_dob(self, ocr: OcrFieldInput, official: str) -> FieldComparison:
        low = ocr.confidence < LOW_CONFIDENCE_THRESHOLD
        if not ocr.value or not ocr.value.strip():
            return FieldComparison("dob", FieldStatus.MISSING, Reason.NOT_FOUND, 0.0, low)
        ocr_date, ocr_year = parse_dob(ocr.value)
        official_date, official_year = parse_dob(official)
        if ocr_year is None or official_year is None:
            return FieldComparison("dob", FieldStatus.REVIEW, Reason.UNREADABLE_DATE, 0.0, low)
        if ocr_date and official_date:
            if ocr_date == official_date:
                return FieldComparison("dob", FieldStatus.MATCH, Reason.EXACT, 1.0, low)
            return FieldComparison("dob", FieldStatus.MISMATCH, Reason.DATE_DIFFERS, 0.0, low)
        if ocr_year == official_year:
            return FieldComparison("dob", FieldStatus.REVIEW, Reason.YEAR_ONLY, 0.5, low)
        return FieldComparison("dob", FieldStatus.MISMATCH, Reason.DATE_DIFFERS, 0.0, low)

    def _compare_id(self, ocr: OcrFieldInput, official_last4: str) -> FieldComparison:
        low = ocr.confidence < LOW_CONFIDENCE_THRESHOLD
        digits = re.sub(r"\D", "", ocr.value or "")[-4:]
        if len(digits) != 4:
            return FieldComparison("id_last4", FieldStatus.MISSING, Reason.NOT_FOUND, 0.0, low)
        if digits == official_last4:
            return FieldComparison("id_last4", FieldStatus.MATCH, Reason.EXACT, 1.0, low)
        return FieldComparison("id_last4", FieldStatus.MISMATCH, Reason.ID_DIFFERS, 0.0, low)

    @staticmethod
    def _overall(fields: list[FieldComparison]) -> OverallStatus:
        statuses = {item.status for item in fields}
        if FieldStatus.MISMATCH in statuses:
            return OverallStatus.MISMATCH
        if statuses & {FieldStatus.REVIEW, FieldStatus.MISSING}:
            return OverallStatus.NEEDS_REVIEW
        return OverallStatus.VERIFIED
