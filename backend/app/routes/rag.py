import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.audit_log import AuditLog
from app.routes.ocr import require_profile_id
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_engine import answer_question

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(
    payload: RAGQueryRequest,
    profile_id: Annotated[uuid.UUID, Depends(require_profile_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RAGQueryResponse:
    # TODO(rbac): restrict retrieval to the owning authenticated user once the
    # role/permission layer lands.
    try:
        result = await answer_question(payload.question)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="RAG provider unavailable",
        ) from exc

    session.add(
        AuditLog(
            profile_id=profile_id,
            action="rag_query",
            metadata_={"chunks_used": int(result.get("chunks_used", 0))},
        )
    )
    await session.commit()

    return RAGQueryResponse(
        answer=str(result["answer"]),
        sources=list(result["sources"]),
    )
