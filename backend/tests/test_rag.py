import asyncio
import uuid
from typing import Any

from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.routes import rag as rag_route
from app.routes.ocr import require_profile_id
from app.services import rag_engine

PROFILE_ID = uuid.uuid4()


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        return None


def test_answer_question_returns_expected_shape(monkeypatch) -> None:
    async def fake_search(
        query_embedding: list[float], match_count: int = 5
    ) -> list[tuple[str, str, float]]:
        return [("carry the existing ration card", "ration-card-renewal.md", 0.12)]

    async def fake_openrouter(question: str, contexts: list[str]) -> str:
        return "Bring the existing card and proof of residence."

    monkeypatch.setattr(rag_engine, "get_embedding", lambda text: [0.0] * 384)
    monkeypatch.setattr(rag_engine, "similarity_search", fake_search)
    monkeypatch.setattr(rag_engine, "_call_openrouter", fake_openrouter)

    result = asyncio.run(rag_engine.answer_question("How do I renew a ration card?"))

    assert {"answer", "sources", "chunks_used"} <= set(result)
    assert result["answer"] == "Bring the existing card and proof of residence."
    assert result["sources"] == ["ration-card-renewal.md"]
    assert result["chunks_used"] == 1


def test_answer_question_without_relevant_chunks(monkeypatch) -> None:
    async def fake_search(
        query_embedding: list[float], match_count: int = 5
    ) -> list[tuple[str, str, float]]:
        return [("unrelated content", "other.md", 0.95)]

    async def fail_openrouter(question: str, contexts: list[str]) -> str:
        raise AssertionError("OpenRouter must not be called without relevant chunks")

    monkeypatch.setattr(rag_engine, "get_embedding", lambda text: [0.0] * 384)
    monkeypatch.setattr(rag_engine, "similarity_search", fake_search)
    monkeypatch.setattr(rag_engine, "_call_openrouter", fail_openrouter)

    result = asyncio.run(rag_engine.answer_question("Unanswerable question"))

    assert result["answer"] == rag_engine.NO_INFO_MESSAGE
    assert result["sources"] == []
    assert result["chunks_used"] == 0


def test_rag_route_response_shape_and_audit_metadata(monkeypatch) -> None:
    fake_session = FakeSession()

    async def override_session() -> Any:
        yield fake_session

    async def override_profile_id() -> uuid.UUID:
        return PROFILE_ID

    async def fake_answer(question: str) -> dict[str, Any]:
        return {
            "answer": "Bring the existing ration card.",
            "sources": ["ration-card-renewal.md"],
            "chunks_used": 2,
        }

    monkeypatch.setattr(rag_route, "answer_question", fake_answer)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[require_profile_id] = override_profile_id

    try:
        client = TestClient(app)
        response = client.post(
            "/api/rag/query", json={"question": "secret question text"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"answer", "sources"}
    assert body["answer"] == "Bring the existing ration card."
    assert body["sources"] == ["ration-card-renewal.md"]

    assert len(fake_session.added) == 1
    audit = fake_session.added[0]
    assert audit.action == "rag_query"
    assert audit.metadata_ == {"chunks_used": 2}

    serialized_metadata = str(audit.metadata_)
    assert "secret question text" not in serialized_metadata
    assert "Bring the existing ration card" not in serialized_metadata
