"""
Automated Tests for Event Deduplication and Idempotent Ingestion.
"""

import json
import unittest
from engine.deduplicator import Deduplicator
from engine.models import TelemetryEvent
from engine.processor import TelemetryProcessor


class TestDeduplication(unittest.TestCase):

    def setUp(self):
        self.processor = TelemetryProcessor()
        with open("fixtures/01_duplicate_packet_storm.json", "r") as f:
            self.raw_fixture = json.load(f)

    def test_fingerprint_determinism(self):
        e1 = TelemetryEvent(
            sensor_id="WQ-S123",
            timestamp="2024-06-15T10:30:00Z",
            readings={"pH": 7.2, "turbidity": 2.1},
            source="field"
        )
        e2 = TelemetryEvent(
            sensor_id="WQ-S123",
            timestamp="2024-06-15T10:30:00Z",
            readings={"turbidity": 2.1, "pH": 7.2},  # Reordered dictionary keys
            source="field"
        )
        fp1 = Deduplicator.compute_fingerprint(e1)
        fp2 = Deduplicator.compute_fingerprint(e2)
        self.assertEqual(fp1, fp2, "Fingerprint must be invariant to metric dictionary key ordering")

    def test_idempotent_packet_storm(self):
        events = [TelemetryEvent(**item) for item in self.raw_fixture]
        self.assertEqual(len(events), 5)

        for event in events:
            self.processor.process_event(event)

        self.assertEqual(self.processor.total_received, 5)
        self.assertEqual(self.processor.total_duplicates, 3)
        self.assertEqual(self.processor.deduplicator.total_seen, 2)

        # Ensure state only incremented version for unique events
        state = self.processor.get_sensor_state("WQ-S123")
        self.assertIsNotNone(state)
        self.assertEqual(state.total_events_processed, 2)
        self.assertEqual(state.version, 2)
        self.assertEqual(state.readings["pH"], 7.25)


if __name__ == "__main__":
    unittest.main()
