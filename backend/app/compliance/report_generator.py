# LogRaven — SOC 2 Compliance Report Generator
#
# Generates professional multi-page PDF evidence packages using reportlab.
# Pages include: cover, executive summary, per-control details, and appendix.

import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
)
from reportlab.lib import colors

if TYPE_CHECKING:
    from app.models.soc2_audit import AuditJob, AuditResult

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# Color Scheme (HexColor constants — for reportlab Table/canvas use only)
# For f-string XML interpolation always use the _HEX_* string constants below.
# ═════════════════════════════════════════════════════════════════════════════

NAVY = HexColor("#1A2744")
ACCENT = HexColor("#2F81F7")
PASS_GREEN = HexColor("#3FB950")
FAIL_RED = HexColor("#F85149")
PARTIAL_YELLOW = HexColor("#D29922")
SUPPRESSED_PURPLE = HexColor("#A371F7")
TEXT_PRIMARY = HexColor("#E6EDF3")
TEXT_SECONDARY = HexColor("#8B949E")
BACKGROUND = HexColor("#0D1117")
SURFACE = HexColor("#161B22")
BORDER = HexColor("#30363D")

# Hex string literals for XML/f-string interpolation
_HEX_NAVY = "#1A2744"
_HEX_ACCENT = "#2F81F7"
_HEX_PASS = "#3FB950"
_HEX_FAIL = "#F85149"
_HEX_PARTIAL = "#D29922"
_HEX_SUPPRESSED = "#A371F7"
_HEX_TEXT_PRIMARY = "#E6EDF3"
_HEX_TEXT_SECONDARY = "#8B949E"

# ═════════════════════════════════════════════════════════════════════════════
# Style Definitions
# ═════════════════════════════════════════════════════════════════════════════

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "CustomTitle",
    parent=styles["Normal"],
    fontSize=28,
    textColor=NAVY,
    spaceAfter=12,
    alignment=1,
    fontName="Helvetica-Bold",
)

heading_style = ParagraphStyle(
    "CustomHeading",
    parent=styles["Normal"],
    fontSize=14,
    textColor=NAVY,
    spaceAfter=10,
    spaceBefore=10,
    fontName="Helvetica-Bold",
)

subheading_style = ParagraphStyle(
    "CustomSubheading",
    parent=styles["Normal"],
    fontSize=11,
    textColor=ACCENT,
    spaceAfter=8,
    fontName="Helvetica-Bold",
)

normal_style = ParagraphStyle(
    "CustomNormal",
    parent=styles["Normal"],
    fontSize=10,
    textColor=TEXT_PRIMARY,
    spaceAfter=6,
    leading=12,
)

secondary_style = ParagraphStyle(
    "CustomSecondary",
    parent=styles["Normal"],
    fontSize=9,
    textColor=TEXT_SECONDARY,
    spaceAfter=4,
)

# ═════════════════════════════════════════════════════════════════════════════
# Page Number Footer
# ═════════════════════════════════════════════════════════════════════════════


def _add_page_number(canvas, doc):
    """Footer callback: print page number on all pages except the cover."""
    if doc.page > 1:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_SECONDARY)
        canvas.drawRightString(A4[0] - 2 * cm, 1.5 * cm, f"Page {doc.page}")
        canvas.restoreState()


# ═════════════════════════════════════════════════════════════════════════════
# Main Function
# ═════════════════════════════════════════════════════════════════════════════


def generate_soc2_report(audit_job: "AuditJob", audit_results: list["AuditResult"]) -> str:
    """Backward-compatible SOC 2 wrapper around the generic report generator."""
    return generate_compliance_report(audit_job, audit_results, framework_name="SOC 2 Type II", framework_id="soc2")


