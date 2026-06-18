"""Tests for the multi-framework compliance engine.

Covers: per-pack validation, signal vocabulary integrity, PII-free collector
output, the SOC 2 golden-file regression guard, the generic grader's parser,
and the crosswalk helpers.
"""

import pytest

from app.compliance import frameworks as fw
from app.compliance.ai_grader import parse_and_validate, score_results
from app.compliance.constants import SOC2_CONTROLS
from app.compliance.crosswalk import build_crosswalk, reuse_factor
from app.compliance.sanitizer import validate_no_pii
from app.compliance.signals import SIGNAL_CATALOG, build_evidence_signals

EXPECTED_FRAMEWORKS = {
    "soc2", "iso27001", "cis_aws", "pci_dss", "hipaa", "gdpr",
    "nist_csf", "nist_800_53", "fedramp", "csa_ccm", "iso27017", "iso27018",
}


def test_all_expected_frameworks_registered():
    registered = {f.id for f in fw.list_frameworks()}
    assert EXPECTED_FRAMEWORKS.issubset(registered)


@pytest.mark.parametrize("framework", fw.list_frameworks(), ids=lambda f: f.id)
def test_framework_pack_is_valid(framework):
    assert framework.id and framework.name and framework.version
    assert len(framework.controls) > 0

    seen_ids = set()
    for control in framework.controls:
        assert control.control_id, f"{framework.id}: empty control_id"
        assert control.name, f"{framework.id}:{control.control_id} empty name"
        assert control.control_id not in seen_ids, f"{framework.id}: duplicate {control.control_id}"
        seen_ids.add(control.control_id)
        assert isinstance(control.automatable, bool)
        # Every referenced signal must exist in the canonical catalog.
        for signal in control.signals:
            assert signal in SIGNAL_CATALOG, f"{framework.id}:{control.control_id} unknown signal {signal}"


def test_soc2_golden_control_set_unchanged():
    """Regression guard: the SOC 2 pack must match the original 11 controls exactly."""
    soc2 = fw.get_framework("soc2")
    assert {c.control_id for c in soc2.controls} == {c["control_id"] for c in SOC2_CONTROLS}
    assert len(soc2.controls) == len(SOC2_CONTROLS) == 11


def test_signal_builder_handles_missing_sections():
    signals = build_evidence_signals({})
    assert set(signals.keys()) == set(SIGNAL_CATALOG.keys())
    assert all(v is None for v in signals.values())


def test_signal_builder_flattens_extended_sections():
    sanitized = {
        "iam": {"mfa_enforcement_rate_percent": 80.0, "root_mfa_enabled": True, "total_users": 5},
        "guardduty": {"enabled": True, "high_severity_findings": 0},
        "encryption": {"s3_default_encryption_rate": 100.0, "kms_key_rotation_rate": 50.0},
        "network": {"open_security_groups": 2, "default_sg_restricted": True},
        "monitoring": {"config_recorder_enabled": True, "securityhub_enabled": False},
    }
    signals = build_evidence_signals(sanitized)
    assert signals["iam_mfa_enforcement_rate"] == 80.0
    assert signals["iam_root_mfa_enabled"] is True
    assert signals["s3_default_encryption_rate"] == 100.0
    assert signals["open_security_groups"] == 2
    assert signals["config_recorder_enabled"] is True
    assert signals["securityhub_enabled"] is False


def test_extended_collector_output_is_pii_free():
    """Aggregate collector output must pass the strict PII validator."""
    extended_sections = {
        "iam_extended": {"stale_access_keys": 3, "admin_users": 1, "access_analyzer_external_findings": 0},
        "cloudtrail_config": {"multi_region": True, "log_file_validation": True, "kms_encrypted": False},
        "encryption": {
            "s3_default_encryption_rate": 92.5, "s3_public_access_blocked": True,
            "ebs_default_encryption": True, "rds_encryption_rate": 100.0, "kms_key_rotation_rate": 75.0,
        },
        "network": {"vpc_flow_logs_enabled": True, "open_security_groups": 0, "default_sg_restricted": True},
        "monitoring": {
            "config_recorder_enabled": True, "securityhub_enabled": True, "inspector_enabled": False,
            "min_log_retention_days": 365, "security_alarms_configured": True,
        },
        "backup": {"backup_configured": True, "rds_backups_enabled": True},
    }
    # Should not raise.
    validate_no_pii(extended_sections)


@pytest.mark.parametrize("framework", fw.list_frameworks(), ids=lambda f: f.id)
def test_grader_parser_fills_all_controls(framework):
    controls = [c.as_prompt_dict() for c in framework.controls]
    # Model returns nothing useful -> parser must still emit one row per control.
    results = parse_and_validate("[]", controls)
    assert len(results) == len(framework.controls)
    assert {r["control_id"] for r in results} == framework.control_ids()
    assert all(r["status"] in ("PASS", "FAIL", "PARTIAL") for r in results)


def test_score_results_uses_total_denominator():
    results = [{"status": "PASS"}, {"status": "PARTIAL"}]
    score = score_results(results, total=4)
    assert score["pass_count"] == 1
    assert score["partial_count"] == 1
    assert score["score_percent"] == 25.0


def test_crosswalk_links_shared_signals_across_frameworks():
    rows = build_crosswalk(["soc2", "cis_aws"])
    assert rows, "expected shared signals between soc2 and cis_aws"
    # MFA enforcement is shared by both frameworks.
    mfa_row = next((r for r in rows if r["signal"] == "iam_mfa_enforcement_rate"), None)
    assert mfa_row is not None
    assert mfa_row["framework_count"] >= 2

    assert reuse_factor(["soc2", "iso27001", "cis_aws"]) > 1.0
