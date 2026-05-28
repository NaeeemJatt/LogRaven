"""Create the lograven database if it does not exist (local Postgres dev helper)."""
import asyncio
import sys
from pathlib import Path

import asyncpg

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


def _load_database_url() -> str:
    if not _ENV_FILE.exists():
        print(f"[ERROR] .env not found at {_ENV_FILE}")
        sys.exit(1)
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            return line.partition("=")[2].strip()
    print("[ERROR] DATABASE_URL not set in .env")
    sys.exit(1)


def _admin_url(database_url: str) -> str:
    """Connect to postgres maintenance DB to run CREATE DATABASE."""
    if "/lograven" in database_url:
        return database_url.rsplit("/", 1)[0] + "/postgres"
    return database_url


async def main() -> None:
    database_url = _load_database_url()
    admin_url = _admin_url(database_url).replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(admin_url, timeout=10)
    exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'lograven'")
    if exists:
        print("Database lograven already exists.")
    else:
        await conn.execute("CREATE DATABASE lograven")
        print("Created database lograven.")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