def generate_compliance_report(
    audit_job: "AuditJob",
    audit_results: list["AuditResult"],
    framework_name: str = "SOC 2 Type II",
    framework_id: str = "soc2",
) -> str:
    """
    Generate a multi-page compliance evidence package PDF for one framework.

    Args:
        audit_job: AuditJob model instance
        audit_results: AuditResult rows for this framework
        framework_name: Display name used in titles/prose
        framework_id: Stable slug used in the filename

    Returns:
        Absolute file path to the generated PDF
    """
    # Create output directory using platform-safe temp dir
    report_dir = Path(tempfile.gettempdir()) / "lograven_reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    company_slug = audit_job.company_name.lower().replace(" ", "_")
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{audit_job.id}_{framework_id}_{company_slug}_{date_str}.pdf"
    pdf_path = report_dir / filename

    logger.info("Generating %s report: %s", framework_name, pdf_path)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"{framework_name} Evidence Package",
    )

    story = []

    # Page 1: Cover Page
    story.extend(_build_cover_page(audit_job, framework_name))
    story.append(PageBreak())

    # Page 2: Executive Summary
    story.extend(_build_executive_summary(audit_job, audit_results, framework_name))
    story.append(PageBreak())

    # Pages 3+: Per-Control Details
    for result in audit_results:
        story.extend(_build_control_detail(result))
        story.append(Spacer(1, 0.3 * cm))
        story.append(PageBreak())

    # Exceptions Log Section (Auditor documentation if any suppressed controls exist)
    exceptions_story = _build_exceptions_section(audit_results)
    if exceptions_story:
        story.extend(exceptions_story)
        story.append(PageBreak())

    # Final Page: Appendix
    story.extend(_build_appendix())

    # Build PDF with page number footer on all pages except cover
    doc.build(
        story,
        onFirstPage=lambda c, d: None,
        onLaterPages=_add_page_number,
    )
    logger.info("Report generated successfully: %s", pdf_path)

    return str(pdf_path)


# ═════════════════════════════════════════════════════════════════════════════
# Page Builders
# ═════════════════════════════════════════════════════════════════════════════


def _build_cover_page(audit_job: "AuditJob", framework_name: str = "SOC 2 Type II") -> list:
    """Build the cover page."""
    story = []

    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            f"<font color='{_HEX_ACCENT}' size=24><b>LogRaven</b></font>",
            normal_style,
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    story.append(
        Paragraph(
            f"<font color='{_HEX_NAVY}' size=28><b>{escape(framework_name)}<br/>Evidence Package</b></font>",
            title_style,
        )
    )
    story.append(Spacer(1, 1 * cm))

    story.append(
        Paragraph(
            f"<font color='{_HEX_TEXT_PRIMARY}' size=18><b>{escape(audit_job.company_name)}</b></font>",
            normal_style,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    period_text = f"{audit_job.audit_start_date} to {audit_job.audit_end_date}"
    story.append(
        Paragraph(
            f"<font color='{_HEX_TEXT_SECONDARY}' size=11>Audit Period: {escape(period_text)}</font>",
            secondary_style,
        )
    )
    story.append(Spacer(1, 0.2 * cm))

    generated_date = datetime.utcnow().strftime("%B %d, %Y")
    story.append(
        Paragraph(
            f"<font color='{_HEX_TEXT_SECONDARY}' size=10>Generated: {generated_date}</font>",
            secondary_style,
        )
    )
    story.append(Spacer(1, 1.5 * cm))

    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            f"<font color='{_HEX_ACCENT}' size=10><b>Prepared by</b></font>",
            subheading_style,
        )
    )
    story.append(
        Paragraph(
            "LogRaven Compliance Agent | Obsidian Cyber Group",
            secondary_style,
        )
    )
    story.append(Spacer(1, 1 * cm))

    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"<font color='{_HEX_FAIL}' size=10><b>CONFIDENTIAL</b></font><br/>"
            f"<font color='{_HEX_TEXT_SECONDARY}' size=9>For audit purposes only</font>",
            secondary_style,
        )
    )

    return story


