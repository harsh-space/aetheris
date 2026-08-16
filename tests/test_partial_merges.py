"""
Automated Tests for Partial Metric Reading Merging.
"""

import json
import unittest
from engine.models import TelemetryEvent
from engine.processor import TelemetryProcessor


class TestPartialMerges(unittest.TestCase):

    def setUp(self):
        self.processor = TelemetryProcessor()
        with open("fixtures/04_partial_reading_merges.json", "r") as f:
            self.raw_fixture = json.load(f)

    def test_progressive_partial_merge(self):
        # Event 1: pH + temperature
        e1 = TelemetryEvent(**self.raw_fixture[0])
        self.processor.process_event(e1)
        s1 = self.processor.get_sensor_state("WQ-S103")
        self.assertEqual(s1.readings, {"pH": 7.40, "temperature": 23.0})

        # Event 2: only turbidity
        e2 = TelemetryEvent(**self.raw_fixture[1])
        self.processor.process_event(e2)
        s2 = self.processor.get_sensor_state("WQ-S103")
        self.assertEqual(s2.readings, {"pH": 7.40, "temperature": 23.0, "turbidity": 2.8})

        # Event 3: only conductivity
        e3 = TelemetryEvent(**self.raw_fixture[2])
        self.processor.process_event(e3)
        s3 = self.processor.get_sensor_state("WQ-S103")
        self.assertEqual(s3.readings, {
            "pH": 7.40,
            "temperature": 23.0,
            "turbidity": 2.8,
            "conductivity": 435.0
        })

        # Event 4: updated pH + temperature (turbidity & conductivity must persist)
        e4 = TelemetryEvent(**self.raw_fixture[3])
        self.processor.process_event(e4)
        s4 = self.processor.get_sensor_state("WQ-S103")
        self.assertEqual(s4.readings, {
            "pH": 7.42,
            "temperature": 23.2,
            "turbidity": 2.8,
            "conductivity": 435.0
        })


if __name__ == "__main__":
    unittest.main()
