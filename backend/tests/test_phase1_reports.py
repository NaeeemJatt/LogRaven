# Tests — Phase 1: Reports API
# Tests pure helper functions and Pydantic schemas only.
# No DB, no Redis, no running server required.

import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
import sys, os

# ── Make app importable without installing the package ───────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Patch settings import so pydantic-settings doesn't need a real .env
from unittest.mock import patch
import types


# ---------------------------------------------------------------------------
# Helpers for building mock ORM objects
# ---------------------------------------------------------------------------

def _make_finding(**kwargs):
    f = MagicMock()
    f.id               = kwargs.get("id",               uuid.uuid4())
    f.severity         = kwargs.get("severity",         "high")
    f.title            = kwargs.get("title",            "Test finding")
    f.description      = kwargs.get("description",      "Something bad happened.")
    f.mitre_technique_id   = kwargs.get("mitre_technique_id",   "T1059.001")
    f.mitre_technique_name = kwargs.get("mitre_technique_name", "PowerShell")
    f.mitre_tactic     = kwargs.get("mitre_tactic",     "Execution")
    f.iocs             = kwargs.get("iocs",             ["185.1.2.3"])
    f.remediation      = kwargs.get("remediation",      "Block the IP.")
    f.finding_type     = kwargs.get("finding_type",     "single")
    f.source_files     = kwargs.get("source_files",     [])
    f.confidence       = kwargs.get("confidence",       0.9)
    return f


def _make_report(**kwargs):
    r = MagicMock()
    r.id               = kwargs.get("id",               uuid.uuid4())
    r.user_id          = kwargs.get("user_id",          uuid.uuid4())
    r.investigation_id = kwargs.get("investigation_id", uuid.uuid4())
    r.summary          = kwargs.get("summary",          "Analysis complete.")
    r.severity_counts  = kwargs.get("severity_counts",  {"high": 1})
    r.mitre_techniques = kwargs.get("mitre_techniques", ["T1059.001"])
    r.correlated_findings    = kwargs.get("correlated_findings",    [])
    r.single_source_findings = kwargs.get("single_source_findings", [])
    r.pdf_storage_key  = kwargs.get("pdf_storage_key",  None)
    r.created_at       = kwargs.get("created_at",       datetime(2025, 1, 15, 10, 30, 0))
    return r


def _make_storage(base_url="http://localhost:8000"):
    s = MagicMock()
    s.get_download_url = lambda key: f"{base_url}/files/{key}"
    return s


# ---------------------------------------------------------------------------
# Phase 1a: build_report_response
# ---------------------------------------------------------------------------

class TestBuildReportResponse:

    def setup_method(self):
        from app.api.reports.helpers import build_report_response
        self.fn = build_report_response

    def test_returns_correct_top_level_keys(self):
        report = _make_report()
        result = self.fn(report, [])
        expected_keys = {
            "id", "investigation_id", "summary", "severity_counts",
            "mitre_techniques", "correlated_findings", "single_source_findings",
            "findings", "created_at",
        }
        assert set(result.keys()) == expected_keys

    def test_ids_serialized_as_strings(self):
        rid = uuid.uuid4()
        inv_id = uuid.uuid4()
        report = _make_report(id=rid, investigation_id=inv_id)
        result = self.fn(report, [])
        assert result["id"] == str(rid)
        assert result["investigation_id"] == str(inv_id)

    def test_created_at_is_iso_string(self):
        report = _make_report()
        result = self.fn(report, [])
        assert isinstance(result["created_at"], str)
        # Should be parseable as datetime
        datetime.fromisoformat(result["created_at"])

    def test_empty_findings_returns_empty_list(self):
        report = _make_report()
        result = self.fn(report, [])
        assert result["findings"] == []

    def test_findings_serialized_correctly(self):
        fid = uuid.uuid4()
        finding = _make_finding(id=fid, severity="critical", confidence=0.95)
        report = _make_report()
        result = self.fn(report, [finding])

        assert len(result["findings"]) == 1
        f = result["findings"][0]
        assert f["id"] == str(fid)
        assert f["severity"] == "critical"
        assert f["confidence"] == 0.95
        assert f["mitre_technique_id"] == "T1059.001"
        assert f["iocs"] == ["185.1.2.3"]

    def test_multiple_findings_preserved(self):
        findings = [_make_finding(severity=s) for s in ("critical", "high", "medium")]
        report = _make_report()
        result = self.fn(report, findings)
        assert len(result["findings"]) == 3
        severities = [f["severity"] for f in result["findings"]]
        assert severities == ["critical", "high", "medium"]

    def test_null_pdf_key_not_in_response(self):
        report = _make_report(pdf_storage_key=None)
        result = self.fn(report, [])
        # pdf_storage_key is a model field, not included in response shape
        assert "pdf_storage_key" not in result

    def test_none_severity_counts_defaults_to_empty_dict(self):
        report = _make_report(severity_counts=None)
        result = self.fn(report, [])
        assert result["severity_counts"] == {}

    def test_none_mitre_techniques_defaults_to_empty_list(self):
        report = _make_report(mitre_techniques=None)
        result = self.fn(report, [])
        assert result["mitre_techniques"] == []


# ---------------------------------------------------------------------------
# Phase 1b: build_download_response
# ---------------------------------------------------------------------------

