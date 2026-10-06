from typing import Any

from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.db import get_session_factory
from app.models.document_chunk import DocumentChunk
from app.services.embeddings import get_embedding
from app.services.llm_client import chat_text

DEFAULT_MATCH_COUNT = 5
MAX_COSINE_DISTANCE = 0.6
NO_INFO_MESSAGE = (
    "No information is available in the indexed checklists to answer this question."
)
DEFAULT_SYSTEM_PROMPT = (
    "You answer questions using only the provided context about Indian government "
    "form applications. If the context does not contain the answer, state that the "
    "information is not available. Never invent details."
)


async def similarity_search(
    query_embedding: list[float],
    match_count: int = DEFAULT_MATCH_COUNT,
) -> list[tuple[str, str, float]]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    statement = (
        select(
            DocumentChunk.content,
            DocumentChunk.source,
            distance.label("distance"),
        )
        .order_by(distance)
        .limit(match_count)
    )
    async with get_session_factory()() as session:
        rows = (await session.execute(statement)).all()
    return [(row.content, row.source, float(row.distance)) for row in rows]


async def _call_llm(question: str, contexts: list[str], system_prompt: str) -> str:
    joined = "\n\n---\n\n".join(contexts)
    user = f"Context:\n{joined}\n\nQuestion: {question}"
    return await chat_text(system_prompt, user)


async def answer_question(
    question: str,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    embedding = await run_in_threadpool(get_embedding, question)
    matches = await similarity_search(embedding)
    relevant = [match for match in matches if match[2] <= MAX_COSINE_DISTANCE]

    if not relevant:
        return {"answer": NO_INFO_MESSAGE, "sources": [], "chunks_used": 0}

    answer = await _call_llm(
        question,
        [match[0] for match in relevant],
        system_prompt or DEFAULT_SYSTEM_PROMPT,
    )

    sources: list[str] = []
    for _, source, _ in relevant:
        if source not in sources:
            sources.append(source)

    return {"answer": answer, "sources": sources, "chunks_used": len(relevant)}
