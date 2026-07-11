"""Seed revision 018 and verify revision 019 queue-time backfill behavior."""

import argparse
import os
import sys
import uuid
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


USER_ID = uuid.UUID("10000000-0000-0000-0000-000000000019")
INVESTIGATION_IDS = {
    "draft": uuid.UUID("20000000-0000-0000-0000-000000000019"),
    "queued": uuid.UUID("30000000-0000-0000-0000-000000000019"),
    "processing": uuid.UUID("40000000-0000-0000-0000-000000000019"),
    "complete": uuid.UUID("50000000-0000-0000-0000-000000000019"),
}


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        from app.config import settings

        url = settings.DATABASE_URL
    url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return psycopg2.connect(url)


def _cleanup(cursor) -> None:
    cursor.execute(
        "DELETE FROM investigations WHERE id = ANY(%s::uuid[])",
        ([str(value) for value in INVESTIGATION_IDS.values()],),
    )
    cursor.execute("DELETE FROM users WHERE id = %s", (str(USER_ID),))


def seed() -> None:
    with _connect() as connection, connection.cursor() as cursor:
        _cleanup(cursor)
        cursor.execute(
            """
            INSERT INTO users (id, email, password_hash, tier, email_verified, name, timezone)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(USER_ID),
                "migration-019@example.com",
                "not-used",
                "free",
                True,
                "Migration Probe",
                "UTC",
            ),
        )
        for status, investigation_id in INVESTIGATION_IDS.items():
            cursor.execute(
                """
                INSERT INTO investigations (
                    id, user_id, name, status, correlation_enabled,
                    created_at, completed_at, error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(investigation_id),
                    str(USER_ID),
                    f"Migration 019 {status}",
                    status,
                    status != "draft",
                    "2025-01-01T00:00:00",
                    "2025-01-02T00:00:00" if status == "complete" else None,
                    f"preserve-{status}",
                ),
            )


def _assert_preserved_rows(cursor) -> dict[str, tuple]:
    cursor.execute(
        """
        SELECT status, name, correlation_enabled, created_at, completed_at, error_message
        FROM investigations
        WHERE id = ANY(%s::uuid[])
        ORDER BY status
        """,
        ([str(value) for value in INVESTIGATION_IDS.values()],),
    )
    rows = {row[0]: row[1:] for row in cursor.fetchall()}
    assert set(rows) == set(INVESTIGATION_IDS)
    for status, row in rows.items():
        name, correlation_enabled, created_at, completed_at, error_message = row
        assert name == f"Migration 019 {status}"
        assert correlation_enabled is (status != "draft")
        assert created_at.isoformat() == "2025-01-01T00:00:00"
        assert (completed_at is not None) is (status == "complete")
        assert error_message == f"preserve-{status}"
    return rows


def verify_upgrade() -> None:
    with _connect() as connection, connection.cursor() as cursor:
        _assert_preserved_rows(cursor)
        cursor.execute(
            """
            SELECT status, queued_at
            FROM investigations
            WHERE id = ANY(%s::uuid[])
            ORDER BY status
            """,
            ([str(value) for value in INVESTIGATION_IDS.values()],),
        )
        queue_times = dict(cursor.fetchall())
        assert queue_times["draft"] is None
        assert queue_times["complete"] is None
        assert queue_times["queued"] is not None
        assert queue_times["processing"] == queue_times["queued"]
        assert queue_times["queued"].year >= 2026

        cursor.execute(
            """
            SELECT indexdef
            FROM pg_indexes
            WHERE tablename = 'investigations'
              AND indexname = 'ix_investigations_status_queued_at'
            """
        )
        index_definition = cursor.fetchone()
        assert index_definition is not None
        assert "(status, queued_at)" in index_definition[0]


def verify_downgrade() -> None:
    with _connect() as connection, connection.cursor() as cursor:
        _assert_preserved_rows(cursor)
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'investigations' AND column_name = 'queued_at'
            """
        )
        assert cursor.fetchone() is None
        cursor.execute(
            """
            SELECT 1
            FROM pg_indexes
            WHERE tablename = 'investigations'
              AND indexname = 'ix_investigations_status_queued_at'
            """
        )
        assert cursor.fetchone() is None
        _cleanup(cursor)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("seed", "verify-upgrade", "verify-downgrade"))
    args = parser.parse_args()
    {
        "seed": seed,
        "verify-upgrade": verify_upgrade,
        "verify-downgrade": verify_downgrade,
    }[args.action]()
