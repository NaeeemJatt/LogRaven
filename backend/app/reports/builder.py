# LogRaven — Report Builder

from collections import defaultdict

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}


def _finding_to_dict(f) -> dict:
    """Convert a Finding ORM object to a plain dict for the template."""
    return {
        "severity":             f.severity,
        "title":                f.title,
        "description":          f.description,
        "mitre_technique_id":   f.mitre_technique_id,
        "mitre_technique_name": f.mitre_technique_name,
        "mitre_tactic":         f.mitre_tactic,
        "iocs":                 f.iocs or [],
        "remediation":          f.remediation,
        "finding_type":         f.finding_type,
        "confidence":           f.confidence,
    }


def build_report_context(report, findings: list) -> dict:
    """
    Build Jinja2 template context from a Report ORM object and
    a list of Finding ORM objects.
    """
    finding_dicts = [_finding_to_dict(f) for f in findings]

    # Split by type
    correlated = [d for d in finding_dicts if d["finding_type"] == "correlated"]
    single     = [d for d in finding_dicts if d["finding_type"] != "correlated"]

    # Sort all findings by severity
    all_sorted = sorted(
        finding_dicts,
        key=lambda d: _SEVERITY_ORDER.get(d.get("severity", "informational"), 4),
    )

    # Severity counts
    critical_count     = sum(1 for d in finding_dicts if d["severity"] == "critical")
    high_count         = sum(1 for d in finding_dicts if d["severity"] == "high")

    # Flat deduplicated IOC list
    seen_iocs: set[str] = set()
    ioc_list: list[str] = []
    for d in finding_dicts:
        for ioc in d.get("iocs") or []:
            ioc_str = str(ioc).strip()
            if ioc_str and ioc_str not in seen_iocs:
                seen_iocs.add(ioc_str)
                ioc_list.append(ioc_str)

    # Group by severity for optional section headers
    findings_by_severity: dict[str, list] = defaultdict(list)
    for d in all_sorted:
        findings_by_severity[d["severity"]].append(d)

    return {
        "report_id":             str(report.id),
        "investigation_id":      str(report.investigation_id),
        "generated_at":          report.created_at.strftime("%Y-%m-%d %H:%M UTC"),
        "summary":               report.summary or "",
        "severity_counts":       report.severity_counts or {},
        "correlated_findings":   correlated,
        "single_findings":       single,
        "all_findings":          all_sorted,
        "findings_by_severity":  dict(findings_by_severity),
        "mitre_techniques":      report.mitre_techniques or [],
        "total_findings":        len(finding_dicts),
        "critical_count":        critical_count,
        "high_count":            high_count,
        "ioc_list":              ioc_list,
    }
