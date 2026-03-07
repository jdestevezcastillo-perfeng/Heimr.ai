"""Tests for heimr.agent.gate — verifies deployment gate decisions."""

import os
import tempfile
import shutil
import unittest

from heimr.analyzer import Analyzer, AnalysisResult
from heimr.agent.gate import GateDecision, evaluate_gate


class TestGateDecision(unittest.TestCase):
    """Test GateDecision properties."""

    def test_approve_exit_code(self):
        d = GateDecision(verdict="APPROVE")
        self.assertTrue(d.passed)
        self.assertEqual(d.exit_code, 0)

    def test_reject_exit_code(self):
        d = GateDecision(verdict="REJECT", reasons=["High error rate"])
        self.assertFalse(d.passed)
        self.assertEqual(d.exit_code, 1)

    def test_warn_exit_code(self):
        d = GateDecision(verdict="WARN", reasons=["Minor anomalies"])
        self.assertFalse(d.passed)
        self.assertEqual(d.exit_code, 0)  # Advisory — don't break pipeline

    def test_to_dict(self):
        d = GateDecision(
            verdict="REJECT",
            reasons=["Error rate too high"],
            confidence=0.9,
            recommendations=["Fix the bug"],
            kpi_snapshot={"error_rate": 5.0},
        )
        data = d.to_dict()
        self.assertEqual(data["verdict"], "REJECT")
        self.assertEqual(data["confidence"], 0.9)
        self.assertIn("Error rate too high", data["reasons"])


class TestEvaluateGate(unittest.TestCase):
    """Test evaluate_gate with real Analyzer output."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

        # Clean test (should pass)
        self.clean_jtl = os.path.join(self.test_dir, "clean.jtl")
        with open(self.clean_jtl, "w") as f:
            f.write("timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect\n")
            for i in range(20):
                f.write(
                    f"{1600000000000 + i * 1000},100,home,200,OK,Thread-1,text,true,,1024,0,1,1,http://localhost/home,100,0,0\n"
                )

        # Bad test (should fail: errors + high latency)
        self.bad_jtl = os.path.join(self.test_dir, "bad.jtl")
        with open(self.bad_jtl, "w") as f:
            f.write("timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect\n")
            for i in range(10):
                f.write(
                    f"{1600000000000 + i * 1000},100,home,200,OK,Thread-1,text,true,,1024,0,1,1,http://localhost/home,100,0,0\n"
                )
            # Errors
            f.write(f"{1600000020000},500,api,500,Error,Thread-1,text,false,,1024,0,1,1,http://localhost/api,500,0,0\n")
            # Anomaly
            f.write(f"{1600000030000},5000,api,200,OK,Thread-1,text,true,,1024,0,1,1,http://localhost/api,5000,0,0\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_gate_approves_clean_run(self):
        analyzer = Analyzer(self.clean_jtl, no_llm=True)
        result = analyzer.analyze()
        decision = evaluate_gate(result)
        self.assertEqual(decision.verdict, "APPROVE")
        self.assertEqual(decision.exit_code, 0)

    def test_gate_rejects_bad_run_strict(self):
        analyzer = Analyzer(self.bad_jtl, no_llm=True)
        result = analyzer.analyze()
        decision = evaluate_gate(result, gate_policy="strict")
        self.assertEqual(decision.verdict, "REJECT")
        self.assertEqual(decision.exit_code, 1)
        self.assertTrue(len(decision.reasons) > 0)

    def test_gate_warns_bad_run_advisory(self):
        analyzer = Analyzer(self.bad_jtl, no_llm=True)
        result = analyzer.analyze()
        decision = evaluate_gate(result, gate_policy="advisory")
        self.assertEqual(decision.verdict, "WARN")
        self.assertEqual(decision.exit_code, 0)  # Advisory doesn't break pipeline

    def test_gate_with_fail_conditions(self):
        analyzer = Analyzer(self.bad_jtl, no_llm=True)
        result = analyzer.analyze()
        decision = evaluate_gate(
            result,
            fail_conditions=["p99_latency > 1000"],
            gate_policy="strict",
        )
        self.assertEqual(decision.verdict, "REJECT")
        # Should have the fail condition reason
        self.assertTrue(any("Failure condition met" in r for r in decision.reasons))

    def test_gate_kpi_snapshot(self):
        analyzer = Analyzer(self.clean_jtl, no_llm=True)
        result = analyzer.analyze()
        decision = evaluate_gate(result)
        self.assertIn("total_requests", decision.kpi_snapshot)
        self.assertIn("p99_latency", decision.kpi_snapshot)
        self.assertEqual(decision.kpi_snapshot["total_requests"], 20)


if __name__ == "__main__":
    unittest.main()
