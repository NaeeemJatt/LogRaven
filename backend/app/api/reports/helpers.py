# LogRaven — Report Response Helpers
#
# PURPOSE:
#   Build API response shapes for report endpoints.
#   Centralised here so both the reports router and any future
#   endpoint that needs the same shape can reuse these builders.


def build_report_response(report, findings: list) -> dict:
    """
    Construct the full report API response dict.

    Args:
        report:   Report ORM instance
        findings: list of Finding ORM instances (already loaded)
    """
    return {
        "id":                     str(report.id),
        "investigation_id":       str(report.investigation_id),
        "summary":                report.summary,
        "severity_counts":        report.severity_counts or {},
        "mitre_techniques":       report.mitre_techniques or [],
        "correlated_findings":    report.correlated_findings or [],
        "single_source_findings": report.single_source_findings or [],
        "findings": [
            {
                "id":                   str(f.id),
                "severity":             f.severity,
                "title":                f.title,
                "description":          f.description,
                "mitre_technique_id":   f.mitre_technique_id,
                "mitre_technique_name": f.mitre_technique_name,
                "mitre_tactic":         f.mitre_tactic,
                "iocs":                 f.iocs or [],
                "remediation":          f.remediation,
                "finding_type":         f.finding_type,
                "source_files":         f.source_files or [],
                "confidence":           f.confidence,
            }
            for f in findings
        ],
        "created_at": report.created_at.isoformat(),
    }


def build_download_response(report, storage) -> dict | None:
    """
    Construct the PDF download response dict.
    Returns None when no PDF has been generated yet.

    Args:
        report:  Report ORM instance
        storage: StorageBackend instance (local or S3)
    """
    if not report.pdf_storage_key:
        return None

    url = storage.get_download_url(report.pdf_storage_key)
    return {
        "download_url": url,
        "filename":     f"lograven-report-{str(report.id)[:8]}.pdf",
        "expires_in":   86400,
    }
