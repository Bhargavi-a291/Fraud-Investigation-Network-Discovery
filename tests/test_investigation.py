"""Automated Evaluation Suite for Autonomous Financial Fraud Investigation & Network Discovery.

Measures:
1. Network Discovery Recall: Discovery of planted accounts, devices, merchants, and relationships.
2. Investigation Completeness: Verifies presence of initial tx, network graph, risk indicators, evidence chain, next steps.
3. Agent Efficiency: Tool call count, depth, and execution runtime.
4. Explainability & Grounding: Validates that all findings trace to genuine records in fraud.db without hallucination.
"""

import sys
import os
import unittest
import time

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.db import ensure_database, query_db, query_one
from agent.agent import FraudInvestigationAgent

class TestFraudInvestigation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_database()
        cls.agent = FraudInvestigationAgent(provider="autonomous", max_steps=12)

    def test_01_planted_mule_network_discovery_tx1001(self):
        """Test Network 1: Seed TX1001 should uncover mule ring sharing Device D77 and funneling to A500."""
        t0 = time.time()
        state = self.agent.investigate("TX1001")
        elapsed = time.time() - t0

        # Status check
        self.assertEqual(state.status, "COMPLETED")

        # Planted accounts that must be discovered
        expected_accounts = {"A102", "A103", "A108", "A115"}
        discovered_accounts = set(state.get_accounts())
        found_intersection = expected_accounts.intersection(discovered_accounts)

        # Discovery Recall
        recall = len(found_intersection) / len(expected_accounts)
        self.assertGreaterEqual(recall, 1.0, f"Expected all mule accounts {expected_accounts}, but discovered {discovered_accounts}")

        # Shared Device D77
        self.assertIn("D77", state.get_devices(), "Device D77 must be discovered as shared infrastructure")

        # Merchant M19
        self.assertIn("M19", state.get_merchants(), "Merchant M19 must be discovered as payment gateway")

        # Risk Score must reflect high risk
        score = state.risk_evaluation.get("prototype_risk_score", 0)
        self.assertGreaterEqual(score, 75, f"Expected critical/high risk score >= 75 for mule network, got {score}")

        # Agent Efficiency
        self.assertLessEqual(len(state.action_history), 12, "Agent should not exceed max tool call limit")
        self.assertLess(elapsed, 5.0, "Investigation should execute promptly")

        print(f"\n[EVALUATION] TX1001 Mule Ring:")
        print(f"  - Account Recall: {recall*100:.1f}% ({len(found_intersection)}/{len(expected_accounts)})")
        print(f"  - Device D77 Discovered: {'D77' in state.get_devices()}")
        print(f"  - Merchant M19 Discovered: {'M19' in state.get_merchants()}")
        print(f"  - Risk Score: {score}/100 ({state.risk_evaluation.get('risk_severity')})")
        print(f"  - Tool Calls: {len(state.action_history)}")
        print(f"  - Latency: {elapsed*1000:.1f} ms")

    def test_02_circular_layering_detection_tx2001(self):
        """Test Network 2: Seed TX2001 should discover circular layering loop (A201->A202->A203->A204->A201)."""
        t0 = time.time()
        state = self.agent.investigate("TX2001")
        elapsed = time.time() - t0

        self.assertEqual(state.status, "COMPLETED")
        
        # Check accounts discovered
        discovered_accounts = set(state.get_accounts())
        for acc in ["A201", "A202", "A203", "A204"]:
            self.assertIn(acc, discovered_accounts, f"Account {acc} should be part of the discovered layering ring")

        # Check circular loop or cycle in topology
        topo = state.graph_topology
        has_cycle = bool(topo.get("circular_cycles")) or state.pattern_summary.get("is_circular_flow")
        self.assertTrue(has_cycle, "Topological cycle analysis must flag circular money movement")

        # Score check
        score = state.risk_evaluation.get("prototype_risk_score", 0)
        self.assertGreaterEqual(score, 50, f"Expected risk score >= 50 for circular layering, got {score}")

        print(f"\n[EVALUATION] TX2001 Layering Ring:")
        print(f"  - Accounts Discovered: {discovered_accounts}")
        print(f"  - Cycle Detected: {has_cycle}")
        print(f"  - Risk Score: {score}/100")
        print(f"  - Latency: {elapsed*1000:.1f} ms")

    def test_03_benign_baseline_tx9001(self):
        """Test Benign Baseline: Legitimate grocery transaction TX9001 should produce low risk and terminate cleanly."""
        t0 = time.time()
        state = self.agent.investigate("TX9001")
        elapsed = time.time() - t0

        self.assertEqual(state.status, "COMPLETED")

        # Score must be low
        score = state.risk_evaluation.get("prototype_risk_score", 0)
        self.assertLessEqual(score, 20, f"Benign transaction should have risk <= 20, got {score}")

        # Account check
        self.assertIn("A901", state.get_accounts())
        self.assertIn("D901", state.get_devices())

        # No suspicious indicators
        indicators = state.risk_evaluation.get("indicators", [])
        self.assertEqual(len(indicators), 0, f"Expected 0 suspicious indicators for clean baseline, got {len(indicators)}")

        print(f"\n[EVALUATION] TX9001 Benign Baseline:")
        print(f"  - Risk Score: {score}/100 (Clean)")
        print(f"  - Indicators: {len(indicators)}")
        print(f"  - Tool Calls: {len(state.action_history)}")
        print(f"  - Latency: {elapsed*1000:.1f} ms")

    def test_04_invalid_transaction_error_handling(self):
        """Test system resiliency against non-existent transaction IDs."""
        state = self.agent.investigate("TX_NONEXISTENT_9999")
        self.assertEqual(state.status, "FAILED")
        self.assertIsNotNone(state.error_message)
        print(f"\n[EVALUATION] Invalid TX Error Handling: Handled gracefully with message: {state.error_message}")

    def test_05_investigation_completeness_and_grounding(self):
        """Test report completeness and empirical grounding."""
        state = self.agent.investigate("TX1001")
        report = state.final_report

        # Verify all mandatory report sections
        required_headers = [
            "Investigation Summary",
            "Initial Transaction",
            "Discovered Network",
            "Suspicious Indicators",
            "Evidence Chain",
            "Recommended Next Steps"
        ]
        for header in required_headers:
            self.assertIn(header, report, f"Report missing mandatory section: {header}")

        # Grounding check: verify that discovered nodes actually exist in the database
        for node in state.get_nodes_list():
            nid = node["id"]
            ntype = node["type"]
            if ntype == "Account":
                db_acc = query_one("SELECT account_id FROM accounts WHERE account_id = ?", (nid,))
                self.assertIsNotNone(db_acc, f"Account {nid} cited in report but missing in database!")
            elif ntype == "Device":
                db_dev = query_one("SELECT device_id FROM devices WHERE device_id = ?", (nid,))
                self.assertIsNotNone(db_dev, f"Device {nid} cited in report but missing in database!")
            elif ntype == "Merchant":
                db_m = query_one("SELECT merchant_id FROM merchants WHERE merchant_id = ?", (nid,))
                self.assertIsNotNone(db_m, f"Merchant {nid} cited in report but missing in database!")

        print(f"\n[EVALUATION] Grounding & Explainability: 100% of discovered nodes ({len(state.discovered_nodes)}) verified in SQLite.")

if __name__ == "__main__":
    unittest.main()
