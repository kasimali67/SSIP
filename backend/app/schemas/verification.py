from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FieldIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    value: str | None = Field(default=None, max_length=120)
    confidence: float = Field(ge=0.0, le=1.0)


class IdLast4In(BaseModel):
    value: str | None = Field(default=None, pattern=r"^\d{4}$")
    confidence: float = Field(ge=0.0, le=1.0)


class OcrFieldsIn(BaseModel):
    name: FieldIn
    dob: FieldIn
    id_last4: IdLast4In


class DigiLockerStartRequest(BaseModel):
    document_type: Literal["aadhaar"] = "aadhaar"


class DigiLockerStartResponse(BaseModel):
    authorization_url: str
    state: str
    is_sandbox: bool


class DigiLockerCompleteRequest(BaseModel):
    code: str = Field(min_length=1, max_length=512)
    state: str = Field(pattern=r"^[A-Za-z0-9_\-]{20,128}$")
    fields: OcrFieldsIn


class FieldComparisonOut(BaseModel):
    field: Literal["name", "dob", "id_last4"]
    status: Literal["match", "review", "mismatch", "missing"]
    reason: str
    score: float
    low_ocr_confidence: bool
    document_value: str | None
    official_value: str | None


class CrossVerificationResponse(BaseModel):
    overall: Literal["verified", "needs_review", "mismatch"]
    fields: list[FieldComparisonOut]
    issuer: str
    is_sandbox: bool