class TestBuildDownloadResponse:

    def setup_method(self):
        from app.api.reports.helpers import build_download_response
        self.fn = build_download_response

    def test_returns_none_when_no_pdf(self):
        report = _make_report(pdf_storage_key=None)
        storage = _make_storage()
        assert self.fn(report, storage) is None

    def test_returns_dict_when_pdf_key_set(self):
        report = _make_report(pdf_storage_key="reports/inv123/lograven-report-abc.pdf")
        storage = _make_storage()
        result = self.fn(report, storage)
        assert result is not None
        assert "download_url" in result
        assert "filename" in result
        assert "expires_in" in result

    def test_download_url_local_uses_signed_api_path(self):
        key = "reports/inv123/lograven-report-abc.pdf"
        report = _make_report(pdf_storage_key=key)
        storage = _make_storage()
        import app.config as cfg

        cfg.settings.STORAGE_BACKEND = "local"
        cfg.settings.JWT_SECRET_KEY = "test-secret-key-with-32-characters!"
        cfg.settings.JWT_ALGORITHM = "HS256"
        cfg.settings.JWT_ISSUER = "lograven"
        result = self.fn(report, storage)
        assert result["download_url"].startswith("/api/v1/downloads/file?token=")

    def test_download_url_s3_uses_storage_presign(self):
        key = "reports/inv123/lograven-report-abc.pdf"
        report = _make_report(pdf_storage_key=key)
        storage = _make_storage(base_url="http://localhost:8000")
        import app.config as cfg

        cfg.settings.STORAGE_BACKEND = "s3"
        try:
            result = self.fn(report, storage)
        finally:
            cfg.settings.STORAGE_BACKEND = "local"
        assert result["download_url"] == f"http://localhost:8000/files/{key}"

    def test_filename_contains_report_id_prefix(self):
        rid = uuid.UUID("12345678-0000-0000-0000-000000000000")
        report = _make_report(id=rid, pdf_storage_key="some/key.pdf")
        storage = _make_storage()
        result = self.fn(report, storage)
        assert "12345678" in result["filename"]
        assert result["filename"].endswith(".pdf")

    def test_expires_in_matches_backend(self):
        report = _make_report(pdf_storage_key="some/key.pdf")
        storage = _make_storage()
        import app.config as cfg

        cfg.settings.STORAGE_BACKEND = "local"
        cfg.settings.JWT_SECRET_KEY = "test-secret-key-with-32-characters!"
        cfg.settings.JWT_ALGORITHM = "HS256"
        cfg.settings.JWT_ISSUER = "lograven"
        result = self.fn(report, storage)
        assert result["expires_in"] == 15 * 60

        cfg.settings.STORAGE_BACKEND = "s3"
        cfg.settings.S3_DOWNLOAD_URL_EXPIRE_SECONDS = 900
        try:
            result_s3 = self.fn(report, storage)
        finally:
            cfg.settings.STORAGE_BACKEND = "local"
        assert result_s3["expires_in"] == 900


# ---------------------------------------------------------------------------
# Phase 1c: Pydantic schema validation
# ---------------------------------------------------------------------------

class TestFindingSchema:

    def setup_method(self):
        from app.schemas.report import FindingSchema
        self.Schema = FindingSchema

    def test_valid_finding_parses(self):
        data = {
            "severity": "high",
            "title": "Suspicious PowerShell",
            "description": "PowerShell executed encoded command.",
            "mitre_technique_id": "T1059.001",
            "mitre_technique_name": "PowerShell",
            "mitre_tactic": "Execution",
            "iocs": ["185.1.2.3"],
            "remediation": "Block IP.",
            "finding_type": "single",
            "confidence": 0.9,
        }
        f = self.Schema(**data)
        assert f.severity == "high"
        assert f.confidence == 0.9

    def test_optional_id_defaults_to_none(self):
        data = {
            "severity": "low",
            "title": "Test",
            "description": "Desc",
            "finding_type": "single",
        }
        f = self.Schema(**data)
        assert f.id is None

    def test_confidence_defaults_to_0_8(self):
        data = {
            "severity": "low",
            "title": "Test",
            "description": "Desc",
            "finding_type": "single",
        }
        f = self.Schema(**data)
        assert f.confidence == 0.8

    def test_iocs_defaults_to_empty_list(self):
        data = {
            "severity": "low",
            "title": "Test",
            "description": "Desc",
            "finding_type": "single",
        }
        f = self.Schema(**data)
        assert f.iocs == []


class TestDownloadResponse:

    def setup_method(self):
        from app.schemas.report import DownloadResponse
        self.Schema = DownloadResponse

    def test_valid_response(self):
        d = self.Schema(download_url="http://example.com/file.pdf", filename="report.pdf")
        assert d.expires_in == 86400
        assert d.filename == "report.pdf"

    def test_filename_is_optional(self):
        d = self.Schema(download_url="http://example.com/file.pdf")
        assert d.filename is None


# ---------------------------------------------------------------------------
# Phase 1d: Router import sanity — ensures the wired-up router.py doesn't
# crash on import (catches typos, missing imports, etc.)
# We mock settings to avoid needing a real .env
# ---------------------------------------------------------------------------

class TestRouterImport:

    def test_reports_helpers_importable(self):
        from app.api.reports.helpers import build_report_response, build_download_response
        assert callable(build_report_response)
        assert callable(build_download_response)

    def test_reports_routes_importable(self):
        from app.api.reports.routes import router
        assert router is not None

    def test_downloads_routes_importable(self):
        from app.api.downloads.routes import router
        assert router is not None

    def test_schemas_importable(self):
        from app.schemas.report import FindingSchema, ReportResponse, DownloadResponse
        assert FindingSchema is not None
        assert ReportResponse is not None
        assert DownloadResponse is not None
