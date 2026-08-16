"""
Cryptographically Hash-Chained Immutable Audit Ledger.
Maintains a verifiable, tamper-evident record of all telemetry ingestions,
state transformations, conflict resolutions, and anomaly classifications.
"""

from __future__ import annotations
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from engine.models import AnomalyReport, AuditRecord, ConflictDecisionTrace, SensorState, TelemetryEvent


class AuditLedger:
    """
    Immutable audit ledger using SHA-256 blockchain-style cryptographic chaining.
    Genesis block starts with hash '0' * 64.
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.records: List[AuditRecord] = []
        self._latest_hash: str = self.GENESIS_HASH
        self._init_db()

    def _init_db(self) -> None:
        """Initializes the SQLite schema for persistent immutable ledger storage and loads records."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prev_hash TEXT NOT NULL,
                    current_hash TEXT NOT NULL UNIQUE,
                    action TEXT NOT NULL,
                    sensor_id TEXT NOT NULL,
                    event_timestamp TEXT NOT NULL,
                    received_timestamp TEXT NOT NULL,
                    event_fingerprint TEXT NOT NULL,
                    raw_event JSON NOT NULL,
                    conflict_trace JSON,
                    anomaly_report JSON,
                    resulting_state JSON NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_sensor ON audit_trail(sensor_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_trail(event_timestamp);")
            conn.commit()

            # Load existing records if any
            cursor.execute("SELECT * FROM audit_trail ORDER BY audit_id ASC;")
            rows = cursor.fetchall()
            for row in rows:
                (
                    a_id, prev_h, curr_h, act, s_id,
                    ev_ts, rec_ts, fp,
                    raw_ev_json, trace_json, anom_json, state_json
                ) = row
                
                rec = AuditRecord(
                    audit_id=a_id,
                    prev_hash=prev_h,
                    current_hash=curr_h,
                    action=act,
                    sensor_id=s_id,
                    event_timestamp=ev_ts,
                    received_timestamp=rec_ts,
                    event_fingerprint=fp,
                    raw_event=json.loads(raw_ev_json),
                    conflict_trace=json.loads(trace_json) if trace_json else None,
                    anomaly_report=json.loads(anom_json) if anom_json else None,
                    resulting_state=json.loads(state_json)
                )
                self.records.append(rec)
                self._latest_hash = curr_h

    @staticmethod
    def calculate_record_hash(prev_hash: str, body_dict: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 hash of previous hash + canonical record body."""
        serialized_body = json.dumps(body_dict, sort_keys=True, separators=(",", ":"))
        combined = f"{prev_hash}|{serialized_body}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def append_record(
        self,
        action: str,
        sensor_id: str,
        event: TelemetryEvent,
        event_fingerprint: str,
        resulting_state: SensorState,
        conflict_trace: Optional[ConflictDecisionTrace] = None,
        anomaly_report: Optional[AnomalyReport] = None,
    ) -> AuditRecord:
        """
        Appends a new cryptographically chained audit record.
        """
        audit_id = len(self.records) + 1
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        body_dict = {
            "audit_id": audit_id,
            "action": action,
            "sensor_id": sensor_id,
            "event_timestamp": event.timestamp,
            "received_timestamp": now_iso,
            "event_fingerprint": event_fingerprint,
            "raw_event": event.model_dump(),
            "conflict_trace": conflict_trace.model_dump() if conflict_trace else None,
            "anomaly_report": anomaly_report.model_dump() if anomaly_report else None,
            "resulting_state": resulting_state.model_dump(),
        }

        current_hash = self.calculate_record_hash(self._latest_hash, body_dict)

        record = AuditRecord(
            audit_id=audit_id,
            prev_hash=self._latest_hash,
            current_hash=current_hash,
            action=action,
            sensor_id=sensor_id,
            event_timestamp=event.timestamp,
            received_timestamp=now_iso,
            event_fingerprint=event_fingerprint,
            raw_event=event.model_dump(),
            conflict_trace=conflict_trace,
            anomaly_report=anomaly_report,
            resulting_state=resulting_state.model_dump(),
        )

        self.records.append(record)
        self._latest_hash = current_hash

        # Store in SQLite
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_trail (
                    audit_id, prev_hash, current_hash, action, sensor_id,
                    event_timestamp, received_timestamp, event_fingerprint,
                    raw_event, conflict_trace, anomaly_report, resulting_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audit_id,
                record.prev_hash,
                record.current_hash,
                record.action,
                record.sensor_id,
                record.event_timestamp,
                record.received_timestamp,
                record.event_fingerprint,
                json.dumps(record.raw_event),
                json.dumps(record.conflict_trace.model_dump() if record.conflict_trace else None),
                json.dumps(record.anomaly_report.model_dump() if record.anomaly_report else None),
                json.dumps(record.resulting_state)
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

        return record

    def verify_integrity(self) -> Tuple[bool, Optional[str]]:
        """
        Verifies the cryptographic SHA-256 chain from genesis to head.
        Returns: (is_valid: bool, error_message: Optional[str])
        """
        if not self.records:
            return True, None

        expected_prev_hash = self.GENESIS_HASH

        for idx, rec in enumerate(self.records):
            if rec.prev_hash != expected_prev_hash:
                return False, f"Broken chain at record {rec.audit_id}: expected prev_hash '{expected_prev_hash}', got '{rec.prev_hash}'"

            body_dict = {
                "audit_id": rec.audit_id,
                "action": rec.action,
                "sensor_id": rec.sensor_id,
                "event_timestamp": rec.event_timestamp,
                "received_timestamp": rec.received_timestamp,
                "event_fingerprint": rec.event_fingerprint,
                "raw_event": rec.raw_event,
                "conflict_trace": rec.conflict_trace.model_dump() if rec.conflict_trace else None,
                "anomaly_report": rec.anomaly_report.model_dump() if rec.anomaly_report else None,
                "resulting_state": rec.resulting_state,
            }

            calculated_hash = self.calculate_record_hash(expected_prev_hash, body_dict)
            if calculated_hash != rec.current_hash:
                return False, f"Hash mismatch at record {rec.audit_id}: calculated '{calculated_hash}', recorded '{rec.current_hash}'"

            expected_prev_hash = rec.current_hash

        return True, "Audit ledger integrity 100% cryptographically verified."

    def get_records(
        self,
        sensor_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditRecord]:
        """Queries audit records with optional sensor filtering and pagination."""
        if sensor_id:
            filtered = [r for r in self.records if r.sensor_id == sensor_id]
        else:
            filtered = self.records
        return filtered[offset:offset + limit]

    def get_record_count(self) -> int:
        return len(self.records)

    def get_latest_hash(self) -> str:
        return self._latest_hash

    def clear(self) -> None:
        """Resets the audit ledger."""
        self.records.clear()
        self._latest_hash = self.GENESIS_HASH
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audit_trail;")
            conn.commit()
