"""
Automated Integration Tests for FastAPI REST Endpoints.
"""

import json
import unittest
from fastapi.testclient import TestClient
from app.main import app, processor


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        processor.reset()

    def test_post_events_normal_ingestion(self):
        payload = {
            "sensor_id": "WQ-S123",
            "timestamp": "2024-06-15T10:30:00Z",
            "readings": {
                "pH": 6.8,
                "turbidity": 2.1,
                "conductivity": 450.0,
                "temperature": 22.5
            },
            "source": "field"
        }
        response = self.client.post("/events", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "PROCESSED")
        self.assertFalse(data["is_duplicate"])
        self.assertEqual(data["resulting_state"]["sensor_id"], "WQ-S123")
        self.assertIsNotNone(data["audit_hash"])

    def test_post_events_idempotent_duplicate(self):
        payload = {
            "sensor_id": "WQ-S123",
            "timestamp": "2024-06-15T10:30:00Z",
            "readings": {"pH": 6.8, "turbidity": 2.1, "conductivity": 450.0, "temperature": 22.5},
            "source": "field"
        }
        # Ingest 1
        res1 = self.client.post("/events", json=payload)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["status"], "PROCESSED")

        # Ingest 2 (exact duplicate)
        res2 = self.client.post("/events", json=payload)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["status"], "DUPLICATE_SKIPPED")
        self.assertTrue(res2.json()["is_duplicate"])

    def test_replay_fixture_endpoint(self):
        req = {
            "fixture_name": "01_duplicate_packet_storm.json",
            "strategy": "source_priority",
            "verify_invariance": True
        }
        response = self.client.post("/replay", json=req)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("replay_summary", data)
        self.assertEqual(data["replay_summary"]["total_events_ingested"], 5)
        self.assertEqual(data["replay_summary"]["unique_events_processed"], 2)
        self.assertTrue(data["invariance_report"]["order_invariant"])

    def test_audit_verification_endpoint(self):
        # Ingest an event
        payload = {
            "sensor_id": "WQ-S123",
            "timestamp": "2024-06-15T10:30:00Z",
            "readings": {"pH": 7.0},
            "source": "field"
        }
        self.client.post("/events", json=payload)

        # Verify integrity
        response = self.client.post("/verify-integrity")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["chain_intact"])
        self.assertGreaterEqual(data["total_blocks"], 1)

    def test_export_csv_endpoint(self):
        payload = {
            "sensor_id": "WQ-S123",
            "timestamp": "2024-06-15T10:30:00Z",
            "readings": {"pH": 7.0, "turbidity": 2.0},
            "source": "field"
        }
        self.client.post("/events", json=payload)

        response = self.client.get("/export/csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("WQ-S123", response.text)


if __name__ == "__main__":
    unittest.main()
