# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from heimr.analyzer import Analyzer, AnalysisResult


def build_analyzer_config_from_args(args) -> Dict[str, Any]:
    """Build the standard Analyzer config dict from CLI-like args."""
    return {
        "prometheus": getattr(args, "prometheus", None),
        "loki": getattr(args, "loki", None),
        "tempo": getattr(args, "tempo", None),
        "llm_url": getattr(args, "llm_url", None),
        "llm_model": getattr(args, "llm_model", None),
        "prompt_template": getattr(args, "prompt_template", None),
        "disable_llm": getattr(args, "no_llm", False),
        "fail_conditions": getattr(args, "fail_condition", None),
        "llm_timeout_sec": getattr(args, "llm_timeout_sec", None),
        "llm_max_retries": getattr(args, "llm_max_retries", None),
        "detector_mode": getattr(args, "detector_mode", None),
        "trend_threshold": getattr(args, "trend_threshold", None),
        "grafana_url": getattr(args, "grafana_url", None),
        "grafana_dashboard_uid": getattr(args, "grafana_dashboard_uid", None),
    }


def run_analysis(
    file_path: str,
    config: Optional[Dict[str, Any]] = None,
    *,
    llm_url: Optional[str] = None,
    llm_model: Optional[str] = None,
    prompt_template: Optional[str] = None,
    no_llm: bool = False,
    jvm_thread_dump: Optional[str] = None,
    jvm_heap_dump: Optional[str] = None,
    jvm_gc_log: Optional[str] = None,
    stream_callback: Optional[Callable[[str], None]] = None,
) -> AnalysisResult:
    """Run the main analysis flow with a standardized Analyzer setup."""
    analyzer = Analyzer(
        file_path=file_path,
        config=config or {},
        llm_url=llm_url,
        llm_model=llm_model,
        prompt_template=prompt_template,
        no_llm=no_llm,
        jvm_thread_dump=jvm_thread_dump,
        jvm_heap_dump=jvm_heap_dump,
        jvm_gc_log=jvm_gc_log,
    )
    return analyzer.analyze(stream_callback=stream_callback)


def run_analysis_from_args(args, *, stream_callback: Optional[Callable[[str], None]] = None) -> AnalysisResult:
    """Run analysis using the shared CLI/web argument contract."""
    config = build_analyzer_config_from_args(args)
    return run_analysis(
        file_path=args.file,
        config=config,
        llm_url=getattr(args, "llm_url", None),
        llm_model=getattr(args, "llm_model", None),
        prompt_template=getattr(args, "prompt_template", None),
        no_llm=getattr(args, "no_llm", False),
        jvm_thread_dump=getattr(args, "jvm_thread_dump", None),
        jvm_heap_dump=getattr(args, "jvm_heap_dump", None),
        jvm_gc_log=getattr(args, "jvm_gc_log", None),
        stream_callback=stream_callback,
    )
