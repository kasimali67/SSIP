"""Creates the profile row for a Supabase user on first use.

Needed once AUTH_MODE=supabase: audit_log.profile_id references profile.id,
so a new user's first audited action would otherwise violate the FK.
Requires profile.created_at to have a server default.
"""
from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.models.profile import Profile


async def ensure_profile(session: AsyncSession, user: CurrentUser) -> None:
    if user.is_mock:
        return
    statement = insert(Profile).values(id=user.id, role="citizen").on_conflict_do_nothing(index_elements=[Profile.id])
    await session.execute(statement)
