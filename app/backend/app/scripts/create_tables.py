"""Run once at startup to ensure all tables exist. Called from entrypoint.sh."""
import asyncio
import subprocess
from sqlalchemy import text
from app.database import Base, engine
from app.models import *  # noqa: F401,F403 — registers all ORM classes


async def _is_alembic_stamped(conn) -> bool:
    try:
        result = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        return result.fetchone() is not None
    except Exception:
        return False


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Base.metadata.create_all(c, checkfirst=True))
        already_stamped = await _is_alembic_stamped(conn)

    if not already_stamped:
        print("Fresh database — stamping Alembic to HEAD to skip DDL re-run...")
        subprocess.run(["alembic", "stamp", "head"], check=True)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
