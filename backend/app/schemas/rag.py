from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.i18n import Language


class RagQueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=2, max_length=1000)
    language: Language = Language.EN


class RagQueryResponse(BaseModel):
    answer: str
    sources: list[str]
    language: Language
    translation_status: Literal["success", "skipped", "failed"]
