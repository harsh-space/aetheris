"""
Automated Tests for Machine Learning Anomaly and Drift Detection.
"""

import unittest
from engine.anomaly_detector import StatisticalMLAnomalyDetector
from engine.models import AnomalyType, TelemetryEvent


class TestAnomalyML(unittest.TestCase):

    def setUp(self):
        self.detector = StatisticalMLAnomalyDetector()

    def test_normal_telemetry(self):
        event = TelemetryEvent(
            sensor_id="WQ-TEST01",
            timestamp="2024-06-15T10:00:00Z",
            readings={"pH": 7.3, "turbidity": 2.5, "conductivity": 420.0, "temperature": 21.0}
        )
        report = self.detector.evaluate_event(event, event.readings)
        self.assertFalse(report.is_anomaly)
        self.assertEqual(report.anomaly_type, AnomalyType.NONE)

    def test_multivariate_mahalanobis_outlier(self):
        # Abnormal multivariate combination: extreme turbidity + high conductivity
        event = TelemetryEvent(
            sensor_id="WQ-TEST02",
            timestamp="2024-06-15T10:00:00Z",
            readings={"pH": 7.2, "turbidity": 35.0, "conductivity": 1500.0, "temperature": 21.0}
        )
        report = self.detector.evaluate_event(event, event.readings)
        self.assertTrue(report.is_anomaly)
        self.assertIn(report.anomaly_type, [AnomalyType.MULTIVARIATE_OUTLIER, AnomalyType.TEMPORAL_RATE_OF_CHANGE])
        self.assertIsNotNone(report.mahalanobis_distance)
        self.assertGreater(report.mahalanobis_distance, 3.5)

    def test_thermal_ph_coupling_shock(self):
        # Initial event
        e1 = TelemetryEvent(
            sensor_id="WQ-TEST03",
            timestamp="2024-06-15T10:00:00Z",
            readings={"pH": 7.5, "turbidity": 2.0, "conductivity": 400.0, "temperature": 20.0}
        )
        self.detector.evaluate_event(e1, e1.readings)

        # Rapid thermal spike (+5°C) paired with pH drop (-0.8) within 2 minutes
        e2 = TelemetryEvent(
            sensor_id="WQ-TEST03",
            timestamp="2024-06-15T10:02:00Z",
            readings={"pH": 6.7, "turbidity": 2.1, "conductivity": 410.0, "temperature": 25.5}
        )
        report2 = self.detector.evaluate_event(e2, e2.readings)
        self.assertTrue(report2.is_anomaly)
        self.assertEqual(report2.anomaly_type, AnomalyType.THERMAL_PH_COUPLING)

    def test_cusum_drift_detection(self):
        # Progressive upward conductivity drift across multiple steps
        times = [
            "2024-06-15T08:00:00Z",
            "2024-06-15T08:30:00Z",
            "2024-06-15T09:00:00Z",
            "2024-06-15T09:30:00Z",
            "2024-06-15T10:00:00Z",
        ]
        cond_values = [450.0, 600.0, 750.0, 900.0, 1050.0]
        
        last_report = None
        for t, c in zip(times, cond_values):
            ev = TelemetryEvent(
                sensor_id="WQ-TEST04",
                timestamp=t,
                readings={"pH": 7.3, "turbidity": 2.0, "conductivity": c, "temperature": 21.0}
            )
            last_report = self.detector.evaluate_event(ev, ev.readings)

        self.assertTrue(last_report.is_anomaly)
        self.assertIn("conductivity", last_report.contributing_metrics)


if __name__ == "__main__":
    unittest.main()
