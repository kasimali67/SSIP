"""migrate document_chunk.embedding to 384 dimensions

Revision ID: 9c1f2ab3d4e5
Revises: 35f016cf814b
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op

revision: str = "9c1f2ab3d4e5"
down_revision: Union[str, None] = "35f016cf814b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_document_chunk_embedding_hnsw"
HNSW_OPTIONS = {
    "postgresql_using": "hnsw",
    "postgresql_ops": {"embedding": "vector_cosine_ops"},
}


def upgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="document_chunk")
    op.execute("ALTER TABLE document_chunk ALTER COLUMN embedding TYPE vector(384)")
    op.create_index(
        INDEX_NAME,
        "document_chunk",
        ["embedding"],
        unique=False,
        **HNSW_OPTIONS,
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="document_chunk")
    op.execute("ALTER TABLE document_chunk ALTER COLUMN embedding TYPE vector(1536)")
    op.create_index(
        INDEX_NAME,
        "document_chunk",
        ["embedding"],
        unique=False,
        **HNSW_OPTIONS,
    )
