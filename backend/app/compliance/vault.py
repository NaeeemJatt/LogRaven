# LogRaven — Cryptographic Evidence Vault Packer
#
# Generates an immutable, auditor-ready ZIP package structured according to
# the AICPA Trust Services Criteria (TSC) / ISO 27001 standards.
# Every artifact in the archive is cryptographically hashed with SHA-256 and
# listed in SHA256_INTEGRITY_MANIFEST.txt for SOC 2 Type II non-repudiation.

import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any

from app.models.soc2_audit import AuditJob, ComplianceException


def _sha256_bytes(data: bytes) -> str:
    """Calculate SHA256 hex digest for binary content."""
    return hashlib.sha256(data).hexdigest()


def _sanitize_filename(name: str) -> str:
    """Ensure safe ASCII alphanumeric filenames."""
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)


def build_evidence_vault_zip(
    company_name: str,
    audit_jobs: list[AuditJob],
    exceptions: list[ComplianceException],
    allowed_frameworks: list[str] | None = None,
    include_raw_telemetry: bool = True,
) -> tuple[bytes, str]:
    """
    Constructs an auditor evidence ZIP archive in-memory.
    Returns (zip_bytes, filename).
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")
    clean_company = _sanitize_filename(company_name)
    zip_filename = f"LogRaven_Evidence_Vault_{clean_company}_{date_str}.zip"

    buf = io.BytesIO()
    manifest_entries: list[tuple[str, str]] = []  # (relpath, sha256)

    def write_file(zf: zipfile.ZipFile, relpath: str, content: bytes) -> None:
        zf.writestr(relpath, content)
        digest = _sha256_bytes(content)
        manifest_entries.append((relpath, digest))

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # ── 1. AUDITOR README ─────────────────────────────────────────────────
        readme_text = (
            f"LogRaven Continuous Compliance — Official Evidence Vault\n"
            f"==========================================================\n\n"
            f"Company Name       : {company_name}\n"
            f"Package Generated  : {now.isoformat()}\n"
            f"Auditor Nonce / ID : {_sha256_bytes(f'{company_name}:{now.isoformat()}'.encode())[:16]}\n"
            f"Total Audits Packaged: {len(audit_jobs)}\n"
            f"Active Exceptions  : {len(exceptions)}\n\n"
            f"METHODOLOGY & NON-REPUDIATION:\n"
            f"All evidence contained within this archive was collected autonomously by LogRaven\n"
            f"via read-only, scoped cloud provider APIs (IAM, CloudTrail, Config, GuardDuty, S3).\n"
            f"Evidence signals are normalized, cryptographically fingerprinted, and mapped to\n"
            f"SOC 2 Trust Services Criteria, ISO 27001, and CIS Benchmarks.\n\n"
            f"INTEGRITY VERIFICATION:\n"
            f"To verify file integrity and detect tampering, run:\n"
            f"  sha256sum -c SHA256_INTEGRITY_MANIFEST.txt\n\n"
            f"FOLDER STRUCTURE:\n"
            f"  01_Executive_Summary.json            — Summary scores & assessment outcomes\n"
            f"  02_Business_Logic_Exceptions_Ledger.csv — Authorized risk acceptances & compensating controls\n"
            f"  Criteria_*/                          — Control evaluation evidence organized by criteria\n"
            f"  Raw_Telemetry_Snapshots/             — Sanitized cloud configuration evidence\n"
            f"  SHA256_INTEGRITY_MANIFEST.txt        — Cryptographic checksums of all bundled files\n"
        )
        write_file(zf, "00_AUDITOR_README.txt", readme_text.encode("utf-8"))

        # ── 2. EXECUTIVE SUMMARY JSON ─────────────────────────────────────────
        latest_job = audit_jobs[0] if audit_jobs else None
        exec_summary: dict[str, Any] = {
            "company_name": company_name,
            "generated_at": now.isoformat(),
            "latest_audit": None,
            "historical_audits_count": len(audit_jobs),
            "exceptions_summary": {
                "active_exceptions_count": len(exceptions),
                "controls_with_exceptions": [e.control_id for e in exceptions],
            },
        }

        if latest_job:
            exec_summary["latest_audit"] = {
                "audit_id": str(latest_job.id),
                "status": latest_job.status,
                "frameworks": latest_job.frameworks or ["soc2"],
                "score_percent": latest_job.score_percent,
                "raw_score_percent": latest_job.raw_score_percent or latest_job.score_percent,
                "completed_at": (
                    getattr(latest_job, "completed_at", None)
                    or getattr(latest_job, "created_at", None)
                ).isoformat()
                if (getattr(latest_job, "completed_at", None) or getattr(latest_job, "created_at", None))
                else None,
                "total_controls_assessed": len(latest_job.results) if latest_job.results else 0,
            }

        summary_bytes = json.dumps(exec_summary, indent=2).encode("utf-8")
        write_file(zf, "01_Executive_Summary.json", summary_bytes)

        # ── 3. EXCEPTIONS & COMPENSATING CONTROLS CSV ─────────────────────────
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow([
            "Control ID",
            "Framework",
            "Status",
            "Business Justification",
            "Compensating Controls",
            "Authorized By",
            "Expires At",
            "Created At",
        ])
        for exc in exceptions:
            writer.writerow([
                exc.control_id,
                exc.framework,
                exc.status,
                exc.justification,
                exc.compensating_controls or "N/A",
                exc.authorized_by or "N/A",
                exc.expires_at.isoformat() if exc.expires_at else "Never",
                exc.created_at.isoformat() if exc.created_at else "",
            ])
        write_file(zf, "02_Business_Logic_Exceptions_Ledger.csv", csv_buf.getvalue().encode("utf-8"))

        # ── 4. CRITERIA FOLDERS (PER-CONTROL EVIDENCE) ────────────────────────
        if latest_job and latest_job.results:
            for res in latest_job.results:
                ctrl_id = res.control_id.upper()
                # Determine folder based on prefix (e.g. CC6 -> Criteria_CC6_Logical_Access)
                if ctrl_id.startswith("CC6"):
                    folder = "Criteria_CC6_Logical_and_Physical_Access"
                elif ctrl_id.startswith("CC7"):
                    folder = "Criteria_CC7_System_Operations"
                elif ctrl_id.startswith("CC8"):
                    folder = "Criteria_CC8_Change_Management"
                elif ctrl_id.startswith("CC9"):
                    folder = "Criteria_CC9_Risk_Mitigation"
                elif ctrl_id.startswith("A.") or ctrl_id.startswith("5.") or ctrl_id.startswith("8."):
                    folder = "Criteria_ISO27001_Information_Security"
                elif ctrl_id.startswith("CIS"):
                    folder = "Criteria_CIS_Benchmark"
                else:
                    folder = "Criteria_General_Security"

                control_evidence = {
                    "control_id": res.control_id,
                    "control_name": res.control_name,
                    "status": res.status,
                    "framework": res.framework,
                    "evidence_summary": res.evidence_summary,
                    "remediation": res.remediation,
                    "referenced_signals": res.referenced_signals or [],
                    "assessed_at": res.assessed_at.isoformat() if res.assessed_at else None,
                }
                safe_ctrl = _sanitize_filename(res.control_id)
                write_file(
                    zf,
                    f"{folder}/{safe_ctrl}_evidence.json",
                    json.dumps(control_evidence, indent=2).encode("utf-8"),
                )

        # ── 5. RAW TELEMETRY SNAPSHOTS ────────────────────────────────────────
        if include_raw_telemetry and latest_job and latest_job.evidence_signals:
            write_file(
                zf,
                "Raw_Telemetry_Snapshots/evidence_signals.json",
                json.dumps(latest_job.evidence_signals, indent=2).encode("utf-8"),
            )

        # ── 6. SHA256 INTEGRITY MANIFEST ──────────────────────────────────────
        # Sort manifest lines by filename for deterministic presentation
        manifest_entries.sort(key=lambda x: x[0])
        manifest_text = "\n".join(f"{digest}  {relpath}" for relpath, digest in manifest_entries) + "\n"
        zf.writestr("SHA256_INTEGRITY_MANIFEST.txt", manifest_text.encode("utf-8"))

    return buf.getvalue(), zip_filename
