from pydantic import BaseModel, Field


class OcrField(BaseModel):
    value: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class OcrExtractResponse(BaseModel):
    name: OcrField
    dob: OcrField
    id_number: OcrField
