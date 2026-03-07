"""Tests for heimr.agent.tools — verifies each tool wraps underlying capabilities correctly."""

import os
import tempfile
import unittest

from heimr.agent.tools import (
    TOOL_REGISTRY,
    execute_tool,
    get_tool_by_name,
    get_tools_description,
)


class TestToolRegistry(unittest.TestCase):
    """Test tool registry structure and metadata."""

    def test_all_tools_have_required_fields(self):
        for tool in TOOL_REGISTRY:
            self.assertIn("name", tool, f"Tool missing 'name': {tool}")
            self.assertIn("description", tool, f"Tool missing 'description': {tool}")
            self.assertIn("parameters", tool, f"Tool missing 'parameters': {tool}")
            self.assertIn("function", tool, f"Tool missing 'function': {tool}")
            self.assertTrue(callable(tool["function"]), f"Tool function not callable: {tool['name']}")

    def test_tool_names_are_unique(self):
        names = [t["name"] for t in TOOL_REGISTRY]
        self.assertEqual(len(names), len(set(names)), "Duplicate tool names found")

    def test_get_tool_by_name(self):
        tool = get_tool_by_name("parse_load_test")
        self.assertIsNotNone(tool)
        self.assertEqual(tool["name"], "parse_load_test")

    def test_get_tool_by_name_missing(self):
        tool = get_tool_by_name("nonexistent_tool")
        self.assertIsNone(tool)

    def test_get_tools_description(self):
        desc = get_tools_description()
        self.assertIsInstance(desc, str)
        self.assertIn("parse_load_test", desc)
        self.assertIn("evaluate_gate", desc)
        self.assertIn("compute_kpis", desc)

    def test_execute_unknown_tool(self):
        result = execute_tool("nonexistent_tool", {})
        self.assertEqual(result["status"], "error")
        self.assertIn("Unknown tool", result["error"])


class TestToolExecution(unittest.TestCase):
    """Test tool execution against actual (test) data."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.jtl_path = os.path.join(self.test_dir, "test.jtl")
        with open(self.jtl_path, "w") as f:
            f.write("timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect\n")
            for i in range(10):
                f.write(
                    f"{1600000000000 + i * 1000},100,home,200,OK,Thread-1,text,true,,1024,0,1,1,http://localhost/home,100,0,0\n"
                )
            f.write(
                f"{1600000020000},500,api,500,Error,Thread-1,text,false,,1024,0,1,1,http://localhost/api,500,0,0\n"
            )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)

    def test_parse_load_test(self):
        result = execute_tool("parse_load_test", {"file_path": self.jtl_path})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["format"], "jtl")
        self.assertEqual(result["data"]["total_rows"], 11)

    def test_compute_kpis(self):
        result = execute_tool("compute_kpis", {"file_path": self.jtl_path})
        self.assertEqual(result["status"], "ok")
        self.assertIn("throughput", result["data"])
        self.assertIn("latency", result["data"])

    def test_detect_anomalies(self):
        result = execute_tool("detect_anomalies", {"file_path": self.jtl_path})
        self.assertEqual(result["status"], "ok")
        self.assertIn("summary", result["data"])

    def test_evaluate_gate(self):
        result = execute_tool("evaluate_gate", {
            "file_path": self.jtl_path,
            "gate_policy": "strict",
        })
        self.assertEqual(result["status"], "ok")
        self.assertIn("verdict", result["data"])
        self.assertIn(result["data"]["verdict"], ["APPROVE", "REJECT", "WARN"])

    def test_run_full_analysis(self):
        result = execute_tool("run_full_analysis", {
            "file_path": self.jtl_path,
            "no_llm": True,
        })
        self.assertEqual(result["status"], "ok")
        self.assertIn("status", result["data"])
        self.assertIn("kpi", result["data"])

    def test_parse_load_test_missing_file(self):
        result = execute_tool("parse_load_test", {"file_path": "/nonexistent/file.jtl"})
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
