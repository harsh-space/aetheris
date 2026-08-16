"""
Automated Tests for Multi-Source Conflict and Identity Resolution.
"""

import json
import unittest
from engine.models import TelemetryEvent
from engine.processor import TelemetryProcessor
from engine.resolver import ConfidenceWeightedResolver, LatestResolver, SourcePriorityResolver


class TestIdentityResolution(unittest.TestCase):

    def setUp(self):
        with open("fixtures/03_conflicting_sources.json", "r") as f:
            self.raw_fixture = json.load(f)

    def test_source_priority_resolution(self):
        # Source hierarchy: lab (1.0) > calibration (0.95) > field (0.8) > backup (0.5)
        processor = TelemetryProcessor(strategy_name="source_priority")
        
        # Ingest field (pH 7.10)
        e_field = TelemetryEvent(**self.raw_fixture[0])
        processor.process_event(e_field)
        self.assertEqual(processor.get_sensor_state("WQ-S102").readings["pH"], 7.10)

        # Ingest lab simultaneous (pH 7.35) -> Lab must override field!
        e_lab = TelemetryEvent(**self.raw_fixture[1])
        processor.process_event(e_lab)
        self.assertEqual(processor.get_sensor_state("WQ-S102").readings["pH"], 7.35)

        # Ingest backup simultaneous (pH 7.05) -> Backup must NOT override lab!
        e_backup = TelemetryEvent(**self.raw_fixture[2])
        processor.process_event(e_backup)
        self.assertEqual(processor.get_sensor_state("WQ-S102").readings["pH"], 7.35)

    def test_confidence_weighted_fusion(self):
        # ConfidenceWeighted blends concurrent readings
        processor = TelemetryProcessor(strategy_name="confidence_weighted")
        
        e_field = TelemetryEvent(**self.raw_fixture[0]) # pH: 7.10, weight: 0.8
        e_lab = TelemetryEvent(**self.raw_fixture[1])   # pH: 7.35, weight: 0.99
        
        processor.process_event(e_field)
        processor.process_event(e_lab)

        state = processor.get_sensor_state("WQ-S102")
        expected_fused_ph = round((7.10 * 0.80 + 7.35 * 0.99) / (0.80 + 0.99), 4)
        self.assertAlmostEqual(state.readings["pH"], expected_fused_ph, places=3)

    def test_latest_resolver(self):
        processor = TelemetryProcessor(strategy_name="latest")
        for item in self.raw_fixture:
            processor.process_event(TelemetryEvent(**item))

        state = processor.get_sensor_state("WQ-S102")
        # Final item at 14:05:00 has pH 7.38
        self.assertEqual(state.readings["pH"], 7.38)


if __name__ == "__main__":
    unittest.main()
