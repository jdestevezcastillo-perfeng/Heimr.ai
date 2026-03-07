# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import os
import sys

from heimr.analyzer import Analyzer


def handle_analyze(args, load_config, normalize_config, merge_config_with_args,
                   print_banner, print_result_summary, generate_markdown_report_content):
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

    # Build config dict for Analyzer
    analyzer_config = {
        'prometheus': args.prometheus,
        'loki': args.loki,
        'tempo': args.tempo,
        'llm_url': args.llm_url,
        'llm_model': args.llm_model,
        'prompt_template': getattr(args, 'prompt_template', None),
        'disable_llm': args.no_llm,
        'fail_conditions': getattr(args, 'fail_condition', None),
        'llm_timeout_sec': args.llm_timeout_sec,
        'llm_max_retries': args.llm_max_retries,
        'detector_mode': args.detector_mode,
        'trend_threshold': args.trend_threshold,
        'grafana_url': args.grafana_url,
        'grafana_dashboard_uid': args.grafana_dashboard_uid,
    }

    # Configure logging if requested
    if args.log_level:
        import logging
        logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    print_banner()
    print(f"Analyzing {args.file}...")

    # Initialize Analyzer
    analyzer = Analyzer(
        file_path=args.file,
        config=analyzer_config,
        llm_url=args.llm_url,
        llm_model=args.llm_model,
        prompt_template=getattr(args, 'prompt_template', None),
        no_llm=args.no_llm,
        jvm_thread_dump=getattr(args, 'jvm_thread_dump', None),
        jvm_heap_dump=getattr(args, 'jvm_heap_dump', None),
        jvm_gc_log=getattr(args, 'jvm_gc_log', None)
    )

    # Helper for LLM streaming
    def stream_chunk(chunk):
        print(chunk, end="", flush=True)

    # Run Analysis
    result = analyzer.analyze(stream_callback=stream_chunk)

    # Print Summary
    print_result_summary(result)

    report_paths = {}

    # --- Report Generation ---
    if args.output:
        # Step 1: Generate HTML report with interactive Plotly charts
        print("\n--- Generating HTML Report (Interactive Charts) ---")
        try:
            from heimr.reporting.charts import ReportCharts
            from heimr.reporting.html import HTMLReportGenerator

            # Use HTML mode for interactive charts
            ReportCharts.set_output_mode('html')
            html_content = generate_markdown_report_content(result, args)

            html_gen = HTMLReportGenerator()
            html_path = args.output.rsplit('.', 1)[0] + '.html'
            html_gen.generate_html(html_content, html_path)
            print(f"✅ HTML report saved to: {html_path}")
            print("   💡 Open in browser and press Ctrl+P to save as PDF")
            report_paths["HTML"] = html_path
        except Exception as e:
            print(f"Warning: Failed to generate HTML: {e}")
            import traceback
            traceback.print_exc()

        # Step 2: Generate Markdown report with static PNG charts (for GitHub/GitLab)
        print("\n--- Generating Markdown Report (Static Charts) ---")
        try:
            from heimr.reporting.charts import ReportCharts

            # Switch to image mode for static PNG charts
            ReportCharts.set_output_mode('image')
            md_content = generate_markdown_report_content(result, args)

            # Use .md extension for markdown file
            md_path = args.output.rsplit('.', 1)[0] + '.md'
            with open(md_path, "w") as f:
                f.write(md_content)
            print(f"✅ Markdown report saved to: {md_path}")
            report_paths["Markdown"] = md_path

            # Reset to HTML mode
            ReportCharts.set_output_mode('html')
        except Exception as e:
            print(f"Warning: Failed to generate Markdown with images: {e}")
            # Fallback: save with HTML charts (may not render in GitHub)
            from heimr.reporting.charts import ReportCharts
            ReportCharts.set_output_mode('html')
            fallback_content = generate_markdown_report_content(result, args)
            with open(args.output, "w") as f:
                f.write(fallback_content)
            print(f"⚠️ Saved Markdown with HTML charts (install kaleido for static images)")
            report_paths["Markdown"] = args.output

    # --- Comparison Logic ---
    comparison_reasons = None
    if args.compare_baseline and args.output:
        print("\n--- Generating Comparison Report ---")
        try:
            from heimr.comparator import PerformanceComparator

            # Analyze baseline
            print(f"Loading baseline: {args.compare_baseline}")
            baseline_config = {
                'prometheus': args.compare_prometheus,
                'loki': args.compare_loki,
                'tempo': args.compare_tempo
            }
            baseline_analyzer = Analyzer(
                file_path=args.compare_baseline,
                config=baseline_config,
                no_llm=True
            )
            baseline_result = baseline_analyzer.analyze()

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
