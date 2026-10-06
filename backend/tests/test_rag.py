import asyncio
import uuid
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import CurrentUser, get_current_user
from app.db import get_session
from app.main import app
from app.routes import rag as rag_route
from app.services import rag_engine
from app.services.i18n import Language, LocalizedAnswer


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        return None

    async def execute(self, statement: Any) -> None:
        return None


def test_answer_question_returns_expected_shape(monkeypatch) -> None:
    async def fake_search(
        query_embedding: list[float], match_count: int = 5
    ) -> list[tuple[str, str, float]]:
        return [("carry the existing ration card", "ration-card-renewal.md", 0.12)]

    async def fake_llm(question: str, contexts: list[str], system_prompt: str) -> str:
        return "Bring the existing card and proof of residence."

    monkeypatch.setattr(rag_engine, "get_embedding", lambda text: [0.0] * 384)
    monkeypatch.setattr(rag_engine, "similarity_search", fake_search)
    monkeypatch.setattr(rag_engine, "_call_llm", fake_llm)

    result = asyncio.run(
        rag_engine.answer_question("How do I renew a ration card?", "system prompt")
    )

    assert {"answer", "sources", "chunks_used"} <= set(result)
    assert result["answer"] == "Bring the existing card and proof of residence."
    assert result["sources"] == ["ration-card-renewal.md"]
    assert result["chunks_used"] == 1


def test_answer_question_without_relevant_chunks(monkeypatch) -> None:
    async def fake_search(
        query_embedding: list[float], match_count: int = 5
    ) -> list[tuple[str, str, float]]:
        return [("unrelated content", "other.md", 0.95)]

    async def fail_llm(question: str, contexts: list[str], system_prompt: str) -> str:
        raise AssertionError("The LLM must not be called without relevant chunks")

    monkeypatch.setattr(rag_engine, "get_embedding", lambda text: [0.0] * 384)
    monkeypatch.setattr(rag_engine, "similarity_search", fake_search)
    monkeypatch.setattr(rag_engine, "_call_llm", fail_llm)

    result = asyncio.run(rag_engine.answer_question("Unanswerable question"))

    assert result["answer"] == rag_engine.NO_INFO_MESSAGE
    assert result["sources"] == []
    assert result["chunks_used"] == 0


def test_rag_route_response_shape_and_audit_metadata(monkeypatch) -> None:
    fake_session = FakeSession()

    async def override_session() -> Any:
        yield fake_session

    def override_user() -> CurrentUser:
        return CurrentUser(id=str(uuid.uuid4()), role="citizen", is_mock=True)

    def override_settings() -> Settings:
        return Settings(database_url="postgresql+asyncpg://u:p@localhost/db")

    async def fake_answer_in_language(
        question: str,
        language: Language,
        *,
        translator: Any,
        answer_fn: Any,
        strategy: str,
    ) -> LocalizedAnswer:
        return LocalizedAnswer(
            answer="Bring the existing ration card.",
            sources=["ration-card-renewal.md"],
            language=Language.EN,
            translation_status="skipped",
        )

    monkeypatch.setattr(rag_route, "answer_in_language", fake_answer_in_language)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[rag_route.get_settings] = override_settings

    try:
        client = TestClient(app)
        response = client.post(
            "/api/rag/query", json={"question": "secret question text"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Bring the existing ration card."
    assert body["sources"] == ["ration-card-renewal.md"]
    assert body["language"] == "en"
    assert body["translation_status"] == "skipped"

    assert len(fake_session.added) == 1
    audit = fake_session.added[0]
    assert audit.action == "rag_query"
    assert audit.metadata_ == {
        "chunks_used": 1,
        "language": "en",
        "translation_status": "skipped",
    }

    serialized_metadata = str(audit.metadata_)
    assert "secret question text" not in serialized_metadata
    assert "Bring the existing ration card" not in serialized_metadata