def _build_executive_summary(
    audit_job: "AuditJob",
    audit_results: list["AuditResult"],
    framework_name: str = "SOC 2 Type II",
) -> list:
    """Build the executive summary page."""
    story = []

    story.append(
        Paragraph(
            f"<font color='{_HEX_NAVY}' size=16><b>Executive Summary</b></font>",
            heading_style,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    pass_count = sum(1 for r in audit_results if r.status == "PASS")
    suppressed_count = sum(1 for r in audit_results if r.status == "SUPPRESSED")
    fail_count = sum(1 for r in audit_results if r.status == "FAIL")
    partial_count = sum(1 for r in audit_results if r.status == "PARTIAL")
    total = len(audit_results)
    raw_score_percent = (pass_count / total * 100) if total > 0 else 0.0
    effective_denom = max(total - suppressed_count, 1)
    adjusted_score_percent = (pass_count / effective_denom * 100) if effective_denom > 0 else 0.0

    score_display = (
        f"<font color='{_HEX_ACCENT}' size=24><b>{adjusted_score_percent:.1f}%</b></font>"
    )
    story.append(Paragraph(score_display, normal_style))
    subtext = (
        f"<font color='{_HEX_TEXT_SECONDARY}' size=10>Adjusted Compliance Score "
        f"({suppressed_count} business exceptions authorized) | Raw: {raw_score_percent:.1f}%</font>"
        if suppressed_count > 0
        else f"<font color='{_HEX_TEXT_SECONDARY}' size=10>Overall Compliance Score</font>"
    )
    story.append(Paragraph(subtext, secondary_style))
    story.append(Spacer(1, 0.5 * cm))

    table_data = [
        [
            f"<font color='{_HEX_TEXT_PRIMARY}' size=9><b>Assessed</b></font>",
            f"<font color='{_HEX_PASS}' size=9><b>PASS</b></font>",
            f"<font color='{_HEX_SUPPRESSED}' size=9><b>EXCEPTIONS</b></font>",
            f"<font color='{_HEX_FAIL}' size=9><b>FAIL</b></font>",
            f"<font color='{_HEX_PARTIAL}' size=9><b>PARTIAL</b></font>",
        ],
        [
            f"<font color='{_HEX_TEXT_PRIMARY}' size=10>{total}</font>",
            f"<font color='{_HEX_PASS}' size=10><b>{pass_count}</b></font>",
            f"<font color='{_HEX_SUPPRESSED}' size=10><b>{suppressed_count}</b></font>",
            f"<font color='{_HEX_FAIL}' size=10><b>{fail_count}</b></font>",
            f"<font color='{_HEX_PARTIAL}' size=10><b>{partial_count}</b></font>",
        ],
    ]

    table = Table(table_data, colWidths=[2.6 * cm, 1.8 * cm, 2.5 * cm, 1.8 * cm, 1.8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), SURFACE),
                ("TEXTCOLOR", (0, 0), (-1, 0), ACCENT),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("BACKGROUND", (0, 1), (-1, -1), NAVY),
                ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_PRIMARY),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [NAVY, SURFACE]),
                ("GRID", (0, 0), (-1, -1), 1, BORDER),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.5 * cm))

    posture_text = (
        f"This audit assessed {total} {escape(framework_name)} controls. "
        f"The assessment found {pass_count} controls operating effectively, "
        f"{suppressed_count} controls with authorized business exceptions, "
        f"{fail_count} controls requiring attention, and {partial_count} controls with partial implementation. "
        f"The adjusted compliance posture is rated at {adjusted_score_percent:.1f}%."
    )
    story.append(Paragraph(posture_text, normal_style))
    story.append(Spacer(1, 0.5 * cm))

    if fail_count > 0:
        story.append(
            Paragraph(
                f"<font color='{_HEX_FAIL}' size=11><b>Controls Requiring Immediate Attention</b></font>",
                subheading_style,
            )
        )
        story.append(Spacer(1, 0.2 * cm))
        for result in audit_results:
            if result.status == "FAIL":
                story.append(
                    Paragraph(
                        f"• <font color='{_HEX_TEXT_PRIMARY}'>"
                        f"{escape(result.control_id)} — {escape(result.control_name)}"
                        f"</font>",
                        normal_style,
                    )
                )

    return story


