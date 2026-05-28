"""Inspect local Postgres for LogRaven-related databases and row counts."""
import asyncio
import asyncpg

ADMIN = "postgresql://postgres:password@localhost:5432/postgres"


async def inspect_db(dbname: str) -> None:
    try:
        conn = await asyncpg.connect(f"postgresql://postgres:password@localhost:5432/{dbname}", timeout=5)
    except Exception as e:
        print(f"  {dbname}: cannot connect — {e}")
        return

    tables = await conn.fetch(
        """
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
        """
    )
    if not tables:
        print(f"  {dbname}: (no public tables)")
        await conn.close()
        return

    print(f"  {dbname}:")
    for t in tables:
        name = t["tablename"]
        try:
            count = await conn.fetchval(f'SELECT COUNT(*) FROM "{name}"')
            print(f"    {name:30} {count} rows")
        except Exception:
            print(f"    {name:30} (count failed)")
    await conn.close()


async def main() -> None:
    conn = await asyncpg.connect(ADMIN, timeout=5)
    dbs = await conn.fetch(
        """
        SELECT datname, pg_size_pretty(pg_database_size(datname)) AS size
        FROM pg_database WHERE datistemplate = false ORDER BY datname
        """
    )
    print("=== All local Postgres databases ===")
    for r in dbs:
        print(f"  {r['datname']:30} {r['size']}")
    await conn.close()

    print("\n=== Tables with data (LogRaven-like DBs) ===")
    for r in dbs:
        name = r["datname"]
        if name in ("postgres", "template0", "template1"):
            continue
        await inspect_db(name)


if __name__ == "__main__":
    asyncio.run(main())
