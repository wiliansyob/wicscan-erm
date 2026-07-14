import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config

if config.config_file_name:
    fileConfig(config.config_file_name)

# Build sync URL from env (replace asyncpg driver with psycopg2)
database_url = os.environ.get("DATABASE_URL", "")
if database_url.startswith("postgresql+asyncpg"):
    database_url = database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
elif database_url.startswith("postgresql://"):
    pass  # already a sync URL
config.set_main_option("sqlalchemy.url", database_url)

# Import all models so Alembic sees the complete metadata graph
from app.database import Base  # noqa: E402
from app.models import *  # noqa: F401,F403,E402  — includes all module models via __init__.py
from app.modules.admin.catalog.models import *  # noqa: F401,F403,E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
