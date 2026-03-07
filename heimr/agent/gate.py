# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Deployment gate — produces structured pass/fail/warn decisions
from an AnalysisResult + AgentConfig.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from heimr.analyzer import AnalysisResult
from heimr.failures import evaluate_failure_conditions


@dataclass
class GateDecision:
    """
    A structured deployment gate verdict.

    Attributes:
        verdict: "APPROVE", "REJECT", or "WARN".
        reasons: Human-readable reasons for the verdict.
        confidence: 0.0–1.0 score of how confident the decision is.
        recommendations: Actionable next steps.
        kpi_snapshot: Key metrics at decision time.
    """

    verdict: str  # "APPROVE" | "REJECT" | "WARN"
    reasons: List[str] = field(default_factory=list)
    confidence: float = 1.0
    recommendations: List[str] = field(default_factory=list)
    kpi_snapshot: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.verdict == "APPROVE"

    @property
    def exit_code(self) -> int:
        """Map verdict to Unix exit code."""
        if self.verdict == "APPROVE":
            return 0
        elif self.verdict == "WARN":
            return 0  # Advisory — don't break the pipeline
        else:
            return 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "reasons": self.reasons,
            "confidence": self.confidence,
            "recommendations": self.recommendations,
            "kpi_snapshot": self.kpi_snapshot,
        }


def evaluate_gate(
    result: AnalysisResult,
    fail_conditions: Optional[List[str]] = None,
    gate_policy: str = "strict",
) -> GateDecision:
    """
    Evaluate a deployment gate from an AnalysisResult.

    This formalizes the existing failure_signals logic into a richer
    decision structure.  The gate inspects:
      1. Failure signals already detected by the Analyzer
      2. Explicit fail_conditions (e.g. "p99_latency > 500")
      3. Anomaly severity
      4. Error rates

    Args:
        result: The AnalysisResult from Analyzer.analyze().
        fail_conditions: Optional list of condition strings.
        gate_policy: "strict" → REJECT on violations; "advisory" → WARN only.

    Returns:
        GateDecision with verdict, reasons, and recommendations.
    """
    reasons: List[str] = []
    recommendations: List[str] = []
    confidence = 1.0

    # ------------------------------------------------------------------
    # 1. Check existing failure signals from Analyzer
    # ------------------------------------------------------------------
    if result.failure_signals:
        reasons.extend(result.failure_signals)

    # ------------------------------------------------------------------
    # 2. Evaluate explicit fail_conditions
    # ------------------------------------------------------------------
    if fail_conditions:
        fc_result = evaluate_failure_conditions(result.stats, fail_conditions)
        if fc_result.failed:
            reasons.extend(fc_result.reasons)

    # ------------------------------------------------------------------
    # 3. Anomaly severity analysis
    # ------------------------------------------------------------------
    anomaly_count = result.anomaly_summary.get("count", 0)
    if anomaly_count > 0:
        avg_anomaly_latency = result.anomaly_summary.get("avg_latency", 0)
        avg_normal_latency = result.stats.get("avg_latency", 1)

        if avg_normal_latency > 0:
            severity_ratio = avg_anomaly_latency / avg_normal_latency
        else:
            severity_ratio = 0

        if severity_ratio > 5:
            recommendations.append(
                f"Anomaly latency is {severity_ratio:.1f}x normal — "
                f"investigate endpoint-level breakdown"
            )
        elif severity_ratio > 2:
            recommendations.append(
                f"Anomaly latency is {severity_ratio:.1f}x normal — "
                f"monitor in production"
            )

    # ------------------------------------------------------------------
    # 4. Error rate analysis
    # ------------------------------------------------------------------
    error_rate = result.stats.get("error_rate", 0)
    if error_rate > 5.0:
        recommendations.append(
            f"Error rate {error_rate:.2f}% is critically high — "
            f"do not deploy without fixing"
        )
    elif error_rate > 1.0:
        recommendations.append(
            f"Error rate {error_rate:.2f}% is elevated — "
            f"review error logs before deploying"
        )

    # ------------------------------------------------------------------
    # 5. LLM analysis availability affects confidence
    # ------------------------------------------------------------------
    if result.llm_error:
        confidence *= 0.7  # Less confident without AI analysis
        recommendations.append(
            f"AI analysis failed ({result.llm_error}) — "
            f"decision based on statistical signals only"
        )
    elif not result.llm_explanation:
        confidence *= 0.8

    # ------------------------------------------------------------------
    # 6. Build KPI snapshot
    # ------------------------------------------------------------------
    kpi_snapshot = {
        "total_requests": result.stats.get("total_requests", 0),
        "error_rate": error_rate,
        "p50_latency": result.stats.get("p50_latency", 0),
        "p95_latency": result.stats.get("p95_latency", 0),
        "p99_latency": result.stats.get("p99_latency", 0),
        "throughput": result.stats.get("throughput", 0),
        "anomaly_count": anomaly_count,
    }

    # ------------------------------------------------------------------
    # 7. Determine verdict
    # ------------------------------------------------------------------
    if not reasons:
        verdict = "APPROVE"
    elif gate_policy == "advisory":
        verdict = "WARN"
    else:
        verdict = "REJECT"

    return GateDecision(
        verdict=verdict,
        reasons=reasons,
        confidence=confidence,
        recommendations=recommendations,
        kpi_snapshot=kpi_snapshot,
    )
