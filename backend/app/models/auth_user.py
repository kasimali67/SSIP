from sqlalchemy import Column, Table
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

# auth.users is owned by Supabase; we register a minimal reference so that
# Profile.id can declare a ForeignKey to it. It must never be created, altered,
# or dropped by our migrations (excluded in alembic/env.py).
auth_users = Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    schema="auth",
    info={"skip_autogenerate": True},
)
