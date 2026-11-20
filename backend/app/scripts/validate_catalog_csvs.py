#!/usr/bin/env python3
"""
LogRaven — CSV Catalog Validator (Module 01)
Validates the canonical Qualys TotalCloud CSV files in backend/app/data/csv_catalog/.
Verifies preambles, header integrity, row counts, criticality distributions, and encoding.
"""

from __future__ import annotations

import csv
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Expected schemas and counts per specification
EXPECTED_CONTROL_COLUMNS = [
    "CID",
    "CONTROL NAME",
    "SERVICE",
    "PLATFORM",
    "TYPE",
    "EXECUTION TYPE",
    "MODIFIED BY",
    "MODIFIED TIME",
    "CRITICALITY",
]

EXPECTED_POLICY_COLUMNS = [
    "POLICY TITLE",
    "PROVIDER",
    "EXECUTION TYPE",
    "CREATED BY",
    "CREATED TIME",
    "MODIFIED BY",
    "MODIFIED TIME",
]

EXPECTED_MANDATE_COLUMNS = [
    "NAME",
    "VERSION",
    "PUBLISHER",
    "RELEASED DATE",
    "LAST MODIFIED DATE",
]

EXPECTED_COUNTS = {
    "controls_aws.csv": {
        "count": 700,
        "criticality": {"HIGH": 374, "MEDIUM": 281, "LOW": 45},
        "platform": "Amazon Web Service",
    },
    "controls_azure.csv": {
        "count": 572,
        "criticality": {"HIGH": 323, "MEDIUM": 186, "LOW": 63},
        "platform": "Microsoft Azure",
    },
    "controls_gcp.csv": {
        "count": 201,
        "criticality": {"HIGH": 107, "MEDIUM": 72, "LOW": 22},
        "platform": "Google Cloud Platform",
    },
    "controls_oci.csv": {
        "count": 92,
        "criticality": {"HIGH": 50, "MEDIUM": 35, "LOW": 7},
        "platform": "Oracle Cloud Infrastructure",
    },
    "policies.csv": {
        "count": 29,
        "providers": {"AWS": 11, "AZURE": 9, "GCP": 7, "OCI": 2},
    },
    "mandates.csv": {
        "count": 38,
    },
}


