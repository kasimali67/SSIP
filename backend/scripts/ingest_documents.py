import asyncio
from pathlib import Path

from llama_index.core.node_parser import SentenceSplitter

from app.db import get_session_factory
from app.models.document_chunk import DocumentChunk
from app.services.embeddings import get_embeddings_batch

BACKEND_DIR = Path(__file__).resolve().parents[1]
CHECKLIST_DIR = BACKEND_DIR / "data" / "checklists"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
BATCH_SIZE = 32


def split_checklists() -> list[tuple[str, str]]:
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks: list[tuple[str, str]] = []
    for path in sorted(CHECKLIST_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for chunk in splitter.split_text(text):
            chunks.append((chunk, path.name))
    return chunks


async def ingest() -> int:
    chunks = split_checklists()
    if not chunks:
        print("No checklist documents found to ingest.")
        return 0

    session_factory = get_session_factory()
    inserted = 0
    async with session_factory() as session:
        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start : start + BATCH_SIZE]
            embeddings = await asyncio.to_thread(
                get_embeddings_batch, [content for content, _ in batch]
            )
            session.add_all(
                [
                    DocumentChunk(content=content, embedding=embedding, source=source)
                    for (content, source), embedding in zip(batch, embeddings)
                ]
            )
            await session.commit()
            inserted += len(batch)
            print(f"Inserted {inserted}/{len(chunks)} chunks")

    return inserted


def main() -> None:
    inserted = asyncio.run(ingest())
    print(f"Ingestion complete: {inserted} chunks")


if __name__ == "__main__":
    main()
