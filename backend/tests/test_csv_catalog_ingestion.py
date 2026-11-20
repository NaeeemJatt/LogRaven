"""
Unit tests for Module 01: CSV Catalog Ingestion & Canonical Storage.
Verifies file existence, schemas, row counts, and criticality distributions.
"""

from pathlib import Path
import pytest
from app.scripts.validate_catalog_csvs import (
    validate_csv_catalog,
    parse_qualys_csv,
    EXPECTED_COUNTS,
    EXPECTED_CONTROL_COLUMNS,
    EXPECTED_POLICY_COLUMNS,
    EXPECTED_MANDATE_COLUMNS,
)

CATALOG_DIR = Path(__file__).resolve().parent.parent / "app" / "data" / "csv_catalog"


def test_catalog_directory_exists():
    assert CATALOG_DIR.is_dir(), f"Catalog directory does not exist at {CATALOG_DIR}"


@pytest.mark.parametrize(
    "filename,expected_count",
    [
        ("controls_aws.csv", 700),
        ("controls_azure.csv", 572),
        ("controls_gcp.csv", 201),
        ("controls_oci.csv", 92),
        ("policies.csv", 29),
        ("mandates.csv", 38),
    ],
)
def test_individual_csv_row_counts(filename: str, expected_count: int):
    filepath = CATALOG_DIR / filename
    assert filepath.is_file(), f"Expected file {filename} to exist"

    first_col = "CID" if filename.startswith("controls") else ("POLICY TITLE" if filename == "policies.csv" else "NAME")
    headers, rows = parse_qualys_csv(filepath, first_col)
    assert len(rows) == expected_count, f"{filename} row count mismatch: {len(rows)} != {expected_count}"


def test_full_catalog_validation_suite():
    report = validate_csv_catalog(CATALOG_DIR)
    assert report["valid"] is True, f"Catalog validation failed with errors: {report.get('errors')}"
    assert report["total_controls"] == 1565
    assert len(report["files"]["policies.csv"]["providers"]) == 4
    assert report["files"]["policies.csv"]["providers"]["AWS"] == 11
    assert report["files"]["policies.csv"]["providers"]["AZURE"] == 9
    assert report["files"]["policies.csv"]["providers"]["GCP"] == 7
    assert report["files"]["policies.csv"]["providers"]["OCI"] == 2


def test_aws_controls_criticality_distribution():
    headers, rows = parse_qualys_csv(CATALOG_DIR / "controls_aws.csv", "CID")
    high = sum(1 for r in rows if r["CRITICALITY"].upper() == "HIGH")
    medium = sum(1 for r in rows if r["CRITICALITY"].upper() == "MEDIUM")
    low = sum(1 for r in rows if r["CRITICALITY"].upper() == "LOW")

    assert high == 374
    assert medium == 281
    assert low == 45
    assert (high + medium + low) == 700
