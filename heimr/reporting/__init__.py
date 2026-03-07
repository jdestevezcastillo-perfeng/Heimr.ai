# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

from heimr.reporting.markdown import (
    create_correlation_chart,
    detect_timeline_mismatch,
    enhance_llm_output,
    extract_llm_tldr,
)

__all__ = [
    "create_correlation_chart",
    "detect_timeline_mismatch",
    "enhance_llm_output",
    "extract_llm_tldr",
    # Lazy-imported in consumers; listed here for discoverability:
    # "ReportCharts",        # from heimr.reporting.charts
    # "HTMLReportGenerator", # from heimr.reporting.html
    # "PDFGenerator",        # from heimr.reporting.pdf
    # "GitHubReporter",      # from heimr.reporting.github
    # "JUnitReporter",       # from heimr.reporting.junit
]
