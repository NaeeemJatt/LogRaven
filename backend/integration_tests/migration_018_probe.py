"""Seed revision 017 and verify revision 018 preserves investigation rows."""

import argparse
import os
import uuid

import psycopg2


USER_ID = uuid.UUID("10000000-0000-0000-0000-000000000018")
INVESTIGATION_ID = uuid.UUID("20000000-0000-0000-0000-000000000018")


def _connect():
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    return psycopg2.connect(url)


def seed() -> None:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute("DELETE FROM investigations WHERE id = %s", (str(INVESTIGATION_ID),))
        cursor.execute("DELETE FROM users WHERE id = %s", (str(USER_ID),))
        cursor.execute(
            """
            INSERT INTO users (id, email, password_hash, tier, email_verified, name, timezone)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(USER_ID),
                "migration-018@example.com",
                "not-used",
                "free",
                True,
                "Migration Probe",
                "UTC",
            ),
        )
        cursor.execute(
            """
            INSERT INTO investigations (
                id, user_id, name, status, correlation_enabled,
                time_window_start, time_window_end
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(INVESTIGATION_ID),
                str(USER_ID),
                "Migration 018 probe",
                "draft",
                True,
                "2026-01-01T00:00:00",
                "2026-01-02T00:00:00",
            ),
        )


def verify() -> None:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT name, status FROM investigations WHERE id = %s", (str(INVESTIGATION_ID),))
        assert cursor.fetchone() == ("Migration 018 probe", "draft")
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'investigations'
              AND column_name IN ('time_window_start', 'time_window_end')
            """
        )
        assert cursor.fetchall() == []
        cursor.execute("DELETE FROM investigations WHERE id = %s", (str(INVESTIGATION_ID),))
        cursor.execute("DELETE FROM users WHERE id = %s", (str(USER_ID),))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("seed", "verify"))
    args = parser.parse_args()
    seed() if args.action == "seed" else verify()
