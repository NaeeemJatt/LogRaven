# Tests — PlayParser sandbox API (auth, validation, evaluate response shape)

import io
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app


def _fake_user():
    return SimpleNamespace(id=uuid.uuid4(), tier="free")


@pytest.fixture
def client_authed():
    user = _fake_user()

    async def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    with TestClient(app) as client:
        yield client, user
    app.dependency_overrides.pop(get_current_user, None)


def test_evaluate_syslog_and_nginx_multi_parser_shape(client_authed):
    client, _user = client_authed
    body = (
        b"Jan  2 12:00:00 web01 sshd[1234]: Failed password for root from 192.0.2.1 port 22 ssh2\n"
        b"Jan  2 12:00:01 web01 sudo: pam_unix(sudo:session): session opened for user alice\n"
    )
    files = {"file": ("sample.log", io.BytesIO(body), "text/plain")}
    data = {"parser_keys": '["syslog", "nginx"]'}
    r = client.post("/api/v1/play-parser/evaluate", files=files, data=data)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert "results" in payload
    assert len(payload["results"]) == 2
    keys = {row["parser_key"] for row in payload["results"]}
    assert keys == {"syslog", "nginx"}
    for row in payload["results"]:
        assert "ok" in row
        assert "event_count" in row
        if row["ok"]:
            assert row["quality"] is not None
            q = row["quality"]
            assert "score" in q
            assert "valid_timestamp_ratio" in q
            assert "structured_ratio" in q
            assert "warnings" in q
            assert isinstance(q["score"], (int, float))


def test_evaluate_unknown_parser_400(client_authed):
    client, _ = client_authed
    body = b"hello\n"
    files = {"file": ("x.log", io.BytesIO(body), "text/plain")}
    data = {"parser_keys": '["not_a_parser"]'}
    r = client.post("/api/v1/play-parser/evaluate", files=files, data=data)
    assert r.status_code == 400
    assert "Unknown parser" in (r.json().get("detail") or "")


def test_meta_public_200():
    """Sanity check that the PlayParser router is mounted (no auth)."""
    with TestClient(app) as client:
        r = client.get("/api/v1/play-parser/meta")
    assert r.status_code == 200
    body = r.json()
    assert body.get("service") == "play-parser"
    assert "/evaluate" in str(body.get("endpoints"))
    assert "evaluate-compare" in str(body.get("endpoints"))
    assert "/preview" in str(body.get("endpoints"))


def test_evaluate_compare_shape_decoder_unreachable(client_authed, monkeypatch):
    async def _no_mgr():
        return False

    monkeypatch.setattr(
        "app.api.play_parser.routes.decoder_manager_is_healthy_cached",
        _no_mgr,
    )
    client, _user = client_authed
    body = (
        b"Jan  2 12:00:00 web01 sshd[1234]: Failed password for root from 192.0.2.1 port 22 ssh2\n"
    )
    files = {"file": ("sample.log", io.BytesIO(body), "text/plain")}
    data = {
        "parser_keys": '["syslog"]',
        "source_type": "linux_endpoint",
        "include_decoders": "true",
        "play_mode": "both",
    }
    r = client.post("/api/v1/play-parser/evaluate-compare", files=files, data=data)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert "parser_results" in payload
    assert "decoders" in payload
    assert payload["decoders"]["manager_reachable"] is False
    assert payload["decoders"]["ok"] is False


def test_evaluate_unauthenticated_401():
    app.dependency_overrides.pop(get_current_user, None)
    body = b"Jan  2 12:00:00 h test: msg\n"
    files = {"file": ("s.log", io.BytesIO(body), "text/plain")}
    data = {"parser_keys": '["syslog"]'}
    with TestClient(app) as client:
        r = client.post("/api/v1/play-parser/evaluate", files=files, data=data)
    assert r.status_code == 401
