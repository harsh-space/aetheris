"""
Automated Tests for Out-of-Order Event Handling and Bi-Temporal State Reconstruction.
"""

import json
import unittest
from engine.models import TelemetryEvent
from engine.processor import TelemetryProcessor


class TestOutOfOrderReconstruction(unittest.TestCase):

    def setUp(self):
        self.processor = TelemetryProcessor()
        with open("fixtures/02_out_of_order_stream.json", "r") as f:
            self.raw_fixture = json.load(f)

    def test_out_of_order_stream_reordering(self):
        # Fixture timestamps: 12:00:00 -> 12:10:00 -> 12:05:00 (delayed) -> 11:50:00 (very delayed) -> 12:15:00
        events = [TelemetryEvent(**item) for item in self.raw_fixture]
        
        for event in events:
            self.processor.process_event(event)

        self.assertEqual(self.processor.total_out_of_order, 2)
        
        # Verify chronological timeline in state store
        timeline_events = self.processor.state_store.get_timeline_events("WQ-S101")
        self.assertEqual(len(timeline_events), 5)
        
        timestamps = [e.timestamp for e in timeline_events]
        expected_order = [
            "2024-06-15T11:50:00Z",
            "2024-06-15T12:00:00Z",
            "2024-06-15T12:05:00Z",
            "2024-06-15T12:10:00Z",
            "2024-06-15T12:15:00Z",
        ]
        self.assertEqual(timestamps, expected_order)

        # Final state must reflect the latest chronologically valid reading (12:15:00)
        curr_state = self.processor.get_sensor_state("WQ-S101")
        self.assertIsNotNone(curr_state)
        self.assertEqual(curr_state.last_event_time, "2024-06-15T12:15:00Z")
        self.assertEqual(curr_state.readings["pH"], 7.40)
        self.assertEqual(curr_state.readings["turbidity"], 2.2)

    def test_historical_point_in_time_query(self):
        events = [TelemetryEvent(**item) for item in self.raw_fixture]
        for event in events:
            self.processor.process_event(event)

        # Point in time query at 12:02:00 should see 12:00:00 state, not future 12:10:00 or 12:15:00
        state_at_1202 = self.processor.get_historical_state("WQ-S101", "2024-06-15T12:02:00Z")
        self.assertIsNotNone(state_at_1202)
        self.assertEqual(state_at_1202.last_event_time, "2024-06-15T12:00:00Z")
        self.assertEqual(state_at_1202.readings["pH"], 7.30)

        # Point in time query at 12:06:00 should see 12:05:00 state
        state_at_1206 = self.processor.get_historical_state("WQ-S101", "2024-06-15T12:06:00Z")
        self.assertIsNotNone(state_at_1206)
        self.assertEqual(state_at_1206.last_event_time, "2024-06-15T12:05:00Z")
        self.assertEqual(state_at_1206.readings["pH"], 7.32)


if __name__ == "__main__":
    unittest.main()