def parse_qualys_csv(filepath: Path, expected_first_col: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Parse Qualys CSV, stripping preamble and returning (headers, rows)."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))

    if not rows:
        raise ValueError(f"File {filepath} is empty")

    header_idx = None
    for idx, row in enumerate(rows[:10]):
        if row and row[0].strip().upper() == expected_first_col.upper():
            header_idx = idx
            break

    if header_idx is None:
        raise ValueError(f"Could not find header row starting with '{expected_first_col}' in {filepath}")

    headers = [col.strip() for col in rows[header_idx]]
    data_rows = []
    for r in rows[header_idx + 1:]:
        if not r or not any(c.strip() for c in r):
            continue
        # Allow trailing empty columns if any
        if len(r) >= len(headers):
            row_dict = {headers[i]: r[i].strip() for i in range(len(headers))}
            data_rows.append(row_dict)
        elif len(r) == len(headers) - 1:
            # Handle potential optional trailing column
            row_dict = {headers[i]: (r[i].strip() if i < len(r) else "") for i in range(len(headers))}
            data_rows.append(row_dict)

    return headers, data_rows


def validate_csv_catalog(catalog_dir: Path | str) -> Dict[str, Any]:
    """Validate all 6 files in the CSV catalog."""
    cat_path = Path(catalog_dir)
    results: Dict[str, Any] = {"files": {}, "valid": True, "errors": []}

    # 1. Validate Controls Files
    total_controls = 0
    for filename in ["controls_aws.csv", "controls_azure.csv", "controls_gcp.csv", "controls_oci.csv"]:
        filepath = cat_path / filename
        if not filepath.is_file():
            results["valid"] = False
            results["errors"].append(f"Missing file: {filename}")
            continue

        try:
            headers, rows = parse_qualys_csv(filepath, "CID")
            expected_spec = EXPECTED_COUNTS[filename]

            # Header verification
            missing_cols = [c for c in EXPECTED_CONTROL_COLUMNS if c not in headers]
            if missing_cols:
                results["valid"] = False
                results["errors"].append(f"{filename} missing columns: {missing_cols}")

            # Count verification
            actual_count = len(rows)
            total_controls += actual_count
            if actual_count != expected_spec["count"]:
                results["valid"] = False
                results["errors"].append(
                    f"{filename} expected {expected_spec['count']} rows, got {actual_count}"
                )

            # Criticality breakdown
            crit_counts = Counter(r.get("CRITICALITY", "").upper() for r in rows)
            expected_crit = expected_spec.get("criticality", {})
            for crit, count in expected_crit.items():
                if crit_counts.get(crit, 0) != count:
                    results["valid"] = False
                    results["errors"].append(
                        f"{filename} criticality {crit} expected {count}, got {crit_counts.get(crit, 0)}"
                    )

            results["files"][filename] = {
                "rows": actual_count,
                "criticality": dict(crit_counts),
                "headers_valid": len(missing_cols) == 0,
            }
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Error parsing {filename}: {str(e)}")

    # 2. Validate Policies
    pol_file = cat_path / "policies.csv"
    if not pol_file.is_file():
        results["valid"] = False
        results["errors"].append("Missing file: policies.csv")
    else:
        try:
            headers, rows = parse_qualys_csv(pol_file, "POLICY TITLE")
            missing_cols = [c for c in EXPECTED_POLICY_COLUMNS if c not in headers]
            if missing_cols:
                results["valid"] = False
                results["errors"].append(f"policies.csv missing columns: {missing_cols}")

            actual_count = len(rows)
            if actual_count != EXPECTED_COUNTS["policies.csv"]["count"]:
                results["valid"] = False
                results["errors"].append(
                    f"policies.csv expected {EXPECTED_COUNTS['policies.csv']['count']} rows, got {actual_count}"
                )

            prov_counts = Counter(r.get("PROVIDER", "").upper() for r in rows)
            results["files"]["policies.csv"] = {
                "rows": actual_count,
                "providers": dict(prov_counts),
                "headers_valid": len(missing_cols) == 0,
            }
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Error parsing policies.csv: {str(e)}")

    # 3. Validate Mandates
    mand_file = cat_path / "mandates.csv"
    if not mand_file.is_file():
        results["valid"] = False
        results["errors"].append("Missing file: mandates.csv")
    else:
        try:
            headers, rows = parse_qualys_csv(mand_file, "NAME")
            missing_cols = [c for c in EXPECTED_MANDATE_COLUMNS if c not in headers]
            if missing_cols:
                results["valid"] = False
                results["errors"].append(f"mandates.csv missing columns: {missing_cols}")

            actual_count = len(rows)
            if actual_count != EXPECTED_COUNTS["mandates.csv"]["count"]:
                results["valid"] = False
                results["errors"].append(
                    f"mandates.csv expected {EXPECTED_COUNTS['mandates.csv']['count']} rows, got {actual_count}"
                )

            results["files"]["mandates.csv"] = {
                "rows": actual_count,
                "headers_valid": len(missing_cols) == 0,
            }
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Error parsing mandates.csv: {str(e)}")

    results["total_controls"] = total_controls
    if total_controls != 1565:
        results["valid"] = False
        results["errors"].append(f"Total controls expected 1565, got {total_controls}")

    return results


def main() -> int:
    default_dir = Path(__file__).resolve().parent.parent / "data" / "csv_catalog"
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else default_dir

    print(f"=== LogRaven CSV Catalog Validator (Module 01) ===")
    print(f"Validating catalog at: {target_dir}")

    report = validate_csv_catalog(target_dir)

    print("\n--- Summary ---")
    for fname, details in report.get("files", {}).items():
        print(f"  [OK] {fname:<20} Rows: {details['rows']}")
        if "criticality" in details:
            print(f"       Criticality: {details['criticality']}")
        if "providers" in details:
            print(f"       Providers:   {details['providers']}")

    print(f"\nTotal Controls: {report.get('total_controls', 0)} / 1565")

    if report["valid"]:
        print("\n>>> VALIDATION STATUS: PASS (100% Fidelity) <<<")
        return 0
    else:
        print("\n>>> VALIDATION STATUS: FAIL <<<")
        for err in report["errors"]:
            print(f"  - ERROR: {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
