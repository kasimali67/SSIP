"""Async engine and session dependency.

One code path for local Docker Postgres and Supabase. Differences live in .env:
  DB_SSL_REQUIRED=true        -> Supabase (TLS required)
  DB_TRANSACTION_POOLER=true  -> Supabase port 6543 (no prepared statements)
Prefer Supabase's *Session* pooler (port 5432) and leave the second flag off.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


def _connect_args() -> dict[str, Any]:
    settings = get_settings()
    args: dict[str, Any] = {}
    if settings.db_ssl_required:
        args["ssl"] = "require"
    if settings.db_transaction_pooler:
        # PgBouncer transaction mode cannot keep prepared statements between transactions.
        args["statement_cache_size"] = 0
        args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid4()}__"
    return args


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    if settings.db_transaction_pooler:
        return create_async_engine(
            settings.database_url, poolclass=NullPool, connect_args=_connect_args()
        )
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args=_connect_args(),
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


# Backwards-compatible alias for callers that use the previous name.
get_session_factory = get_sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
