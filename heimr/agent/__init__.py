# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Heimr Agent — Autonomous Performance Engineering Agent.

Implements a ReAct (Reason-Act-Observe) loop that uses existing Heimr
analysis capabilities as tools to autonomously analyze load test results,
correlate multi-signal data, and make deployment gate decisions.
"""

from heimr.agent.config import AgentConfig
from heimr.agent.react_loop import AgentRunner, AgentResult

__all__ = ["AgentRunner", "AgentConfig", "AgentResult"]
