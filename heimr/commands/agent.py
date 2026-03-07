# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import os
import sys


def handle_agent(args, load_config, normalize_config, print_banner):
    """Handle the 'agent' CLI command."""
    from heimr.agent.config import AgentConfig
    from heimr.agent.react_loop import AgentRunner

    # Load config
    config = {}
    if args.config:
        config = load_config(args.config)
    else:
        config = normalize_config(config)

    # Configure logging
    if args.log_level:
        import logging
        logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    # Build AgentConfig
    agent_config = AgentConfig.from_heimr_config(
        config,
        results_file=args.file,
        mode=args.mode,
        gate_policy=args.gate_policy,
        max_iterations=args.max_iterations,
        verbose=args.verbose,
        llm_url=args.llm_url,
        llm_model=args.llm_model,
        prometheus=args.prometheus,
        loki=args.loki,
        tempo=args.tempo,
        fail_conditions=getattr(args, "fail_condition", None),
    )

    print_banner()
    print(f"🤖 Heimr Agent — {agent_config.mode} mode")
    print(f"📁 Results: {args.file}")
    print(f"🚦 Gate policy: {agent_config.gate_policy}")
    print(f"🔄 Max iterations: {agent_config.max_iterations}")
    print()

    # Run agent
    runner = AgentRunner(agent_config)
    result = runner.run(task=args.task)

    # Print verdict
    print("\n" + "=" * 60)
    if result.error:
        print(f"❌ Agent Error: {result.error}")
    else:
        print(f"📋 Verdict:\n{result.verdict}")
    print(f"\n⏱️  Completed in {result.elapsed_seconds:.1f}s ({result.total_iterations} iterations)")
    print("=" * 60)

    # CI/CD artifacts
    if getattr(args, "ci_summary", None):
        try:
            from heimr.reporting.github import GitHubReporter
            output_path = None if args.ci_summary == "GITHUB_STEP_SUMMARY" else args.ci_summary
            gh = GitHubReporter(output_path=output_path)
            summary_lines = [f"# 🤖 Heimr Agent Analysis\n"]
            summary_lines.append(f"**Verdict:** {'✅ APPROVED' if result.exit_code == 0 else '❌ REJECTED'}\n")
            summary_lines.append(f"**Iterations:** {result.total_iterations} | **Time:** {result.elapsed_seconds:.1f}s\n")
            summary_lines.append(f"\n{result.verdict}\n")
            with open(output_path or os.getenv("GITHUB_STEP_SUMMARY", "/dev/null"), "a") as f:
                f.write("\n".join(summary_lines))
        except Exception as e:
            print(f"Warning: Failed to write GitHub Summary: {e}", file=sys.stderr)

    # Save audit trail
    audit_path = args.file.rsplit(".", 1)[0] + "_agent_audit.json"
    try:
        import json
        with open(audit_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        print(f"📝 Audit trail saved to: {audit_path}")
    except Exception as e:
        print(f"Warning: Failed to save audit trail: {e}", file=sys.stderr)

    sys.exit(result.exit_code)
