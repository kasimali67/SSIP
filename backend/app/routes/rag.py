"""POST /api/rag/query - multilingual wrapper around the existing English RAG engine."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.db import get_session
from app.models.audit_log import AuditLog
from app.schemas.rag import RagQueryRequest, RagQueryResponse
from app.services.i18n import answer_in_language, get_translator
from app.services.llm_client import LLMUnavailable
from app.services.profiles import ensure_profile
from app.services.rag_engine import answer_question

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/query", response_model=RagQueryResponse)
async def query_rag(
    body: RagQueryRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RagQueryResponse:
    try:
        result = await answer_in_language(
            body.question,
            body.language,
            translator=get_translator(settings),
            answer_fn=answer_question,
            strategy=settings.rag_output_strategy,
        )
    except LLMUnavailable as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "The assistant is temporarily unavailable."
        ) from exc

    await ensure_profile(session, user)
    session.add(
        AuditLog(
            profile_id=None if user.is_mock else user.id,
            action="rag_query",
            metadata_={
                "chunks_used": len(result.sources),
                "language": result.language.value,
                "translation_status": result.translation_status,
            },
        )
    )
    await session.commit()
    return RagQueryResponse(
        answer=result.answer,
        sources=result.sources,
        language=result.language,
        translation_status=result.translation_status,
    )
