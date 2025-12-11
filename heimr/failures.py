# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Failure condition parsing and evaluation.
Shared between single-run analysis and baseline comparison.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FailureCheckResult:
    failed: bool
    reasons: List[str]


def parse_failure_condition(condition: str) -> Optional[Tuple[str, str, float]]:
    """
    Parse a condition like "p99_latency > 500".
    Returns (metric_name, operator, threshold) or None if invalid.
    """
    if not condition or not isinstance(condition, str):
        return None
    parts = condition.split()
    if len(parts) != 3:
        return None
    metric_name, op, threshold_str = parts
    try:
        threshold = float(threshold_str)
    except ValueError:
        return None
    if op not in {">", ">=", "<", "<="}:
        return None
    return metric_name, op, threshold


def evaluate_failure_conditions(
    current_stats: Dict[str, Any],
    fail_conditions: Optional[List[str]] = None,
) -> FailureCheckResult:
    """
    Evaluate a list of absolute failure conditions against current_stats.
    """
    failed = False
    reasons: List[str] = []
    if not fail_conditions:
        return FailureCheckResult(False, [])

    for condition in fail_conditions:
        parsed = parse_failure_condition(condition)
        if not parsed:
            reasons.append(f"Invalid failure condition format: '{condition}'")
            continue
        metric_name, op, threshold = parsed
        if metric_name not in current_stats:
            reasons.append(f"Unknown metric in condition: '{metric_name}'")
            continue
        try:
            value = float(current_stats[metric_name])
        except Exception:
            reasons.append(f"Non-numeric metric in condition: '{metric_name}'")
            continue

        condition_met = False
        if op == ">":
            condition_met = value > threshold
        elif op == ">=":
            condition_met = value >= threshold
        elif op == "<":
            condition_met = value < threshold
        elif op == "<=":
            condition_met = value <= threshold

        if condition_met:
            failed = True
            reasons.append(f"Failure condition met: {metric_name} ({value}) {op} {threshold}")

    return FailureCheckResult(failed, reasons)

