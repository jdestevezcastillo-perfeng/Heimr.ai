# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Agent configuration — extends base Heimr config with agent-specific settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentConfig:
    """
    Configuration for the Heimr agent runner.

    Attributes:
        results_file: Path to load test results (k6 JSON, JTL, etc.)
        config: Base Heimr config dict (from heimr.yaml)
        mode: "autonomous" runs without human interaction;
              "supervised" pauses before irreversible actions.
        max_iterations: Safety limit on ReAct loop iterations.
        gate_policy: "strict" fails the pipeline on violations;
                     "advisory" only reports findings.
        output_targets: Where to write results.
        llm_url: Override LLM endpoint.
        llm_model: Override LLM model.
        prometheus: Prometheus URL or file path.
        loki: Loki URL or file path.
        tempo: Tempo URL or file path.
        fail_conditions: List of conditions like "p99_latency > 500".
        compare_baseline: Path to baseline results for regression detection.
        jvm_thread_dump: Path to thread dump file.
        jvm_heap_dump: Path to heap histogram file.
        jvm_gc_log: Path to GC log file.
        verbose: Whether to print reasoning steps to stdout.
    """

    results_file: str = ""
    config: Dict[str, Any] = field(default_factory=dict)

    # Agent behavior
    mode: str = "autonomous"  # "autonomous" | "supervised"
    max_iterations: int = 10
    gate_policy: str = "strict"  # "strict" | "advisory"
    output_targets: List[str] = field(
        default_factory=lambda: ["github_summary", "report"]
    )
    verbose: bool = False

    # LLM settings (override config)
    llm_url: Optional[str] = None
    llm_model: Optional[str] = None

    # Observability sources
    prometheus: Optional[str] = None
    loki: Optional[str] = None
    tempo: Optional[str] = None

    # Gating
    fail_conditions: Optional[List[str]] = None
    compare_baseline: Optional[str] = None

    # JVM
    jvm_thread_dump: Optional[str] = None
    jvm_heap_dump: Optional[str] = None
    jvm_gc_log: Optional[str] = None

    @classmethod
    def from_heimr_config(cls, config: Dict[str, Any], **overrides) -> "AgentConfig":
        """
        Build AgentConfig from a standard heimr.yaml config dict,
        with CLI overrides taking precedence.
        """
        agent_section = config.get("agent", {})

        kwargs = {
            "config": config,
            "mode": agent_section.get("mode", "autonomous"),
            "max_iterations": int(agent_section.get("max_iterations", 10)),
            "gate_policy": agent_section.get("gate_policy", "strict"),
            "output_targets": agent_section.get(
                "output_targets", ["github_summary", "report"]
            ),
            "verbose": agent_section.get("verbose", False),
            "llm_url": config.get("llm_url"),
            "llm_model": config.get("llm_model"),
            "prometheus": config.get("prometheus"),
            "loki": config.get("loki"),
            "tempo": config.get("tempo"),
            "fail_conditions": config.get("fail_conditions"),
        }

        # CLI overrides win
        for key, value in overrides.items():
            if value is not None:
                kwargs[key] = value

        return cls(**kwargs)
