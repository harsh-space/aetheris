"""
Automated Tests for Multi-Sensor Spatial and Cluster Correlation.
"""

import json
import unittest
from engine.models import TelemetryEvent
from engine.processor import TelemetryProcessor


class TestSpatialCorrelation(unittest.TestCase):

    def setUp(self):
        self.processor = TelemetryProcessor()
        with open("fixtures/05_drift_vs_spike_correlation.json", "r") as f:
            self.raw_fixture = json.load(f)

    def test_isolated_drift_vs_systemic_plume(self):
        events = [TelemetryEvent(**item) for item in self.raw_fixture]
        
        reports = []
        for event in events:
            _, anom, _, _, _, _ = self.processor.process_event(event)
            reports.append((event.sensor_id, anom))

        # WQ-S201 (South basin) has isolated drift
        s201_reports = [r for s_id, r in reports if s_id == "WQ-S201" and r.is_anomaly]
        self.assertTrue(len(s201_reports) > 0)
        self.assertFalse(s201_reports[-1].corroborated_by_neighbors)

        # WQ-S101 and WQ-S102 (North basin) both spike at 10:05 and 10:06
        s102_spike = [r for s_id, r in reports if s_id == "WQ-S102" and r.is_anomaly][-1]
        self.assertTrue(s102_spike.is_anomaly)
        self.assertTrue(s102_spike.corroborated_by_neighbors)
        self.assertIn("WQ-S101", s102_spike.details.get("corroborated_neighbors", []))


if __name__ == "__main__":
    unittest.main()
