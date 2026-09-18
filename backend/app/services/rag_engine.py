from typing import Any

import httpx
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.db import get_session_factory
from app.models.document_chunk import DocumentChunk
from app.services.embeddings import get_embedding

DEFAULT_MATCH_COUNT = 5
MAX_COSINE_DISTANCE = 0.6
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "deepseek/deepseek-chat"
NO_INFO_MESSAGE = (
    "No information is available in the indexed checklists to answer this question."
)
SYSTEM_PROMPT = (
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
    return [
        (row.content, row.source, float(row.distance))
        for row in rows
    ]


async def _call_openrouter(question: str, contexts: list[str]) -> str:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    joined = "\n\n---\n\n".join(contexts)
    payload: dict[str, Any] = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{joined}\n\nQuestion: {question}"},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
        response.raise_for_status()

    choices = response.json().get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter returned no choices")
    return str(choices[0]["message"]["content"]).strip()


async def answer_question(question: str) -> dict[str, Any]:
    embedding = await run_in_threadpool(get_embedding, question)
    matches = await similarity_search(embedding)
    relevant = [match for match in matches if match[2] <= MAX_COSINE_DISTANCE]

    if not relevant:
        return {"answer": NO_INFO_MESSAGE, "sources": [], "chunks_used": 0}

    answer = await _call_openrouter(question, [match[0] for match in relevant])

    sources: list[str] = []
    for _, source, _ in relevant:
        if source not in sources:
            sources.append(source)

    return {"answer": answer, "sources": sources, "chunks_used": len(relevant)}
