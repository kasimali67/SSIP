"""OCR text -> structured fields, with confidence computed deterministically.

Design decisions:
1. ID numbers are found locally by regex and reduced to their last 4 digits.
   They are redacted to "[ID]" before any text is sent to the LLM, so the
   full Aadhaar/PAN number never leaves this process.
2. The LLM returns *which OCR line* each value came from. Field confidence is
   that line's OCR confidence, not a number the LLM invents (LLM self-reported
   confidence is not calibrated). If the value is not actually present in the
   cited line, confidence drops to 0.0 and the field is flagged for review.
3. If the LLM is unavailable, rule-based extraction takes over.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.services.llm_client import LLMUnavailable, chat_json
from app.services.ocr.providers import OcrLine, OcrText

LOW_CONFIDENCE_THRESHOLD = 0.75
RULES_PENALTY = 0.8

_AADHAAR_RE = re.compile(r"(?<!\d)(\d{4})[ \-]?(\d{4})[ \-]?(\d{4})(?!\d)")
_PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)
_DATE_RE = re.compile(r"(?<!\d)(\d{2})[/\-.](\d{2})[/\-.](\d{4})(?!\d)")
_YOB_RE = re.compile(r"(?:year\s*of\s*birth|yob|जन्म\s*वर्ष)\D{0,6}(\d{4})", re.IGNORECASE)
_GENDER_WORDS = {
    "MALE": "M", "FEMALE": "F", "TRANSGENDER": "T",
    "पुरुष": "M", "महिला": "F", "પુરુષ": "M", "સ્ત્રી": "F",
}
_HEADER_WORDS = {
    "GOVERNMENT", "INDIA", "AADHAAR", "DOB", "MALE", "FEMALE", "ADDRESS", "INCOME", "TAX",
    "DEPARTMENT", "भारत", "सरकार", "आधार", "ભારત", "સરકાર", "આધાર",
}

ExtractionMethod = Literal["llm", "rules"]


@dataclass(frozen=True)
class ExtractedField:
    value: str | None
    confidence: float

    @property
    def needs_review(self) -> bool:
        return self.value is None or self.confidence < LOW_CONFIDENCE_THRESHOLD


@dataclass(frozen=True)
class StructuredDocument:
    name: ExtractedField
    dob: ExtractedField
    gender: ExtractedField
    id_masked: ExtractedField
    id_last4: str | None
    id_type: Literal["aadhaar", "pan"] | None
    extraction_method: ExtractionMethod
    ocr_provider: str
    is_demo: bool


@dataclass(frozen=True)
class _IdHit:
    line_index: int
    last4: str
    id_type: Literal["aadhaar", "pan"]


class _LlmField(BaseModel):
    value: str | None = None
    line: int | None = None


class _LlmExtraction(BaseModel):
    name: _LlmField = Field(default_factory=_LlmField)
    dob: _LlmField = Field(default_factory=_LlmField)
    gender: _LlmField = Field(default_factory=_LlmField)


_SYSTEM_PROMPT = (
    "You extract fields from OCR text of Indian identity documents. Lines are numbered. "
    "Return ONLY a JSON object with keys name, dob, gender. Each value is an object "
    '{"value": string or null, "line": integer or null}, where line is the number of the '
    "line the value was read from. name: the document holder's full name exactly as printed "
    "(not a father's or husband's name, not the issuing authority). dob: date of birth as "
    "YYYY-MM-DD, or YYYY if only the year is printed. gender: M, F or T. Use null when a "
    "field is not printed. Never guess. ID numbers appear as [ID]; ignore them."
)


def _find_id(lines: list[OcrLine]) -> _IdHit | None:
    for index, line in enumerate(lines):
        aadhaar = _AADHAAR_RE.search(line.text)
        if aadhaar:
            return _IdHit(index, aadhaar.group(3), "aadhaar")
        pan = _PAN_RE.search(line.text)
        if pan:
            return _IdHit(index, pan.group(0).upper()[-4:], "pan")
    return None


def _mask(hit: _IdHit) -> str:
    return f"XXXX-XXXX-{hit.last4}" if hit.id_type == "aadhaar" else f"XXXXXX{hit.last4}"


def _redact(text: str) -> str:
    return _PAN_RE.sub("[ID]", _AADHAAR_RE.sub("[ID]", text))


def _normalize_date(text: str) -> str | None:
    match = _DATE_RE.search(text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    year_only = _YOB_RE.search(text)
    return year_only.group(1) if year_only else None


def _gender_in(line_text: str) -> str | None:
    """Latin words must match whole tokens ("MALE" must not match inside "FEMALE")."""
    tokens = set(line_text.upper().replace(":", " ").replace("/", " ").split())
    for word, code in _GENDER_WORDS.items():
        if (word.isascii() and word in tokens) or (not word.isascii() and word in line_text):
            return code
    return None


def _grounded(value: str, line_text: str, kind: str) -> bool:
    """Reject values the cited line does not actually contain (hallucination guard)."""
    haystack = line_text.casefold()
    if kind == "dob":
        return value[:4] in line_text
    if kind == "gender":
        return _gender_in(line_text) == value.strip().upper()
    tokens = [token for token in re.split(r"\s+", value.casefold()) if token]
    return bool(tokens) and all(token in haystack for token in tokens)


def _field_from_llm(item: _LlmField, lines: list[OcrLine], kind: str) -> ExtractedField:
    if not item.value:
        return ExtractedField(None, 0.0)
    value = item.value.strip()
    if item.line is None or not 0 <= item.line < len(lines):
        return ExtractedField(value, 0.0)
    line = lines[item.line]
    confidence = line.confidence if _grounded(value, line.text, kind) else 0.0
    return ExtractedField(value, round(confidence, 2))


async def _extract_with_llm(lines: list[OcrLine]) -> tuple[ExtractedField, ExtractedField, ExtractedField]:
    numbered = "\n".join(f"{index}: {_redact(line.text)}" for index, line in enumerate(lines))
    raw = await chat_json(_SYSTEM_PROMPT, numbered)
    try:
        parsed = _LlmExtraction.model_validate(raw)
    except ValidationError as exc:
        raise LLMUnavailable("schema_mismatch") from exc
    return (
        _field_from_llm(parsed.name, lines, "name"),
        _field_from_llm(parsed.dob, lines, "dob"),
        _field_from_llm(parsed.gender, lines, "gender"),
    )


def _extract_with_rules(lines: list[OcrLine]) -> tuple[ExtractedField, ExtractedField, ExtractedField]:
    name = ExtractedField(None, 0.0)
    dob = ExtractedField(None, 0.0)
    gender = ExtractedField(None, 0.0)
    for line in lines:
        upper_tokens = set(line.text.upper().replace(":", " ").split())
        if dob.value is None and (normalized := _normalize_date(line.text)):
            dob = ExtractedField(normalized, round(line.confidence * RULES_PENALTY, 2))
        if gender.value is None and (code := _gender_in(line.text)):
            gender = ExtractedField(code, round(line.confidence * RULES_PENALTY, 2))
        is_candidate_name = (
            name.value is None
            and not any(ch.isdigit() for ch in line.text)
            and not upper_tokens & _HEADER_WORDS
            and 2 <= len(line.text.split()) <= 4
        )
        if is_candidate_name:
            name = ExtractedField(line.text.strip(), round(line.confidence * RULES_PENALTY, 2))
    return name, dob, gender


async def structure_document(ocr: OcrText, *, use_llm: bool = True) -> StructuredDocument:
    lines = ocr.lines
    id_hit = _find_id(lines)
    id_field = (
        ExtractedField(_mask(id_hit), lines[id_hit.line_index].confidence)
        if id_hit
        else ExtractedField(None, 0.0)
    )

    method: ExtractionMethod = "rules"
    if use_llm:
        try:
            name, dob, gender = await _extract_with_llm(lines)
            method = "llm"
        except LLMUnavailable:
            name, dob, gender = _extract_with_rules(lines)
    else:
        name, dob, gender = _extract_with_rules(lines)

    return StructuredDocument(
        name=name,
        dob=dob,
        gender=gender,
        id_masked=id_field,
        id_last4=id_hit.last4 if id_hit else None,
        id_type=id_hit.id_type if id_hit else None,
        extraction_method=method,
        ocr_provider=ocr.provider,
        is_demo=ocr.is_demo,
    )
