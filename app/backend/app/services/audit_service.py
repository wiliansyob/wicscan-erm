"""Audit logging removed — single-user CISO tool, no audit trail needed."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession


async def log_action(
    db: AsyncSession,
    *,
    org_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    action: str = "",
    entity_type: str = "",
    entity_id: uuid.UUID | None = None,
    entity_snapshot: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    correlation_id: str | None = None,
    details: dict | None = None,
) -> None:
    pass
