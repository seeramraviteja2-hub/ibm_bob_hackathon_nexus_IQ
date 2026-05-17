"""
NexusIQ — Alembic async env.py
Uses asyncpg + SQLAlchemy async engine so migrations work with the same
DATABASE_URL the app uses. The config.py validator ensures the URL is in
postgresql+asyncpg:// format — alembic reads it from the environment directly.
"""
import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import models so autogenerate can detect them ─────────────────────────────
from db.models import Base  # noqa: E402
target_metadata = Base.metadata

# ── Resolve DATABASE_URL from env (same normalization as config.py) ───────────
def _normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

database_url = _normalize_url(
    os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url", ""))
)

config.set_main_option("sqlalchemy.url", database_url)


# ── Async migration runners ────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (for SQL script output)."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
