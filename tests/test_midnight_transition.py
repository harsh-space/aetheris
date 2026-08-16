"""
Automated Tests for Temporal Boundary and UTC Midnight Transitions.
"""

import json
import unittest
from engine.models import TelemetryEvent
from engine.processor import TelemetryProcessor


class TestMidnightTransition(unittest.TestCase):

    def setUp(self):
        self.processor = TelemetryProcessor()
        with open("fixtures/06_midnight_boundary_transition.json", "r") as f:
            self.raw_fixture = json.load(f)

    def test_midnight_transition_continuity(self):
        events = [TelemetryEvent(**item) for item in self.raw_fixture]
        for ev in events:
            self.processor.process_event(ev)

        self.assertEqual(self.processor.total_received, 4)
        state = self.processor.get_sensor_state("WQ-S101")
        self.assertIsNotNone(state)
        # Verify the state successfully advanced across day boundary to 2024-06-16T00:00:15Z
        self.assertEqual(state.last_event_time, "2024-06-16T00:00:15Z")
        self.assertEqual(state.readings["conductivity"], 421.2)


if __name__ == "__main__":
    unittest.main()
