"""
LogRaven — Database utility script for Windows development.

Replaces all psql commands. Uses asyncpg directly — no psql, no more.com.
Reads DATABASE_URL from the .env file at the project root (LogRaven/.env).

Usage:
    python scripts/db.py tables      — list all tables with row counts
    python scripts/db.py migrations  — show alembic migration state
    python scripts/db.py check       — test connection + print full status
    python scripts/db.py drop        — drop all tables (asks for confirmation)
"""

import asyncio
import sys
import re
from pathlib import Path

# ── Resolve .env from project root (LogRaven/.env) ───────────────────────────

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


def _load_env() -> dict[str, str]:
    """Parse .env file and return key/value pairs."""
    env: dict[str, str] = {}
    if not _ENV_FILE.exists():
        print(f"[ERROR] .env not found at: {_ENV_FILE}")
        sys.exit(1)
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def _get_asyncpg_dsn(database_url: str) -> str:
    """Convert SQLAlchemy-style URL to asyncpg DSN."""
    return re.sub(r"^postgresql(\+asyncpg)?://", "postgresql://", database_url)


# ── ANSI colours (safe on Windows 10+) ──────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
DIM    = "\033[2m"


def _hr(char: str = "-", width: int = 52) -> str:
    return CYAN + char * width + RESET


def _ok(msg: str) -> str:
    return f"{GREEN}✓{RESET} {msg}"


def _fail(msg: str) -> str:
    return f"{RED}✗{RESET} {msg}"


# ── Commands ─────────────────────────────────────────────────────────────────

LOGRAVEN_TABLES = [
    "users",
    "investigations",
    "investigation_files",
    "reports",
    "findings",
    "audit_log",
]


async def show_tables() -> None:
    import asyncpg

    env = _load_env()
    dsn = _get_asyncpg_dsn(env["DATABASE_URL"])

    conn = await asyncpg.connect(dsn)
    try:
        rows = await conn.fetch(
            """
            SELECT
                t.tablename,
                (SELECT COUNT(*) FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_name = t.tablename) AS exists
            FROM pg_tables t
            WHERE t.schemaname = 'public'
            ORDER BY t.tablename;
            """
        )
        counts = {}
        for row in rows:
            tname = row["tablename"]
            try:
                c = await conn.fetchval(f'SELECT COUNT(*) FROM "{tname}"')
                counts[tname] = c
            except Exception:
                counts[tname] = "?"

        print()
        print(_hr())
        print(f"{BOLD}{CYAN}  LogRaven -- Database Tables{RESET}")
        print(_hr())
        print(f"  {'Table':<28} {'Rows':>8}")
        print(f"  {DIM}{'─'*28}  {'─'*8}{RESET}")
        for row in rows:
            t = row["tablename"]
            marker = "  " if t in LOGRAVEN_TABLES else f"{YELLOW}?{RESET} "
            print(f"  {marker}{t:<26} {counts.get(t, '?'):>8}")
        print(_hr())
        print(f"  {DIM}{len(rows)} table(s) total{RESET}")
        print()
    finally:
        await conn.close()


async def show_migrations() -> None:
    import asyncpg

    env = _load_env()
    dsn = _get_asyncpg_dsn(env["DATABASE_URL"])

    conn = await asyncpg.connect(dsn)
    try:
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='alembic_version')"
        )
        print()
        print(_hr())
        print(f"{BOLD}{CYAN}  LogRaven -- Alembic Migrations{RESET}")
        print(_hr())

        if not exists:
            print(f"  {_fail('alembic_version table not found — run: alembic upgrade head')}")
        else:
            rows = await conn.fetch("SELECT version_num FROM alembic_version")
            current = rows[0]["version_num"] if rows else None

            expected = ["001", "002", "003", "004", "005", "006"]
            descriptions = {
                "001": "create users",
                "002": "create investigations",
                "003": "create investigation_files",
                "004": "create reports",
                "005": "create findings",
                "006": "create audit_log",
            }
            for rev in expected:
                desc = descriptions[rev]
                if current and int(current) >= int(rev):
                    status = _ok(f"{rev}  {desc}")
                else:
                    status = _fail(f"{rev}  {desc}  {DIM}(pending){RESET}")
                print(f"  {status}")

            print()
            if current:
                print(f"  {BOLD}Current head:{RESET} {GREEN}{current}{RESET}")
            else:
                print(f"  {RED}No migrations applied.{RESET}")

        print(_hr())
        print()
    finally:
        await conn.close()


