# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

from __future__ import annotations

from typing import Dict, Tuple

from heimr.analyzer import AnalysisResult
from heimr.reporting.markdown import generate_markdown_report_content

REPORTS_EXTRA_HINT = "Install report dependencies with `pip install heimr-ai[reports]`."


def generate_markdown_report(result: AnalysisResult, args) -> str:
    """Generate markdown report content using the shared reporting pipeline."""
    return generate_markdown_report_content(result, args)


def write_analysis_reports(result: AnalysisResult, args) -> Tuple[Dict[str, str], bool]:
    """
    Generate analysis reports from a shared implementation.

    Returns `(report_paths, markdown_image_mode_ok)`.
    """
    try:
        from heimr.reporting.charts import ReportCharts
        from heimr.reporting.html import HTMLReportGenerator
    except ImportError as exc:
        raise RuntimeError(REPORTS_EXTRA_HINT) from exc

    report_paths: Dict[str, str] = {}

    ReportCharts.set_output_mode("html")
    html_content = generate_markdown_report(result, args)

    html_gen = HTMLReportGenerator()
    html_path = args.output.rsplit(".", 1)[0] + ".html"
    html_gen.generate_html(html_content, html_path)
    report_paths["HTML"] = html_path

    markdown_image_mode_ok = True
    try:
        ReportCharts.set_output_mode("image")
        md_content = generate_markdown_report(result, args)
        md_path = args.output.rsplit(".", 1)[0] + ".md"
        with open(md_path, "w") as f:
            f.write(md_content)
        report_paths["Markdown"] = md_path
    except Exception:
        markdown_image_mode_ok = False
        ReportCharts.set_output_mode("html")
        fallback_content = generate_markdown_report(result, args)
        with open(args.output, "w") as f:
            f.write(fallback_content)
        report_paths["Markdown"] = args.output
    finally:
        ReportCharts.set_output_mode("html")

    return report_paths, markdown_image_mode_ok
