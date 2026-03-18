# LogRaven — PDF Report Generator

import os

from app.utils.logger import get_logger

logger = get_logger(__name__)

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def generate_pdf(report, findings: list, output_dir: str) -> str:
    """
    Render a LogRaven report to PDF using WeasyPrint + Jinja2.

    Args:
        report:     Report ORM object
        findings:   list of Finding ORM objects
        output_dir: directory to write the PDF into

    Returns:
        Absolute path to the generated PDF file.
    """
    try:
        import jinja2
    except ImportError:
        raise ImportError("Jinja2 not installed. Run: pip install jinja2")

    try:
        from weasyprint import HTML, CSS
    except ImportError:
        raise ImportError("WeasyPrint not installed. Run: pip install weasyprint")

    from app.reports.builder import build_report_context

    # ── Build template context ────────────────────────────────────────────────
    context = build_report_context(report, findings)

    # ── Render HTML ───────────────────────────────────────────────────────────
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    template = env.get_template("lograven_report.html")
    html_content = template.render(**context)

    # ── Generate PDF ──────────────────────────────────────────────────────────
    css_path = os.path.join(_TEMPLATES_DIR, "lograven_report.css")

    # WeasyPrint resolves relative CSS hrefs against base_url
    # Passing base_url ensures the <link> tag in the template resolves correctly
    base_url = _TEMPLATES_DIR + os.sep

    pdf_bytes = HTML(string=html_content, base_url=base_url).write_pdf(
        stylesheets=[CSS(filename=css_path)]
    )

    # ── Write to disk ─────────────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    filename = f"lograven-report-{str(report.id)[:8]}.pdf"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "wb") as fh:
        fh.write(pdf_bytes)

    logger.info("LogRaven PDF: generated %s (%d bytes)", output_path, len(pdf_bytes))
    return output_path
