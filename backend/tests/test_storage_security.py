# Tests — upload filename sanitization and storage path resolution

import uuid

import pytest
from fastapi import HTTPException

from app.api.investigations.validators import sanitize_upload_filename
from app.utils.security import (
    create_access_token,
    create_file_download_token,
    create_refresh_token,
    decode_file_download_token,
    decode_token,
)
from app.utils.storage_paths import resolved_file_under_storage_base


class TestSanitizeUploadFilename:
    def test_no_directory_separators(self):
        assert "/" not in sanitize_upload_filename("a/b.log")
        assert "\\" not in sanitize_upload_filename(r"a\b.log")

    def test_basename_only_from_traversal_like_name(self):
        n = sanitize_upload_filename("../../etc/passwd")
        assert ".." not in n
        assert "/" not in n
        assert n == "passwd"

    def test_default_when_empty(self):
        assert sanitize_upload_filename("") == "upload"
        assert sanitize_upload_filename("...") == "upload"


def test_resolved_file_rejects_absolute_key(tmp_path):
    target = tmp_path / "store"
    target.mkdir()
    with pytest.raises(HTTPException) as exc:
        resolved_file_under_storage_base(target, str(tmp_path / "other" / "f.txt"))
    assert exc.value.status_code == 404


def test_file_download_token_roundtrip_includes_owner():
    import app.config as cfg

    uid = str(uuid.uuid4())
    cfg.settings.JWT_SECRET_KEY = "test-secret-key-with-32-characters!"
    cfg.settings.JWT_ALGORITHM = "HS256"
    cfg.settings.JWT_ISSUER = "lograven"
    tok = create_file_download_token("reports/x.pdf", uid)
    key, owner = decode_file_download_token(tok)
    assert key == "reports/x.pdf"
    assert owner == uid


def test_access_token_roundtrip_enforces_issuer_and_audience():
    import app.config as cfg

    uid = str(uuid.uuid4())
    cfg.settings.JWT_SECRET_KEY = "test-secret-key-with-32-characters!"
    cfg.settings.JWT_ALGORITHM = "HS256"
    cfg.settings.JWT_ISSUER = "lograven"
    cfg.settings.JWT_AUDIENCE = "lograven-api"

    tok = create_access_token(uid, "free")
    payload = decode_token(tok)
    assert payload["sub"] == uid
    assert payload["type"] == "access"
    assert payload["iss"] == "lograven"
    assert payload["aud"] == "lograven-api"


def test_refresh_token_roundtrip_contains_unique_jti():
    import app.config as cfg

    uid = str(uuid.uuid4())
    cfg.settings.JWT_SECRET_KEY = "test-secret-key-with-32-characters!"
    cfg.settings.JWT_ALGORITHM = "HS256"
    cfg.settings.JWT_ISSUER = "lograven"
    cfg.settings.JWT_AUDIENCE = "lograven-api"

    tok, jti = create_refresh_token(uid)
    payload = decode_token(tok)
    assert payload["sub"] == uid
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_resolved_file_rejects_parent_escape(tmp_path):
    target = tmp_path / "store"
    target.mkdir()
    (tmp_path / "secret.txt").write_text("x", encoding="utf-8")
    with pytest.raises(HTTPException):
        resolved_file_under_storage_base(target, "../secret.txt")
