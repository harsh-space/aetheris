"""
Core data models for IoT Telemetry, State Representation, Anomaly Detection, and Audit Trails.
"""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SensorSource(str, Enum):
    FIELD = "field"
    BACKUP = "backup"
    LAB = "lab"
    CALIBRATION = "calibration"
    MOBILE = "mobile"


class AnomalySeverity(str, Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyType(str, Enum):
    NONE = "NONE"
    MULTIVARIATE_OUTLIER = "MULTIVARIATE_OUTLIER"
    TEMPORAL_RATE_OF_CHANGE = "TEMPORAL_RATE_OF_CHANGE"
    THERMAL_PH_COUPLING = "THERMAL_PH_COUPLING"
    SENSOR_DRIFT = "SENSOR_DRIFT"
    SPATIAL_PLUME = "SPATIAL_PLUME"
    OUT_OF_BOUNDS = "OUT_OF_BOUNDS"


class TelemetryEvent(BaseModel):
    sensor_id: str = Field(..., description="Unique identifier of the IoT sensor node (e.g. WQ-S123)")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of the measurement")
    readings: Dict[str, Optional[float]] = Field(..., description="Dictionary of metric measurements e.g. pH, turbidity, conductivity, temperature")
    source: str = Field(default="field", description="Source of the event (e.g. field, backup, lab, calibration)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional sensor metadata like location coordinates, battery, firmware")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        try:
            clean_ts = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except Exception as e:
            raise ValueError(f"Invalid ISO 8601 timestamp format: {v}") from e

    @field_validator("readings")
    @classmethod
    def clean_readings(cls, v: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
        cleaned: Dict[str, Optional[float]] = {}
        for k, val in v.items():
            if val is not None:
                try:
                    cleaned[k.strip()] = float(val)
                except (ValueError, TypeError):
                    pass
        return cleaned


class MetricState(BaseModel):
    value: float
    timestamp: str
    source: str
    confidence: float = 1.0


class SensorState(BaseModel):
    sensor_id: str
    last_event_time: str
    readings: Dict[str, float] = Field(default_factory=dict)
    metric_states: Dict[str, MetricState] = Field(default_factory=dict)
    version: int = 1
    total_events_processed: int = 0
    last_source: str = "field"
    is_anomalous: bool = False
    active_anomaly_type: AnomalyType = AnomalyType.NONE
    last_anomaly_score: float = 0.0
    last_updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))


class AnomalyReport(BaseModel):
    is_anomaly: bool = False
    anomaly_type: AnomalyType = AnomalyType.NONE
    severity: AnomalySeverity = AnomalySeverity.NORMAL
    anomaly_score: float = 0.0
    mahalanobis_distance: Optional[float] = None
    drift_score: Optional[float] = None
    corroborated_by_neighbors: bool = False
    contributing_metrics: List[str] = Field(default_factory=list)
    explanation: str = "Normal operating conditions."
    details: Dict[str, Any] = Field(default_factory=dict)


class ConflictDecisionTrace(BaseModel):
    strategy_used: str
    conflicting_fields: List[str] = Field(default_factory=list)
    resolution_notes: List[str] = Field(default_factory=list)
    merged_readings: Dict[str, float] = Field(default_factory=dict)


class AuditRecord(BaseModel):
    audit_id: int
    prev_hash: str
    current_hash: str
    action: str
    sensor_id: str
    event_timestamp: str
    received_timestamp: str
    event_fingerprint: str
    raw_event: Dict[str, Any]
    conflict_trace: Optional[ConflictDecisionTrace] = None
    anomaly_report: Optional[AnomalyReport] = None
    resulting_state: Dict[str, Any]


class ReplayResult(BaseModel):
    total_events_ingested: int
    unique_events_processed: int
    duplicates_filtered: int
    out_of_order_reordered: int
    anomalies_detected: int
    final_sensor_count: int
    audit_ledger_valid: bool
    execution_time_ms: float
    sensor_states: Dict[str, Dict[str, Any]]
