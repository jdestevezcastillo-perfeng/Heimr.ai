# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Heimr.ai - AI-Powered Load Test Analysis & Root Cause Explanation
"""

from importlib.metadata import version, PackageNotFoundError

from heimr.analyzer import Analyzer, AnalysisResult

try:
    __version__ = version("heimr-ai")
except PackageNotFoundError:
    __version__ = "0.2.0"

__all__ = ["Analyzer", "AnalysisResult", "__version__"]
