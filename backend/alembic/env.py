# LogRaven — Alembic Environment Configuration
import asyncio
import os
from logging.config import fileConfig
from pathlib import Path
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them
from app.models import Base  # noqa: F401

target_metadata = Base.metadata

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


def _normalize_database_url(url: str) -> str:
    """Match app DB URL; rewrite Docker hostname for host-side alembic runs."""
    url = url.replace("@lograven-db:", "@localhost:")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _load_database_url() -> str:
    if env_url := os.environ.get("DATABASE_URL"):
        return _normalize_database_url(env_url)

    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or not line.startswith("DATABASE_URL="):
                continue
            _, _, value = line.partition("=")
            if value.strip():
                return _normalize_database_url(value.strip())

    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    url = _load_database_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _load_database_url()
    connectable = async_engine_from_config(
        configuration,
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