async def check_db() -> None:
    import asyncpg

    env = _load_env()
    dsn = _get_asyncpg_dsn(env["DATABASE_URL"])

    print()
    print(_hr("="))
    print(f"{BOLD}{CYAN}  LogRaven -- Database Health Check{RESET}")
    print(_hr("="))
    print(f"  {DIM}DSN: {re.sub(r':([^:@]+)@', ':***@', dsn)}{RESET}")
    print()

    try:
        conn = await asyncpg.connect(dsn)
    except Exception as e:
        print(f"  {_fail(f'Connection FAILED: {e}')}")
        print()
        sys.exit(1)

    try:
        pg_version = await conn.fetchval("SELECT version()")
        print(f"  {_ok('Connection successful')}")
        print(f"  {DIM}{pg_version.split(',')[0]}{RESET}")
        print()

        existing = {
            row["tablename"]
            for row in await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            )
        }

        print(f"  {'Table':<28} {'Status'}")
        print(f"  {DIM}{'─'*28}  {'─'*12}{RESET}")
        all_ok = True
        for t in LOGRAVEN_TABLES:
            if t in existing:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{t}"')
                print(f"  {_ok(f'{t:<26}')}  {DIM}{count} rows{RESET}")
            else:
                print(f"  {_fail(f'{t:<26}')}  {RED}MISSING{RESET}")
                all_ok = False

        print()
        if all_ok:
            print(f"  {GREEN}{BOLD}All tables present. Database layer complete.{RESET}")
        else:
            print(f"  {RED}{BOLD}Some tables missing -- run: alembic upgrade head{RESET}")

    finally:
        await conn.close()

    print(_hr("="))
    print()


async def drop_all() -> None:
    import asyncpg

    env = _load_env()
    dsn = _get_asyncpg_dsn(env["DATABASE_URL"])

    print()
    print(_hr("="))
    print(f"{BOLD}{RED}  LogRaven -- DROP ALL TABLES{RESET}")
    print(_hr("="))
    print(f"  {YELLOW}This will permanently delete all data.{RESET}")
    print(f"  Tables: {', '.join(LOGRAVEN_TABLES + ['alembic_version'])}")
    print()
    confirm = input("  Type YES to confirm: ").strip()
    if confirm != "YES":
        print(f"  {DIM}Aborted.{RESET}")
        print()
        return

    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("SET session_replication_role = replica;")
        drop_order = [
            "findings",
            "reports",
            "investigation_files",
            "investigations",
            "audit_log",
            "users",
            "alembic_version",
        ]
        existing = {
            row["tablename"]
            for row in await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            )
        }
        for t in drop_order:
            if t in existing:
                await conn.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE')
                print(f"  {_ok(f'Dropped: {t}')}")
            else:
                print(f"  {DIM}Skip (not found): {t}{RESET}")

        await conn.execute("SET session_replication_role = DEFAULT;")
        print()
        print(f"  {GREEN}{BOLD}Done. Run 'alembic upgrade head' to recreate.{RESET}")
    finally:
        await conn.close()

    print(_hr("="))
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

COMMANDS = {
    "tables":     show_tables,
    "migrations": show_migrations,
    "check":      check_db,
    "drop":       drop_all,
}

USAGE = f"""
{BOLD}{CYAN}LogRaven db.py -- database utility (no psql required){RESET}

Usage:
  python scripts/db.py {CYAN}tables{RESET}      List all tables with row counts
  python scripts/db.py {CYAN}migrations{RESET}  Show alembic migration state
  python scripts/db.py {CYAN}check{RESET}       Full connection + table health check
  python scripts/db.py {CYAN}drop{RESET}        Drop all tables (asks for confirmation)
"""

if __name__ == "__main__":
    # Enable ANSI colours and UTF-8 output on Windows
    import os
    os.system("")
    # Force UTF-8 on Windows so box-drawing chars print correctly
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(USAGE)
        sys.exit(0)

    asyncio.run(COMMANDS[sys.argv[1]]())
