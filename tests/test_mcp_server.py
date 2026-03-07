"""Tests for heimr.agent.mcp_server — verifies MCP server structure without requiring mcp SDK."""

import importlib
import inspect
import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helper: build a mock FastMCP that records registrations
# ---------------------------------------------------------------------------

class MockFastMCP:
    """Fake FastMCP that records tool/resource/prompt registrations."""

    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "")
        self.instructions = kwargs.get("instructions", "")
        self._tools = {}
        self._resources = {}
        self._prompts = {}

    def tool(self):
        """Decorator that records a tool function."""
        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn
        return decorator

    def resource(self, uri: str):
        """Decorator that records a resource function."""
        def decorator(fn):
            self._resources[uri] = fn
            return fn
        return decorator

    def prompt(self):
        """Decorator that records a prompt function."""
        def decorator(fn):
            self._prompts[fn.__name__] = fn
            return fn
        return decorator

    def run(self, **kwargs):
        pass


def _import_mcp_server_with_mock():
    """Import mcp_server.py using a mock FastMCP so we can inspect registrations."""
    mock_fastmcp_mod = types.ModuleType("mcp.server.fastmcp")
    mock_mcp_mod = types.ModuleType("mcp")
    mock_mcp_server_mod = types.ModuleType("mcp.server")

    # Use a list so the lambda can capture the instance created during import
    instances = []

    def factory_fn(**kw):
        inst = MockFastMCP(**kw)
        instances.append(inst)
        return inst

    mock_fastmcp_mod.FastMCP = factory_fn

    saved = {}
    for mod_name in ["mcp", "mcp.server", "mcp.server.fastmcp"]:
        saved[mod_name] = sys.modules.get(mod_name)

    sys.modules["mcp"] = mock_mcp_mod
    sys.modules["mcp.server"] = mock_mcp_server_mod
    sys.modules["mcp.server.fastmcp"] = mock_fastmcp_mod

    # Remove cached module so it re-imports with our mock
    sys.modules.pop("heimr.agent.mcp_server", None)

    try:
        from heimr.agent import mcp_server
        importlib.reload(mcp_server)
        return mcp_server, instances[-1]
    finally:
        # Restore original module state
        for mod_name, original in saved.items():
            if original is None:
                sys.modules.pop(mod_name, None)
            else:
                sys.modules[mod_name] = original


class TestMCPServerToolRegistry(unittest.TestCase):
    """Test that the tool registry matches MCP server expectations."""

    def test_mcp_server_tools_match_registry(self):
        """Verify that the MCP server exposes the same tools as the tool registry."""
        from heimr.agent.tools import TOOL_REGISTRY

        registry_names = {t["name"] for t in TOOL_REGISTRY}
        expected = {
            "parse_load_test",
            "compute_kpis",
            "detect_anomalies",
            "query_prometheus",
            "query_loki",
            "query_tempo",
            "evaluate_gate",
            "run_full_analysis",
        }
        self.assertEqual(registry_names, expected)

    def test_mcp_tool_functions_exist_in_tools_module(self):
        """Verify tools.py has the private implementation for each tool."""
        from heimr.agent import tools

        for name in [
            "_parse_load_test",
            "_compute_kpis",
            "_detect_anomalies",
            "_query_prometheus",
            "_query_loki",
            "_query_tempo",
            "_evaluate_gate",
            "_run_full_analysis",
        ]:
            self.assertTrue(
                hasattr(tools, name),
                f"Missing tool function: {name}",
            )
            self.assertTrue(callable(getattr(tools, name)))

    def test_execute_tool_delegates_correctly(self):
        """Test that execute_tool routes to the right function."""
        from heimr.agent.tools import execute_tool

        # Unknown tool should error
        result = execute_tool("nonexistent", {})
        self.assertEqual(result["status"], "error")

        # Known tool with bad args should error gracefully
        result = execute_tool("parse_load_test", {"file_path": "/no/such/file"})
        self.assertEqual(result["status"], "error")

    def test_tool_descriptions_are_meaningful(self):
        """Verify tool descriptions are non-empty and informative."""
        from heimr.agent.tools import TOOL_REGISTRY

        for tool in TOOL_REGISTRY:
            self.assertTrue(
                len(tool["description"]) > 20,
                f"Tool '{tool['name']}' has too short a description",
            )


