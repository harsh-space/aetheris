"""
Unified IoT Telemetry Processing Engine.
Orchestrates Deduplication, State Reconstruction, Identity Resolution,
Statistical Anomaly Detection, Spatial Correlation, and Immutable Audit Logging.
"""

from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, Tuple
from engine.anomaly_detector import StatisticalMLAnomalyDetector
from engine.audit_ledger import AuditLedger
from engine.deduplicator import Deduplicator
from engine.models import (
    AnomalyReport,
    AuditRecord,
    ConflictDecisionTrace,
    SensorState,
    TelemetryEvent,
)
from engine.resolver import ConflictResolutionStrategy, SourcePriorityResolver, get_resolver
from engine.spatial_correlator import SpatialCorrelator
from engine.state_store import StateStore


class TelemetryProcessor:
    """
    Main real-time processing engine coordinating all telemetry subsystems.
    """

    def __init__(
        self,
        strategy_name: str = "source_priority",
        db_path: str = ":memory:"
    ):
        self.deduplicator = Deduplicator()
        self.resolver = get_resolver(strategy_name)
        self.state_store = StateStore(resolver=self.resolver)
        self.anomaly_detector = StatisticalMLAnomalyDetector()
        self.spatial_correlator = SpatialCorrelator()
        self.audit_ledger = AuditLedger(db_path=db_path)

        # Performance & event metrics
        self.total_received = 0
        self.total_duplicates = 0
        self.total_out_of_order = 0
        self.total_anomalies = 0

    def set_strategy(self, strategy_name: str) -> None:
        """Dynamically switches conflict resolution strategy."""
        self.resolver = get_resolver(strategy_name)
        self.state_store.set_resolver(self.resolver)

    def process_event(
        self,
        event: TelemetryEvent
    ) -> Tuple[SensorState, AnomalyReport, ConflictDecisionTrace, Optional[AuditRecord], bool, bool]:
        """
        Processes a single incoming telemetry event through the pipeline.
        Returns:
            (sensor_state, anomaly_report, conflict_trace, audit_record, is_duplicate, is_out_of_order)
        """
        self.total_received += 1

        # Step 1: Idempotency & Deduplication
        is_dup, fingerprint = self.deduplicator.is_duplicate(event)
        if is_dup:
            self.total_duplicates += 1
            curr_state = self.state_store.get_state(event.sensor_id)
            if curr_state is None:
                # In rare edge case where state was not stored, recreate dummy state
                curr_state = SensorState(
                    sensor_id=event.sensor_id,
                    last_event_time=event.timestamp,
                    readings={k: v for k, v in event.readings.items() if v is not None}
                )
            
            dummy_trace = ConflictDecisionTrace(
                strategy_used=self.resolver.__class__.__name__,
                resolution_notes=[f"Duplicate event ignored. Fingerprint: {fingerprint}"]
            )
            dummy_anomaly = AnomalyReport(explanation="Duplicate event skipped.")
            return curr_state, dummy_anomaly, dummy_trace, None, True, False

        # Step 2: Temporal State Store & Conflict Resolution
        updated_state, conflict_trace, is_out_of_order = self.state_store.process_event(
            event=event,
            fingerprint=fingerprint
        )
        if is_out_of_order:
            self.total_out_of_order += 1

        # Step 3: Statistical Machine Learning Anomaly Detection (NumPy/Pandas)
        anomaly_report = self.anomaly_detector.evaluate_event(
            event=event,
            merged_readings=updated_state.readings
        )

        # Step 4: Multi-Sensor Spatial Correlation
        if anomaly_report.is_anomaly:
            self.spatial_correlator.record_anomaly(event.sensor_id, event.timestamp, anomaly_report)
            from datetime import datetime
            event_dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            is_corroborated, affected_neighbors, spatial_diag = self.spatial_correlator.evaluate_spatial_correlation(
                sensor_id=event.sensor_id,
                current_dt=event_dt,
                current_report=anomaly_report,
                all_states=self.state_store.get_all_states()
            )
            anomaly_report.corroborated_by_neighbors = is_corroborated
            anomaly_report.details["spatial_diagnosis"] = spatial_diag
            anomaly_report.details["corroborated_neighbors"] = affected_neighbors
            self.total_anomalies += 1

        # Update state anomaly markers
        updated_state.is_anomalous = anomaly_report.is_anomaly
        updated_state.active_anomaly_type = anomaly_report.anomaly_type
        updated_state.last_anomaly_score = anomaly_report.anomaly_score

        # Step 5: Cryptographically Linked Audit Ledger
        action_name = "OUT_OF_ORDER_INGEST" if is_out_of_order else "TELEMETRY_INGEST"
        audit_rec = self.audit_ledger.append_record(
            action=action_name,
            sensor_id=event.sensor_id,
            event=event,
            event_fingerprint=fingerprint,
            resulting_state=updated_state,
            conflict_trace=conflict_trace,
            anomaly_report=anomaly_report
        )

        return updated_state, anomaly_report, conflict_trace, audit_rec, False, is_out_of_order

    def get_sensor_state(self, sensor_id: str) -> Optional[SensorState]:
        return self.state_store.get_state(sensor_id)

    def get_historical_state(self, sensor_id: str, timestamp_str: str) -> Optional[SensorState]:
        return self.state_store.get_state_at(sensor_id, timestamp_str)

    def get_all_states(self) -> Dict[str, SensorState]:
        return self.state_store.get_all_states()

    def get_audit_trail(self, sensor_id: Optional[str] = None, limit: int = 100) -> List[AuditRecord]:
        return self.audit_ledger.get_records(sensor_id=sensor_id, limit=limit)

    def verify_ledger(self) -> Tuple[bool, Optional[str]]:
        return self.audit_ledger.verify_integrity()

    def reset(self) -> None:
        """Resets all engine state."""
        self.deduplicator.clear()
        self.state_store.clear()
        self.anomaly_detector.reset()
        self.spatial_correlator.clear()
        self.audit_ledger.clear()
        self.total_received = 0
        self.total_duplicates = 0
        self.total_out_of_order = 0
        self.total_anomalies = 0
