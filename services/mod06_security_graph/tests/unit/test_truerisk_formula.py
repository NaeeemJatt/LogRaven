"""Unit tests for TrueRisk Composite Prioritization Equation (TC-MOD6-003, PRD-MOD-06)."""

import pytest
from services.mod06_security_graph.internal.truerisk_engine.calculator import (
    TrueRiskCalculator,
    TrueRiskInputs,
)


def test_tc_mod6_003_internal_asset_critical_cve_deprioritized():
    """TC-MOD6-003: Asset with Critical IOM (S_IOM=100), Internal Network (E_reach=25),
    No Admin (I_blast=0), No PII (D_sens=0), No IOA (T_active=0).
    
    Expected Pass Criteria:
    TrueRisk formula computes exactly: 0.25(100) + 0.25(25) + 0 = 31.25.
    Score rounds to 31, categorized as Medium risk (deprioritized despite Critical CVE).
    """
    inputs = TrueRiskInputs(
        s_iom=100.0,
        e_reach=25.0,
        i_blast=0.0,
        d_sens=0.0,
        t_active=0.0,
    )

    exact_score = TrueRiskCalculator.compute_score(inputs)
    assert exact_score == 31.25, f"Expected exactly 31.25, got {exact_score}"

    evaluation = TrueRiskCalculator.evaluate(
        custom_s_iom=100.0,
        custom_e_reach=25.0,
        custom_i_blast=0.0,
        custom_d_sens=0.0,
        custom_t_active=0.0,
    )

    assert evaluation["truerisk_score"] == 31
    assert evaluation["risk_tier"] == "MEDIUM"


def test_maximum_risk_toxic_crown_jewel():
    """Verifies that an asset exposed to Internet with Admin Role and Crown Jewel hits Critical (100)."""
    evaluation = TrueRiskCalculator.evaluate(
        misconfig_severity="CRITICAL",  # 100
        network_exposure="DIRECT_INTERNET",  # 100
        identity_role="ADMIN",  # 100
        data_classification="PII_PCI_HIPAA",  # 100
        threat_status="ACTIVE_IOA",  # 100
    )

    assert evaluation["score_exact"] == 100.0
    assert evaluation["truerisk_score"] == 100
    assert evaluation["risk_tier"] == "CRITICAL"


def test_completely_isolated_clean_workload():
    """Verifies isolated workload with no vulnerabilities computes to 0 (Low)."""
    evaluation = TrueRiskCalculator.evaluate(
        misconfig_severity="CLEAN",
        network_exposure="ISOLATED",
        identity_role="NONE",
        data_classification="NONE",
        threat_status="NONE",
    )

    assert evaluation["truerisk_score"] == 0
    assert evaluation["risk_tier"] == "LOW"