class TestMCPServerModule(unittest.TestCase):
    """Test the MCP server module itself using mocked FastMCP."""

    @classmethod
    def setUpClass(cls):
        cls.mcp_server, cls.mock_mcp = _import_mcp_server_with_mock()

    def test_all_8_tools_registered(self):
        """MCP server registers exactly 8 tools matching the tool registry."""
        expected_tools = {
            "parse_load_test",
            "compute_kpis",
            "detect_anomalies",
            "query_prometheus",
            "query_loki",
            "query_tempo",
            "evaluate_gate",
            "run_full_analysis",
        }
        self.assertEqual(set(self.mock_mcp._tools.keys()), expected_tools)

    def test_resources_registered(self):
        """MCP server registers the expected resources."""
        self.assertIn("heimr://tools", self.mock_mcp._resources)
        self.assertIn("heimr://supported-formats", self.mock_mcp._resources)
        self.assertEqual(len(self.mock_mcp._resources), 2)

    def test_prompts_registered(self):
        """MCP server registers the expected prompt templates."""
        self.assertIn("analyze_load_test", self.mock_mcp._prompts)
        self.assertIn("deployment_gate", self.mock_mcp._prompts)
        self.assertEqual(len(self.mock_mcp._prompts), 2)

    def test_tool_functions_delegate_to_execute_tool(self):
        """Each MCP tool function calls execute_tool with the correct tool name."""
        with patch("heimr.agent.tools.execute_tool", return_value={"status": "ok"}) as mock_exec:
            self.mock_mcp._tools["parse_load_test"](file_path="test.json")
            mock_exec.assert_called_with("parse_load_test", {"file_path": "test.json"})

        with patch("heimr.agent.tools.execute_tool", return_value={"status": "ok"}) as mock_exec:
            self.mock_mcp._tools["compute_kpis"](file_path="test.json")
            mock_exec.assert_called_with("compute_kpis", {"file_path": "test.json"})

        with patch("heimr.agent.tools.execute_tool", return_value={"status": "ok"}) as mock_exec:
            self.mock_mcp._tools["detect_anomalies"](
                file_path="test.json", detector_mode="mad"
            )
            mock_exec.assert_called_with("detect_anomalies", {
                "file_path": "test.json",
                "detector_mode": "mad",
            })

    def test_tool_functions_have_docstrings(self):
        """Every registered MCP tool has a docstring for tool description."""
        for name, fn in self.mock_mcp._tools.items():
            self.assertIsNotNone(
                fn.__doc__,
                f"MCP tool '{name}' is missing a docstring",
            )
            self.assertGreater(
                len(fn.__doc__.strip()), 20,
                f"MCP tool '{name}' docstring is too short",
            )

    def test_resource_heimr_tools_returns_string(self):
        """The heimr://tools resource returns a non-empty string."""
        result = self.mock_mcp._resources["heimr://tools"]()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 50)

    def test_resource_supported_formats_content(self):
        """The heimr://supported-formats resource lists known formats."""
        result = self.mock_mcp._resources["heimr://supported-formats"]()
        self.assertIsInstance(result, str)
        for fmt in ["k6", "JMeter", "Gatling", "Locust", "HAR"]:
            self.assertIn(fmt, result)
        for source in ["Prometheus", "Loki", "Tempo"]:
            self.assertIn(source, result)

    def test_prompt_analyze_load_test(self):
        """The analyze_load_test prompt includes the file path."""
        result = self.mock_mcp._prompts["analyze_load_test"](file_path="results.json")
        self.assertIn("results.json", result)
        self.assertIn("parse_load_test", result)
        self.assertIn("evaluate_gate", result)

    def test_prompt_deployment_gate(self):
        """The deployment_gate prompt includes file path and policy."""
        result = self.mock_mcp._prompts["deployment_gate"](
            file_path="results.json", policy="strict"
        )
        self.assertIn("results.json", result)
        self.assertIn("strict", result)

    def test_prompt_deployment_gate_with_conditions(self):
        """The deployment_gate prompt includes fail conditions when provided."""
        result = self.mock_mcp._prompts["deployment_gate"](
            file_path="results.json",
            fail_conditions="p99 > 500ms",
            policy="lenient",
        )
        self.assertIn("p99 > 500ms", result)

    def test_main_function_exists(self):
        """The mcp_server module has a main() entrypoint."""
        self.assertTrue(hasattr(self.mcp_server, "main"))
        self.assertTrue(callable(self.mcp_server.main))

    def test_mcp_server_name_and_instructions(self):
        """The MCP server has a descriptive name and instructions."""
        self.assertIn("Heimr", self.mock_mcp.name)
        self.assertIn("performance", self.mock_mcp.instructions.lower())


class TestMCPCLIHandler(unittest.TestCase):
    """Test the 'heimr mcp' CLI integration path."""

    def test_cli_mcp_import_error_handled(self):
        """CLI gracefully handles missing mcp SDK."""
        # The CLI handler catches ImportError when mcp SDK is not installed.
        # We verify the import path exists in the CLI module.
        import heimr.cli
        source = inspect.getsource(heimr.cli)
        self.assertIn("from heimr.agent.mcp_server import mcp as mcp_app", source)
        self.assertIn("pip install mcp", source)


if __name__ == "__main__":
    unittest.main()
