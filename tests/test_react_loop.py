"""Tests for heimr.agent.react_loop — verifies ReAct loop, response parsing, and AgentResult."""

import json
import unittest
from unittest.mock import MagicMock, patch

from heimr.agent.config import AgentConfig
from heimr.agent.react_loop import AgentResult, AgentRunner, AgentStep, _parse_agent_response


class TestResponseParser(unittest.TestCase):
    """Test the THOUGHT/ACTION/ACTION_INPUT parser."""

    def test_parse_standard_response(self):
        text = """THOUGHT: I need to parse the load test file first.
ACTION: parse_load_test
ACTION_INPUT: {"file_path": "/data/k6.json"}"""

        result = _parse_agent_response(text)
        self.assertEqual(result["thought"], "I need to parse the load test file first.")
        self.assertEqual(result["action"], "parse_load_test")
        self.assertEqual(result["action_input"], {"file_path": "/data/k6.json"})

    def test_parse_finish_action(self):
        text = """THOUGHT: I have enough data to make a decision.
ACTION: FINISH
ACTION_INPUT: {"verdict": "APPROVE - All KPIs within thresholds."}"""

        result = _parse_agent_response(text)
        self.assertEqual(result["action"], "FINISH")
        self.assertEqual(result["action_input"]["verdict"], "APPROVE - All KPIs within thresholds.")

    def test_parse_multiline_thought(self):
        text = """THOUGHT: The load test shows high p99 latency.
The anomaly detector found 5 spikes.
I should check Prometheus for CPU data.
ACTION: query_prometheus
ACTION_INPUT: {"source": "http://prometheus:9090"}"""

        result = _parse_agent_response(text)
        self.assertIn("high p99 latency", result["thought"])
        self.assertIn("CPU data", result["thought"])
        self.assertEqual(result["action"], "query_prometheus")

    def test_parse_malformed_json(self):
        text = """THOUGHT: Testing bad JSON.
ACTION: parse_load_test
ACTION_INPUT: not valid json at all"""

        result = _parse_agent_response(text)
        self.assertEqual(result["action"], "parse_load_test")
        # Should put raw value in action_input
        self.assertIn("_raw", result["action_input"])

    def test_parse_json_embedded_in_text(self):
        text = """THOUGHT: Need to parse this.
ACTION: compute_kpis
ACTION_INPUT: Here are the args: {"file_path": "/data/test.jtl"} end."""

        result = _parse_agent_response(text)
        self.assertEqual(result["action_input"], {"file_path": "/data/test.jtl"})


class TestAgentResult(unittest.TestCase):
    """Test AgentResult serialization and properties."""

    def test_to_dict(self):
        result = AgentResult(
            verdict="APPROVE",
            exit_code=0,
            total_iterations=3,
            elapsed_seconds=5.2,
        )
        d = result.to_dict()
        self.assertEqual(d["verdict"], "APPROVE")
        self.assertEqual(d["exit_code"], 0)
        self.assertIsInstance(d["steps"], list)

    def test_audit_trail(self):
        step = AgentStep(
            iteration=1,
            thought="Need to check KPIs",
            action="compute_kpis",
            action_input={"file_path": "test.jtl"},
            observation='{"status": "ok"}',
        )
        result = AgentResult(
            verdict="All good",
            steps=[step],
        )
        trail = result.audit_trail
        self.assertIn("Step 1", trail)
        self.assertIn("compute_kpis", trail)
        self.assertIn("All good", trail)


class TestAgentRunner(unittest.TestCase):
    """Test AgentRunner with mocked LLM."""

    @patch("heimr.agent.react_loop.AgentRunner._call_llm")
    def test_agent_finishes_in_one_step(self, mock_llm):
        """Test that agent terminates when LLM returns FINISH."""
        mock_llm.return_value = """THOUGHT: I'll run a full analysis and decide.
ACTION: FINISH
ACTION_INPUT: {"verdict": "APPROVE - Test passed all thresholds."}"""

        config = AgentConfig(
            results_file="/tmp/dummy.jtl",
            max_iterations=5,
        )

        runner = AgentRunner.__new__(AgentRunner)
        runner.config = config
        runner._llm = MagicMock()
        runner._llm.provider = "local"
        runner._llm.base_url = "http://localhost:11434/v1"
        runner._llm.model = "test"
        runner._llm.timeout_sec = None
        runner._call_llm = mock_llm

        result = runner.run("Test task")

        self.assertEqual(result.exit_code, 0)
        self.assertIn("APPROVE", result.verdict)
        self.assertEqual(result.total_iterations, 1)
        self.assertIsNone(result.error)

    @patch("heimr.agent.react_loop.AgentRunner._call_llm")
    @patch("heimr.agent.react_loop.execute_tool")
    def test_agent_tool_then_finish(self, mock_execute, mock_llm):
        """Test that agent can call a tool, observe, then finish."""
        mock_llm.side_effect = [
            # First call: use a tool
            'THOUGHT: I need to parse the file.\nACTION: parse_load_test\nACTION_INPUT: {"file_path": "/tmp/test.jtl"}',
            # Second call: finish
            'THOUGHT: Got the data, looks good.\nACTION: FINISH\nACTION_INPUT: {"verdict": "APPROVE - 100 requests, 0 errors."}',
        ]

        mock_execute.return_value = {
            "status": "ok",
            "data": {"total_rows": 100, "format": "jtl"},
        }

        config = AgentConfig(
            results_file="/tmp/test.jtl",
            max_iterations=5,
        )

        runner = AgentRunner.__new__(AgentRunner)
        runner.config = config
        runner._llm = MagicMock()
        runner._llm.provider = "local"
        runner._call_llm = mock_llm

        result = runner.run("Analyze and decide")

        self.assertEqual(result.total_iterations, 2)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("APPROVE", result.verdict)
        mock_execute.assert_called_once_with("parse_load_test", {"file_path": "/tmp/test.jtl"})

    @patch("heimr.agent.react_loop.AgentRunner._call_llm")
    def test_agent_max_iterations(self, mock_llm):
        """Test that agent stops at max_iterations."""
        # LLM never returns FINISH
        mock_llm.return_value = 'THOUGHT: Still thinking.\nACTION: compute_kpis\nACTION_INPUT: {"file_path": "/tmp/test.jtl"}'

        config = AgentConfig(
            results_file="/tmp/test.jtl",
            max_iterations=3,
        )

        runner = AgentRunner.__new__(AgentRunner)
        runner.config = config
        runner._llm = MagicMock()
        runner._llm.provider = "local"
        runner._call_llm = mock_llm

        with patch("heimr.agent.react_loop.execute_tool") as mock_exec:
            mock_exec.return_value = {"status": "ok", "data": {}}
            result = runner.run("Never-ending task")

        self.assertEqual(result.exit_code, 1)
        self.assertIn("maximum iterations", result.verdict)
        self.assertEqual(result.total_iterations, 3)

    @patch("heimr.agent.react_loop.AgentRunner._call_llm")
    def test_agent_llm_failure(self, mock_llm):
        """Test that agent handles LLM errors gracefully."""
        mock_llm.side_effect = ConnectionError("LLM is down")

        config = AgentConfig(
            results_file="/tmp/test.jtl",
            max_iterations=5,
        )

        runner = AgentRunner.__new__(AgentRunner)
        runner.config = config
        runner._llm = MagicMock()
        runner._llm.provider = "local"
        runner._call_llm = mock_llm

        result = runner.run("Test task")

        self.assertEqual(result.exit_code, 1)
        self.assertIsNotNone(result.error)
        self.assertIn("LLM call failed", result.error)


if __name__ == "__main__":
    unittest.main()
