import os
import uuid

import httpx
import pytest


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("LOGRAVEN_RUN_INTEGRATION") != "1",
        reason="set LOGRAVEN_RUN_INTEGRATION=1 to use real PostgreSQL and Redis",
    ),
]


@pytest.mark.asyncio
async def test_auth_and_investigation_flow_uses_real_postgres_and_redis():
    from app.main import app

    email = f"integration-{uuid.uuid4()}@example.com"
    password = "integration-password-123"
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        registered = await client.post("/auth/register", json={"email": email, "password": password})
        assert registered.status_code == 201
        assert registered.json()["user"]["email"] == email

        current_user = await client.get("/auth/me")
        assert current_user.status_code == 200
        assert current_user.json()["email"] == email

        created = await client.post("/api/v1/investigations", json={"name": "Integration case"})
        assert created.status_code == 201
        investigation_id = created.json()["id"]
        assert created.json()["queued_at"] is None

        updated = await client.patch(
            f"/api/v1/investigations/{investigation_id}",
            json={"correlation_enabled": False},
        )
        assert updated.status_code == 200
        assert updated.json()["correlation_enabled"] is False

        listed = await client.get("/api/v1/investigations")
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [investigation_id]

        fetched = await client.get(f"/api/v1/investigations/{investigation_id}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Integration case"

        deleted = await client.delete(f"/api/v1/investigations/{investigation_id}")
        assert deleted.status_code == 204

        logged_out = await client.post("/auth/logout")
        assert logged_out.status_code == 200
        assert (await client.get("/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_findings_api_isolates_users_with_real_postgres(postgres_connection):
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client_a,
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client_b,
    ):
        users = []
        investigations = []
        for client, label in ((client_a, "a"), (client_b, "b")):
            registered = await client.post(
                "/auth/register",
                json={
                    "email": f"integration-{label}-{uuid.uuid4()}@example.com",
                    "password": "integration-password-123",
                },
            )
            users.append(registered.json()["user"]["id"])
            created = await client.post(
                "/api/v1/investigations",
                json={"name": f"Tenant {label.upper()} case"},
            )
            investigations.append(created.json()["id"])

        with postgres_connection.cursor() as cursor:
            for index, (user_id, investigation_id) in enumerate(zip(users, investigations, strict=True)):
                report_id = str(uuid.uuid4())
                cursor.execute(
                    """
                    INSERT INTO reports (id, investigation_id, user_id, summary)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (report_id, investigation_id, user_id, "integration"),
                )
                cursor.execute(
                    """
                    INSERT INTO findings (id, report_id, severity, title, description)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        report_id,
                        "high",
                        f"Private finding {index}",
                        "Must remain user-scoped.",
                    ),
                )
        postgres_connection.commit()

        findings_a = (await client_a.get("/api/v1/findings")).json()["items"]
        findings_b = (await client_b.get("/api/v1/findings")).json()["items"]
        assert [item["title"] for item in findings_a] == ["Private finding 0"]
        assert [item["title"] for item in findings_b] == ["Private finding 1"]
