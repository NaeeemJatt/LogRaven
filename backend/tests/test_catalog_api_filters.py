# LogRaven — Direct Catalog Route Filtering Unit Test
import pytest
from fastapi import Response
from app.api.routes.cspm_compliance import list_catalog_controls


def test_catalog_mandate_filtering_pci_dss_oci():
    # Test PCI-DSS v4.0 on Oracle Cloud (92 rules total in OCI)
    resp = Response()
    res = list_catalog_controls(
        response=resp,
        provider="OCI",
        mandate="PCI-DSS v4.0",
        limit=50,
    )
    assert res["total"] == 92
    assert len(res["items"]) > 0
    assert all(item["provider"] == "OCI" for item in res["items"])


def test_catalog_mandate_filtering_all_providers():
    for mandate_name in [
        "SOC 2",
        "PCI-DSS v4.0",
        "ISO/IEC 27001:2022",
        "HIPAA Security Rule",
        "NIST CSF",
        "FedRAMP Moderate",
        "CIS Controls",
        "GDPR",
    ]:
        resp = Response()
        res = list_catalog_controls(
            response=resp,
            mandate=mandate_name,
            limit=10,
        )
        assert res["total"] == 1565, f"Failed for {mandate_name}, got {res['total']}"


def test_catalog_criticality_filtering_has_critical_rules():
    resp = Response()
    res = list_catalog_controls(
        response=resp,
        criticality="CRITICAL",
        limit=100,
    )
    assert res["total"] > 0
    assert all(item["criticality"] == "CRITICAL" for item in res["items"])
    titles = [item["title"].lower() for item in res["items"]]
    assert any("multi-factor authentication" in t or "root" in t for t in titles)


def test_catalog_criticality_filtering_per_provider():
    for prov in ["AWS", "AZURE", "GCP", "OCI"]:
        resp = Response()
        res = list_catalog_controls(
            response=resp,
            provider=prov,
            criticality="CRITICAL",
            limit=50,
        )
        assert res["total"] > 0, f"Expected CRITICAL rules for {prov}"
