# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
ReAct (Reason-Act-Observe) agent loop for autonomous performance engineering.

The agent receives a task (e.g. "analyze this k6 run and decide whether to
deploy"), uses Heimr tools to gather data, reasons about the results, and
produces a final verdict with an audit trail.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional

from heimr.agent.config import AgentConfig
from heimr.agent.tools import (
    TOOL_REGISTRY,
    execute_tool,
    get_tools_description,
)

logger = logging.getLogger("heimr.agent")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AgentStep:
    """One Reason→Act→Observe cycle."""

    iteration: int
    thought: str  # The agent's reasoning
    action: str  # Tool name or "FINISH"
    action_input: Dict[str, Any]  # Tool arguments
    observation: str  # Tool output (stringified)
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation[:2000],  # Cap for serialization
            "timestamp": self.timestamp,
        }


@dataclass
class AgentResult:
    """
    Final output of an agent run.

    Attributes:
        verdict: The agent's final summary/decision.
        steps: Full audit trail of Reason→Act→Observe cycles.
        exit_code: 0 = success/approve, 1 = reject/error.
        total_iterations: Number of ReAct cycles executed.
        elapsed_seconds: Wall time for the full run.
        error: Error message if the agent failed.
    """

    verdict: str = ""
    steps: List[AgentStep] = field(default_factory=list)
    exit_code: int = 0
    total_iterations: int = 0
    elapsed_seconds: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "steps": [s.to_dict() for s in self.steps],
            "exit_code": self.exit_code,
            "total_iterations": self.total_iterations,
            "elapsed_seconds": self.elapsed_seconds,
            "error": self.error,
        }

    @property
    def audit_trail(self) -> str:
        """Human-readable audit trail."""
        lines = []
        for step in self.steps:
            lines.append(f"--- Step {step.iteration} ---")
            lines.append(f"Thought: {step.thought}")
            lines.append(f"Action: {step.action}")
            if step.action != "FINISH":
                lines.append(f"Input: {json.dumps(step.action_input, default=str)}")
                lines.append(f"Observation: {step.observation[:500]}")
            lines.append("")
        lines.append(f"--- Final Verdict ---")
        lines.append(self.verdict)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Heimr, an autonomous performance engineering agent.
Your job is to analyze load test results, correlate signals from multiple
observability sources, and make deployment gate decisions.

You operate in a Reason→Act→Observe loop:
1. THINK about what information you need next
2. Choose a TOOL to gather that information
3. OBSERVE the tool's output
4. Repeat until you have enough data to make a decision

## Available Tools

{tools_description}

## Response Format

You MUST respond in EXACTLY this format (no extra text outside this structure):

THOUGHT: <your reasoning about what to do next>
ACTION: <tool_name>
ACTION_INPUT: <valid JSON object with tool arguments>

When you have gathered enough information and are ready to deliver your final
analysis and verdict, use:

THOUGHT: <your final reasoning>
ACTION: FINISH
ACTION_INPUT: {{"verdict": "<your complete analysis and deployment recommendation>"}}

## Important Rules