def _build_control_detail(audit_result: "AuditResult") -> list:
    """Build a per-control detail section."""
    story = []

    story.append(
        Paragraph(
            f"<font color='{_HEX_NAVY}' size=14><b>"
            f"{escape(audit_result.control_id)} — {escape(audit_result.control_name)}"
            f"</b></font>",
            heading_style,
        )
    )

    # Status badge — use hex string literals, NOT HexColor objects
    if audit_result.status == "PASS":
        badge_hex = _HEX_PASS
        badge_text = "PASS"
    elif audit_result.status == "SUPPRESSED":
        badge_hex = _HEX_SUPPRESSED
        badge_text = "SUPPRESSED (BUSINESS EXCEPTION)"
    elif audit_result.status == "FAIL":
        badge_hex = _HEX_FAIL
        badge_text = "FAIL"
    else:
        badge_hex = _HEX_PARTIAL
        badge_text = "PARTIAL"

    story.append(
        Paragraph(
            f"<font color='{badge_hex}' size=11><b>Status: {badge_text}</b></font>",
            normal_style,
        )
    )
    story.append(Spacer(1, 0.2 * cm))

    # If suppressed, render business justification callout
    exc = (audit_result.raw_evidence_summary or {}).get("exception")
    if exc:
        justification = exc.get("business_justification", "Documented business logic requirement")
        compensating = exc.get("compensating_controls") or "None documented"
        suppressed_by = exc.get("suppressed_by", "Security Officer")
        story.append(
            Paragraph(
                f"<font color='{_HEX_SUPPRESSED}' size=10><b>Authorized Business Logic Exception</b></font><br/>"
                f"<font color='{_HEX_TEXT_PRIMARY}' size=9><b>Justification:</b> {escape(justification)}</font><br/>"
                f"<font color='{_HEX_TEXT_SECONDARY}' size=9><b>Compensating Controls:</b> {escape(compensating)}</font><br/>"
                f"<font color='{_HEX_TEXT_SECONDARY}' size=8>Authorized by: {escape(suppressed_by)}</font>",
                normal_style,
            )
        )
        story.append(Spacer(1, 0.3 * cm))

    story.append(
        Paragraph(
            f"<font color='{_HEX_TEXT_PRIMARY}' size=10>{escape(audit_result.ai_description)}</font>",
            normal_style,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    evidence_refs = audit_result.raw_evidence_summary.get("evidence_references", [])
    if evidence_refs:
        story.append(
            Paragraph(
                f"<font color='{_HEX_ACCENT}' size=10><b>Evidence References</b></font>",
                subheading_style,
            )
        )
        for ref in evidence_refs:
            story.append(
                Paragraph(
                    f"• <font color='{_HEX_TEXT_SECONDARY}'>{escape(str(ref))}</font>",
                    secondary_style,
                )
            )
        story.append(Spacer(1, 0.2 * cm))

    gaps = audit_result.raw_evidence_summary.get("gaps", [])
    story.append(
        Paragraph(
            f"<font color='{_HEX_ACCENT}' size=10><b>Gaps Identified</b></font>",
            subheading_style,
        )
    )
    if gaps:
        for gap in gaps:
            story.append(
                Paragraph(
                    f"• <font color='{_HEX_FAIL}'>{escape(str(gap))}</font>",
                    secondary_style,
                )
            )
    else:
        story.append(
            Paragraph(
                f"<font color='{_HEX_PASS}' size=10>None identified — control is operating effectively.</font>",
                secondary_style,
            )
        )

    remediation = audit_result.raw_evidence_summary.get("remediation")
    if remediation:
        story.append(Spacer(1, 0.2 * cm))
        story.append(
            Paragraph(
                f"<font color='{_HEX_ACCENT}' size=10><b>Recommended Remediation</b></font>",
                subheading_style,
            )
        )
        story.append(
            Paragraph(
                f"<font color='{_HEX_TEXT_PRIMARY}' size=10>{escape(str(remediation))}</font>",
                normal_style,
            )
        )

    remediation_guide = audit_result.raw_evidence_summary.get("remediation_guide")
    if remediation_guide:
        cli_cmd = remediation_guide.get("aws_cli_command")
        verify_cmd = remediation_guide.get("verification_command")
        if cli_cmd and not cli_cmd.startswith("# Note"):
            story.append(Spacer(1, 0.15 * cm))
            story.append(
                Paragraph(
                    f"<font color='{_HEX_TEXT_SECONDARY}' size=8><b>AWS CLI Remediation:</b></font><br/>"
                    f"<font color='{_HEX_ACCENT}' face='Courier' size=8>{escape(cli_cmd[:300])}</font>",
                    normal_style,
                )
            )
        if verify_cmd and not verify_cmd.startswith("# Re-run"):
            story.append(Spacer(1, 0.1 * cm))
            story.append(
                Paragraph(
                    f"<font color='{_HEX_TEXT_SECONDARY}' size=8><b>Verification Command:</b></font><br/>"
                    f"<font color='{_HEX_PASS}' face='Courier' size=8>{escape(verify_cmd[:250])}</font>",
                    normal_style,
                )
            )

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("<hr/><br/>", normal_style))

    return story


def _build_appendix() -> list:
    """Build the final appendix page."""
    story = []

    story.append(
        Paragraph(
            f"<font color='{_HEX_NAVY}' size=16><b>Appendix</b></font>",
            heading_style,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    story.append(
        Paragraph(
            f"<font color='{_HEX_ACCENT}' size=11><b>About This Report</b></font>",
            subheading_style,
        )
    )
    about_text = (
        "This SOC 2 evidence package was generated by LogRaven Compliance Agent. "
        "The audit process collects evidence from your AWS account via read-only STS AssumeRole, "
        "assesses it against AICPA Trust Service Criteria (CC6 and CC7 controls), and generates this report. "
        "The methodology is designed to be repeatable and transparent, providing objective evidence of your "
        "control posture at a point in time."
    )
    story.append(Paragraph(about_text, normal_style))
    story.append(Spacer(1, 0.3 * cm))

    story.append(
        Paragraph(
            f"<font color='{_HEX_ACCENT}' size=11><b>Data Privacy Notice</b></font>",
            subheading_style,
        )
    )
    privacy_text = (
        "LogRaven maintains strict data privacy boundaries. Raw AWS identifiers (account IDs, ARNs, IP addresses, "
        "usernames) are collected and stored in your PostgreSQL database only. Before any AI analysis, all PII is "
        "stripped and replaced with aggregated statistics (counts, booleans, policy summaries). This sanitized "
        "summary is sent to our AI engine for control assessment. Raw identifiers never leave your infrastructure."
    )
    story.append(Paragraph(privacy_text, normal_style))
    story.append(Spacer(1, 0.3 * cm))

    story.append(
        Paragraph(
            f"<font color='{_HEX_FAIL}' size=11><b>Disclaimer</b></font>",
            subheading_style,
        )
    )
    disclaimer_text = (
        "This report is AI-assisted. All findings should be reviewed by a qualified security professional "
        "before submission to a certification body. LogRaven and its operators assume no liability for any errors, "
        "omissions, or interpretations contained herein. This report is provided as-is for informational purposes."
    )
    story.append(Paragraph(disclaimer_text, normal_style))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"<font color='{_HEX_TEXT_SECONDARY}' size=9><b>LogRaven Compliance Agent</b><br/>"
            "Obsidian Cyber Group — SOC 2 Audit Readiness as a Service</font>",
            secondary_style,
        )
    )

    return story


def _build_exceptions_section(audit_results: list["AuditResult"]) -> list:
    """Build dedicated business logic exceptions & compensating controls log for auditors."""
    suppressed = [r for r in audit_results if r.status == "SUPPRESSED"]
    if not suppressed:
        return []

    story = []
    story.append(
        Paragraph(
            f"<font color='{_HEX_NAVY}' size=16><b>Auditor Log: Business Exceptions & Compensating Controls</b></font>",
            heading_style,
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            f"<font color='{_HEX_TEXT_SECONDARY}' size=10>The following {len(suppressed)} controls have authorized business logic exceptions approved with documented compensating controls. These items have been reviewed and accepted by security leadership.</font>",
            secondary_style,
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    table_data = [
        [
            f"<font color='{_HEX_TEXT_PRIMARY}' size=9><b>Control</b></font>",
            f"<font color='{_HEX_TEXT_PRIMARY}' size=9><b>Business Justification</b></font>",
            f"<font color='{_HEX_TEXT_PRIMARY}' size=9><b>Compensating Controls</b></font>",
            f"<font color='{_HEX_TEXT_PRIMARY}' size=9><b>Review By / Expiry</b></font>",
        ]
    ]

    for r in suppressed:
        exc = (r.raw_evidence_summary or {}).get("exception") or {}
        justification = exc.get("business_justification") or "Documented business logic requirement"
        compensating = exc.get("compensating_controls") or "N/A"
        suppressed_by = exc.get("suppressed_by") or "Security Lead"
        expires_at = exc.get("expires_at")
        expiry_str = expires_at.split("T")[0] if expires_at else "Perpetual"

        table_data.append(
            [
                f"<font color='{_HEX_SUPPRESSED}' size=8><b>{escape(r.control_id)}</b><br/>{escape(r.control_name[:40])}</font>",
                f"<font color='{_HEX_TEXT_PRIMARY}' size=8>{escape(justification[:180])}</font>",
                f"<font color='{_HEX_TEXT_SECONDARY}' size=8>{escape(compensating[:180])}</font>",
                f"<font color='{_HEX_TEXT_SECONDARY}' size=8>{escape(suppressed_by)}<br/>Exp: {escape(expiry_str)}</font>",
            ]
        )

    table = Table(table_data, colWidths=[3.5 * cm, 5.5 * cm, 5.5 * cm, 3.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), SURFACE),
                ("TEXTCOLOR", (0, 0), (-1, 0), ACCENT),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 1), (-1, -1), NAVY),
                ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_PRIMARY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [NAVY, SURFACE]),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ]
        )
    )
    story.append(table)
    return story

