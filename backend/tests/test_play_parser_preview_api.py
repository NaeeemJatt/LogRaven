# Tests — PlayParser POST /preview

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


def test_preview_syslog_parser(client_authed):
    client, _ = client_authed
    body = (
        b"Jan  2 12:00:00 web01 sshd[1234]: Failed password for root from 192.0.2.1 port 22 ssh2\n"
    )
    files = {"file": ("sample.log", io.BytesIO(body), "text/plain")}
    data = {"preview_target": "syslog", "line_limit": "10"}
    r = client.post("/api/v1/play-parser/preview", files=files, data=data)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["preview_kind"] == "parser"
    assert p["key"] == "syslog"
    assert len(p["rows"]) >= 1
    assert p["rows"][0]["line_no"] == 1
    assert "Failed password" in p["rows"][0]["raw"]
    assert p["rows"][0]["parsed"] is not None


def test_preview_decoder_unreachable_note(client_authed, monkeypatch):
    async def _no_mgr():
        return False

    monkeypatch.setattr(
        "app.api.play_parser.routes.decoder_manager_is_healthy_cached",
        _no_mgr,
    )
    client, _ = client_authed
    body = b"Jan  2 12:00:00 h test: hello\n"
    files = {"file": ("s.log", io.BytesIO(body), "text/plain")}
    data = {"preview_target": "decoder", "source_type": "linux_endpoint", "line_limit": "5"}
    r = client.post("/api/v1/play-parser/preview", files=files, data=data)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["preview_kind"] == "decoder"
    assert p["rows"] == []
    assert p["note"]


def test_evaluate_compare_decoders_only_empty_parser_keys(client_authed, monkeypatch):
    async def _no_mgr():
        return False

    monkeypatch.setattr(
        "app.api.play_parser.routes.decoder_manager_is_healthy_cached",
        _no_mgr,
    )
    client, _ = client_authed
    body = b"Jan  2 12:00:00 h test: x\n"
    files = {"file": ("s.log", io.BytesIO(body), "text/plain")}
    data = {
        "parser_keys": "[]",
        "source_type": "linux_endpoint",
        "play_mode": "decoders_only",
        "include_decoders": "true",
    }
    r = client.post("/api/v1/play-parser/evaluate-compare", files=files, data=data)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["parser_results"] == []
    assert payload["decoders"]["manager_reachable"] is False


def test_evaluate_compare_parsers_only_skips_decoders(client_authed, monkeypatch):
    calls = {"n": 0}

    async def _count_mgr():
        calls["n"] += 1
        return False

    monkeypatch.setattr(
        "app.api.play_parser.routes.decoder_manager_is_healthy_cached",
        _count_mgr,
    )
    client, _ = client_authed
    body = b"Jan  2 12:00:00 web01 sshd[1]: test\n"
    files = {"file": ("s.log", io.BytesIO(body), "text/plain")}
    data = {
        "parser_keys": '["syslog"]',
        "source_type": "linux_endpoint",
        "include_decoders": "true",
        "play_mode": "parsers_only",
    }
    r = client.post("/api/v1/play-parser/evaluate-compare", files=files, data=data)
    assert r.status_code == 200, r.text
    assert calls["n"] == 0
    payload = r.json()
    assert len(payload["parser_results"]) == 1
    assert payload["parser_results"][0]["parser_key"] == "syslog"
