# LogRaven — PDF Report Generator
#
# Strategy:
#   1. Try WeasyPrint (best quality — requires GTK3 system libs, works in Docker/Linux)
#   2. Fall back to xhtml2pdf (pure Python — works on Windows without system deps)
#
# Both renderers consume the same Jinja2 HTML template, so the output is
# functionally identical; only CSS fidelity differs slightly on Windows.

import os

from app.utils.logger import get_logger

logger = get_logger(__name__)

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _render_html(report, findings: list) -> str:
    """Render the Jinja2 HTML template and return the HTML string."""
    try:
        import jinja2
    except ImportError:
        raise ImportError("Jinja2 not installed. Run: pip install jinja2")

    from app.reports.builder import build_report_context
    context = build_report_context(report, findings)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    template = env.get_template("lograven_report.html")
    return template.render(**context)


def _write_with_weasyprint(html_content: str, css_path: str, output_path: str) -> None:
    """Render PDF using WeasyPrint (Linux/Docker — needs GTK3)."""
    from weasyprint import HTML, CSS
    base_url = _TEMPLATES_DIR + os.sep
    pdf_bytes = HTML(string=html_content, base_url=base_url).write_pdf(
        stylesheets=[CSS(filename=css_path)]
    )
    with open(output_path, "wb") as fh:
        fh.write(pdf_bytes)


def _write_with_xhtml2pdf(html_content: str, output_path: str) -> None:
    """Render PDF using xhtml2pdf (pure Python — works on Windows)."""
    from xhtml2pdf import pisa

    with open(output_path, "wb") as fh:
        result = pisa.CreatePDF(html_content, dest=fh, encoding="utf-8")

    if result.err:
        raise RuntimeError(f"xhtml2pdf reported {result.err} error(s) while generating PDF")


def generate_pdf(report, findings: list, output_dir: str) -> str:
    """
    Render a LogRaven report to PDF.

    Tries WeasyPrint first; if GTK3 is unavailable (common on Windows dev
    machines) falls back to xhtml2pdf which has no system-level dependencies.

    Args:
        report:     Report ORM object
        findings:   list of Finding ORM objects
        output_dir: directory to write the PDF into

    Returns:
        Absolute path to the generated PDF file.
    """
    html_content = _render_html(report, findings)
    css_path     = os.path.join(_TEMPLATES_DIR, "lograven_report.css")

    os.makedirs(output_dir, exist_ok=True)
    filename    = f"lograven-report-{str(report.id)[:8]}.pdf"
    output_path = os.path.join(output_dir, filename)

    # ── Try WeasyPrint ────────────────────────────────────────────────────────
    try:
        _write_with_weasyprint(html_content, css_path, output_path)
        logger.info("LogRaven PDF [weasyprint]: %s (%d bytes)", output_path, os.path.getsize(output_path))
        return output_path
    except Exception as wp_err:
        # WeasyPrint fails on Windows without GTK3 — fall through to xhtml2pdf
        logger.warning("WeasyPrint unavailable (%s) — falling back to xhtml2pdf", wp_err)

    # ── Fall back to xhtml2pdf ────────────────────────────────────────────────
    _write_with_xhtml2pdf(html_content, output_path)
    logger.info("LogRaven PDF [xhtml2pdf]: %s (%d bytes)", output_path, os.path.getsize(output_path))
    return output_path
