# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import os
import sys

from heimr.analyzer import Analyzer
from heimr.services.analysis import build_analyzer_config_from_args, run_analysis
from heimr.services.reporting import REPORTS_EXTRA_HINT, write_analysis_reports


def handle_analyze(args, load_config, normalize_config, merge_config_with_args,
                   print_banner, print_result_summary):
    """Handle the 'analyze' CLI command."""

    # Load and merge config
    config = {}
    if args.config:
        config = load_config(args.config)
    else:
        config = normalize_config(config)
    args = merge_config_with_args(args, config)

    # Warn if deprecated --explain was used
    if getattr(args, "explain", False):
        print("Warning: --explain is deprecated; AI analysis runs by default.")

    # Configure logging if requested
    if args.log_level:
        import logging
        logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    print_banner()
    print(f"Analyzing {args.file}...")

    # Helper for LLM streaming
    def stream_chunk(chunk):
        print(chunk, end="", flush=True)

    # Run Analysis
    analyzer = Analyzer(
        file_path=args.file,
        config=build_analyzer_config_from_args(args),
        llm_url=getattr(args, 'llm_url', None),
        llm_model=getattr(args, 'llm_model', None),
        prompt_template=getattr(args, 'prompt_template', None),
        no_llm=getattr(args, 'no_llm', False),
        jvm_thread_dump=getattr(args, 'jvm_thread_dump', None),
        jvm_heap_dump=getattr(args, 'jvm_heap_dump', None),
        jvm_gc_log=getattr(args, 'jvm_gc_log', None),
    )
    result = analyzer.analyze(stream_callback=stream_chunk)

    # Print Summary
    print_result_summary(result)

    report_paths = {}

    # --- Report Generation ---
    if args.output:
        print("\n--- Generating HTML Report (Interactive Charts) ---")
        print("\n--- Generating Markdown Report (Static Charts) ---")
        try:
            generated_paths, markdown_image_mode_ok = write_analysis_reports(result, args)
            report_paths.update(generated_paths)
            print(f"✅ HTML report saved to: {report_paths['HTML']}")
            print("   💡 Open in browser and press Ctrl+P to save as PDF")
            print(f"✅ Markdown report saved to: {report_paths['Markdown']}")
            if not markdown_image_mode_ok:
                print("⚠️ Saved Markdown with HTML charts (install kaleido for static images)")
        except Exception as e:
            print(f"Warning: Failed to generate Markdown with images: {e}")
            if str(e) == REPORTS_EXTRA_HINT:
                print(REPORTS_EXTRA_HINT)

    # --- Comparison Logic ---
    comparison_reasons = None
    if args.compare_baseline and args.output:
        print("\n--- Generating Comparison Report ---")
        try:
            from heimr.comparator import PerformanceComparator

            # Analyze baseline
            print(f"Loading baseline: {args.compare_baseline}")
            baseline_result = run_analysis(
                file_path=args.compare_baseline,
                config={
                    'prometheus': args.compare_prometheus,
                    'loki': args.compare_loki,
                    'tempo': args.compare_tempo,
                },
                no_llm=True,
            )

            comparator = PerformanceComparator(baseline_result.stats, result.stats)

            metrics_comparison = comparator.compare_metrics()
            anomalies_comparison = comparator.compare_anomalies(
                baseline_result.anomaly_summary, result.anomaly_summary
            )

            prometheus_comparison = None
            if baseline_result.prom_metrics and result.prom_metrics:
                prometheus_comparison = comparator.compare_prometheus(
                    baseline_result.prom_metrics, result.prom_metrics
                )

            logs_comparison = None
            if baseline_result.loki_logs and result.loki_logs:
                logs_comparison = comparator.compare_logs(
                    baseline_result.loki_logs, result.loki_logs
                )

            traces_comparison = None
            if baseline_result.tempo_traces and result.tempo_traces:
                traces_comparison = comparator.compare_traces(
                    baseline_result.tempo_traces, result.tempo_traces
                )

            comparison_report = comparator.generate_comparison_report(
                metrics_comparison,
                anomalies_comparison,
                prometheus_comparison,
                logs_comparison,
                traces_comparison
            )

            # Apply gating for baseline comparison
            gating = comparator.check_failure_conditions(
                metrics_comparison,
                fail_on_regression=args.fail_on_regression,
                fail_conditions=args.fail_condition
            )
            if gating.get("failed"):
                print("❌ Comparison gating failed:")
                for reason in gating.get("reasons", []):
                    print(f"  - {reason}")
                result.status = "FAILED"
                result.failure_signals.extend(gating.get("reasons", []))
                comparison_reasons = gating.get("reasons", [])

            comparison_path = args.output.rsplit('.', 1)[0] + '_comparison.md'
            with open(comparison_path, 'w') as f:
                f.write(comparison_report)
            print(f"✅ Comparison report saved to: {comparison_path}")
            report_paths["Comparison Markdown"] = comparison_path

            # Comparison PDF
            try:
                from heimr.reporting.pdf import PDFGenerator
                pdf_gen = PDFGenerator()
                pdf_path = comparison_path.rsplit('.', 1)[0] + '.pdf'
                pdf_gen.generate_pdf(comparison_report, pdf_path)
                print(f"✅ Comparison PDF saved to: {pdf_path}")
                report_paths["Comparison PDF"] = pdf_path
            except Exception as e:
                print(f"Warning: Failed to generate comparison PDF: {e}")

        except Exception as e:
            print(f"Warning: Failed to generate comparison report: {e}")
            import traceback
            traceback.print_exc()

    # --- CI/CD Artifacts ---
    tags_dict = None
    if getattr(args, "tag", None):
        tags_dict = {}
        for tag in args.tag:
            if '=' in tag:
                k, v = tag.split('=', 1)
                tags_dict[k] = v
            else:
                tags_dict[tag] = True

    if args.ci_summary:
        from heimr.reporting.github import GitHubReporter
        output_path = None if args.ci_summary == "GITHUB_STEP_SUMMARY" else args.ci_summary
        gh = GitHubReporter(output_path=output_path)
        gh.generate_summary(
            stats=result.stats,
            anomalies=result.anomaly_summary,
            failure_reasons=result.failure_signals,
            tags=tags_dict,
            report_paths=report_paths or None,
            comparison_reasons=comparison_reasons,
        )

    if args.junit_output:
        from heimr.reporting.junit import JUnitReporter
        junit = JUnitReporter(output_path=args.junit_output)
        junit.generate_report(
            stats=result.stats,
            anomalies=result.anomaly_summary,
            failure_reasons=result.failure_signals,
            tags=tags_dict,
        )

    # Exit code
    if result.status == "FAILED":
        sys.exit(1)
    sys.exit(0)
