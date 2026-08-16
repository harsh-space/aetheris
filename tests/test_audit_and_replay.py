"""
Automated Tests for Hash-Chained Audit Ledger and Deterministic Replay Invariance.
"""

import json
import unittest
from engine.models import TelemetryEvent
from engine.processor import TelemetryProcessor
from engine.replay_engine import ReplayEngine


class TestAuditAndReplay(unittest.TestCase):

    def setUp(self):
        with open("fixtures/02_out_of_order_stream.json", "r") as f:
            self.raw_fixture = json.load(f)
        self.events = [TelemetryEvent(**item) for item in self.raw_fixture]

    def test_audit_ledger_integrity(self):
        processor = TelemetryProcessor()
        for ev in self.events:
            processor.process_event(ev)

        is_valid, msg = processor.verify_ledger()
        self.assertTrue(is_valid, f"Ledger integrity failed: {msg}")
        self.assertEqual(processor.audit_ledger.get_record_count(), len(self.events))

    def test_audit_ledger_tamper_detection(self):
        processor = TelemetryProcessor()
        for ev in self.events:
            processor.process_event(ev)

        # Corrupt record 2 payload in memory
        record = processor.audit_ledger.records[1]
        record.resulting_state["readings"]["pH"] = 999.9  # Malicious tampering!

        is_valid, msg = processor.verify_ledger()
        self.assertFalse(is_valid, "Tampered ledger must be detected!")
        self.assertIn("Hash mismatch", msg)

    def test_order_invariance_deterministic_replay(self):
        replay_engine = ReplayEngine()
        is_invariant, msg, details = replay_engine.verify_order_invariance(
            events=self.events,
            permutations=5
        )
        self.assertTrue(is_invariant, f"Replay was not order-invariant: {msg} | Details: {details}")


if __name__ == "__main__":
    unittest.main()
