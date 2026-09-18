from llama_index.embeddings.fastembed import FastEmbedEmbedding

from app.models.document_chunk import EMBEDDING_DIMENSIONS

EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Initialized once per process; never constructed per call.
_embed_model = FastEmbedEmbedding(model_name=EMBED_MODEL_NAME)


def _as_embedding(vector: list[float]) -> list[float]:
    values = [float(value) for value in vector]
    if len(values) != EMBEDDING_DIMENSIONS:
        raise RuntimeError(
            f"Embedding model returned {len(values)} dimensions, "
            f"expected {EMBEDDING_DIMENSIONS}"
        )
    return values


def get_embedding(text: str) -> list[float]:
    return _as_embedding(_embed_model.get_text_embedding(text))


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    return [
        _as_embedding(embedding)
        for embedding in _embed_model.get_text_embedding_batch(texts)
    ]