1. Always start by parsing the load test file to understand what data is available.
2. Then compute KPIs to get the quantitative picture.
3. Use anomaly detection to find statistical outliers.
4. Query observability sources (Prometheus, Loki, Tempo) if configured.
5. End with evaluate_gate to produce a deployment decision.
6. Correlate signals across all sources — don't analyze them in isolation.
7. Be specific: cite actual numbers, endpoint names, timestamps.
8. If a tool errors, reason about why and try an alternative approach.
9. Keep your analysis concise and actionable.
"""


def _build_system_prompt(config: AgentConfig) -> str:
    """Build the system prompt with tool descriptions injected."""
    tools_desc = get_tools_description()
    prompt = SYSTEM_PROMPT.format(tools_description=tools_desc)

    # Add context about available observability sources
    context_lines = ["\n## Current Configuration"]
    if config.results_file:
        context_lines.append(f"- Load test results: {config.results_file}")
    if config.prometheus:
        context_lines.append(f"- Prometheus: {config.prometheus}")
    if config.loki:
        context_lines.append(f"- Loki: {config.loki}")
    if config.tempo:
        context_lines.append(f"- Tempo: {config.tempo}")
    if config.fail_conditions:
        context_lines.append(f"- Fail conditions: {config.fail_conditions}")
    if config.gate_policy:
        context_lines.append(f"- Gate policy: {config.gate_policy}")

    prompt += "\n".join(context_lines) + "\n"
    return prompt


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def _parse_agent_response(text: str) -> Dict[str, Any]:
    """
    Parse the LLM's structured response into thought/action/input.

    Expected format:
        THOUGHT: ...
        ACTION: tool_name
        ACTION_INPUT: {"key": "value"}

    Returns dict with keys: thought, action, action_input.
    """
    result = {"thought": "", "action": "", "action_input": {}}

    lines = text.strip().split("\n")
    current_section = None
    current_content: List[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("THOUGHT:"):
            if current_section:
                result[current_section] = "\n".join(current_content).strip()
            current_section = "thought"
            current_content = [stripped[len("THOUGHT:"):].strip()]
        elif stripped.upper().startswith("ACTION_INPUT:"):
            if current_section:
                result[current_section] = "\n".join(current_content).strip()
            current_section = "action_input_raw"
            current_content = [stripped[len("ACTION_INPUT:"):].strip()]
        elif stripped.upper().startswith("ACTION:"):
            if current_section:
                result[current_section] = "\n".join(current_content).strip()
            current_section = "action"
            current_content = [stripped[len("ACTION:"):].strip()]
        else:
            current_content.append(line)

    # Flush last section
    if current_section:
        result[current_section] = "\n".join(current_content).strip()

    # Parse action_input JSON
    raw_input = result.pop("action_input_raw", "")
    if raw_input:
        try:
            result["action_input"] = json.loads(raw_input)
        except json.JSONDecodeError:
            # Try to extract JSON from the raw string
            try:
                start = raw_input.index("{")
                end = raw_input.rindex("}") + 1
                result["action_input"] = json.loads(raw_input[start:end])
            except (ValueError, json.JSONDecodeError):
                result["action_input"] = {"_raw": raw_input}

    return result


# ---------------------------------------------------------------------------
# Agent Runner
# ---------------------------------------------------------------------------

class AgentRunner:
    """
    Runs the ReAct loop using the configured LLM and Heimr tools.

    Usage:
        config = AgentConfig(results_file="k6.json", ...)
        runner = AgentRunner(config)
        result = runner.run("Analyze this k6 run and decide whether to deploy")
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self._llm = None
        self._build_llm()

    def _build_llm(self):
        """Initialize the LLM client from config."""
        from heimr.llm import LLMClient

        llm_url = self.config.llm_url or self.config.config.get("llm_url")
        llm_model = self.config.llm_model or self.config.config.get("llm_model", "medium")

        # Normalize llm_url
        if isinstance(llm_url, str) and llm_url.startswith("http"):
            if not llm_url.rstrip("/").endswith("/v1"):
                llm_url = llm_url.rstrip("/") + "/v1"

        # Determine URL if not set
        if not llm_url:
            has_api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if not has_api_key:
                llm_url = "http://localhost:11434/v1"

        self._llm = LLMClient(
            base_url=llm_url,
            model=llm_model,
            timeout_sec=self.config.config.get("llm_timeout_sec"),
            max_retries=int(self.config.config.get("llm_max_retries", 1) or 1),
        )

    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call the LLM with a list of messages and return the full response."""
        if self._llm.provider == "anthropic":
            return self._call_anthropic(messages)
        else:
            return self._call_openai_compatible(messages)

    def _call_openai_compatible(self, messages: List[Dict[str, str]]) -> str:
        """Call OpenAI-compatible API (OpenAI, Ollama, vLLM)."""
        from openai import OpenAI

        base_url = self._llm.base_url or "http://localhost:11434/v1"
        api_key = os.environ.get("OPENAI_API_KEY", "not-needed")

        client = OpenAI(api_key=api_key, base_url=base_url)
        model = self._llm.model or "qwen3.5:9b"

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,  # Low temp for deterministic tool selection
            max_tokens=2000,
            timeout=self._llm.timeout_sec,
        )
        return response.choices[0].message.content or ""

    def _call_anthropic(self, messages: List[Dict[str, str]]) -> str:
        """Call Anthropic API."""
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        client = anthropic.Anthropic(api_key=api_key)
        model = self._llm.model or "claude-sonnet-4-20250514"

        # Separate system from user messages
        system_text = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text += msg["content"] + "\n"
            else:
                user_messages.append(msg)

        response = client.messages.create(
            model=model,
            max_tokens=2000,
            temperature=0.1,
            system=system_text,
            messages=user_messages,
        )
        return response.content[0].text

    def run(self, task: str = None) -> AgentResult:
        """
        Execute the ReAct loop.

        Args:
            task: The high-level task description. If not provided,
                  a default task is constructed from the config.

        Returns:
            AgentResult with verdict, audit trail, and exit code.
        """
        start_time = time.time()

        if not task:
            task = self._default_task()

        system_prompt = _build_system_prompt(self.config)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"TASK: {task}"},
        ]

        steps: List[AgentStep] = []
        result = AgentResult()

        for iteration in range(1, self.config.max_iterations + 1):
            if self.config.verbose:
                print(f"\n{'='*60}")
                print(f"🔄 Iteration {iteration}/{self.config.max_iterations}")
                print(f"{'='*60}")

            # --- Reason ---
            try:
                llm_response = self._call_llm(messages)
            except Exception as e:
                logger.error("LLM call failed at iteration %d: %s", iteration, e)
                result.error = f"LLM call failed: {e}"
                result.exit_code = 1
                break

            parsed = _parse_agent_response(llm_response)
            thought = parsed.get("thought", "")
            action = parsed.get("action", "").strip()
            action_input = parsed.get("action_input", {})

            if self.config.verbose:
                print(f"💭 Thought: {thought}")
                print(f"🔧 Action: {action}")
                if action != "FINISH":
                    print(f"📥 Input: {json.dumps(action_input, default=str)}")

            # --- FINISH ---
            if action.upper() == "FINISH":
                verdict = action_input.get("verdict", thought)
                step = AgentStep(
                    iteration=iteration,
                    thought=thought,
                    action="FINISH",
                    action_input=action_input,
                    observation="",
                    timestamp=time.time(),
                )
                steps.append(step)
                result.verdict = verdict
                result.exit_code = 0

                if self.config.verbose:
                    print(f"\n✅ Agent finished in {iteration} iterations")
                    print(f"📋 Verdict: {verdict[:200]}...")
                break

            # --- Act ---
            observation = execute_tool(action, action_input)
            observation_str = json.dumps(observation, default=str)

            # Cap observation size for LLM context
            if len(observation_str) > 4000:
                observation_str = observation_str[:4000] + "\n... (truncated)"

            step = AgentStep(
                iteration=iteration,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation_str,
                timestamp=time.time(),
            )
            steps.append(step)

            if self.config.verbose:
                status = observation.get("status", "unknown")
                icon = "✅" if status == "ok" else "❌"
                print(f"📤 Observation: {icon} {observation_str[:200]}")

            # --- Observe (feed back to LLM) ---
            messages.append({"role": "assistant", "content": llm_response})
            messages.append({
                "role": "user",
                "content": f"OBSERVATION:\n{observation_str}\n\nContinue your analysis.",
            })

        else:
            # Max iterations reached
            result.verdict = (
                f"Agent reached maximum iterations ({self.config.max_iterations}). "
                f"Partial analysis based on {len(steps)} steps."
            )
            result.exit_code = 1
            result.error = "Max iterations reached"

        result.steps = steps
        result.total_iterations = len(steps)
        result.elapsed_seconds = time.time() - start_time

        return result

    def _default_task(self) -> str:
        """Build a default task prompt from the config."""
        parts = [
            f"Analyze the load test results at '{self.config.results_file}'.",
        ]

        if self.config.prometheus:
            parts.append(f"Query Prometheus at '{self.config.prometheus}' for system metrics.")
        if self.config.loki:
            parts.append(f"Query Loki at '{self.config.loki}' for error logs.")
        if self.config.tempo:
            parts.append(f"Query Tempo at '{self.config.tempo}' for slow traces.")
        if self.config.fail_conditions:
            parts.append(
                f"Apply these fail conditions: {self.config.fail_conditions}"
            )

        parts.append(
            f"Make a deployment gate decision using gate_policy='{self.config.gate_policy}'."
        )
        parts.append(
            "Provide a comprehensive performance analysis with root cause hypotheses "
            "and actionable recommendations."
        )

        return " ".join(parts)
