"""
Identity Resolution and Multi-Source Conflict Resolution Engine.
Implements configurable strategies for resolving overlapping, competing, or ambiguous sensor measurements.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from engine.models import ConflictDecisionTrace, MetricState, SensorSource


class ConflictResolutionStrategy(ABC):
    """Abstract base class for conflict resolution strategies."""

    @abstractmethod
    def resolve(
        self,
        sensor_id: str,
        incoming_readings: Dict[str, float],
        incoming_source: str,
        incoming_timestamp: str,
        current_metric_states: Dict[str, MetricState]
    ) -> Tuple[Dict[str, float], Dict[str, MetricState], ConflictDecisionTrace]:
        """
        Resolves conflicts between incoming readings and current metric states.
        Returns: (merged_readings, updated_metric_states, decision_trace)
        """
        pass


class SourcePriorityResolver(ConflictResolutionStrategy):
    """
    Resolves conflicts using a strict hierarchy of source reliability:
    lab (1.0) > calibration (0.95) > field (0.80) > mobile (0.60) > backup (0.50)
    """

    DEFAULT_SOURCE_PRIORITY: Dict[str, float] = {
        SensorSource.LAB.value: 1.0,
        SensorSource.CALIBRATION.value: 0.95,
        SensorSource.FIELD.value: 0.80,
        SensorSource.MOBILE.value: 0.60,
        SensorSource.BACKUP.value: 0.50,
    }

    def __init__(self, priority_map: Optional[Dict[str, float]] = None):
        self.priority_map = priority_map or self.DEFAULT_SOURCE_PRIORITY

    def get_source_weight(self, source: str) -> float:
        return self.priority_map.get(source.lower(), 0.5)

    def resolve(
        self,
        sensor_id: str,
        incoming_readings: Dict[str, float],
        incoming_source: str,
        incoming_timestamp: str,
        current_metric_states: Dict[str, MetricState]
    ) -> Tuple[Dict[str, float], Dict[str, MetricState], ConflictDecisionTrace]:
        merged_readings: Dict[str, float] = {k: v.value for k, v in current_metric_states.items()}
        updated_states: Dict[str, MetricState] = dict(current_metric_states)
        conflicting_fields: List[str] = []
        resolution_notes: List[str] = []

        in_weight = self.get_source_weight(incoming_source)
        in_dt = datetime.fromisoformat(incoming_timestamp.replace("Z", "+00:00"))

        for metric, in_val in incoming_readings.items():
            if metric not in updated_states:
                # New metric for sensor - accept directly
                updated_states[metric] = MetricState(
                    value=in_val,
                    timestamp=incoming_timestamp,
                    source=incoming_source,
                    confidence=in_weight
                )
                merged_readings[metric] = in_val
                resolution_notes.append(f"Metric '{metric}' initialized from {incoming_source} (val={in_val})")
            else:
                curr_state = updated_states[metric]
                curr_weight = self.get_source_weight(curr_state.source)
                curr_dt = datetime.fromisoformat(curr_state.timestamp.replace("Z", "+00:00"))

                # Check conflict
                if in_dt >= curr_dt:
                    # Incoming is newer or simultaneous
                    if in_dt == curr_dt and in_weight < curr_weight:
                        # Simultaneous but lower priority source - retain existing
                        conflicting_fields.append(metric)
                        resolution_notes.append(
                            f"Metric '{metric}' conflict at {incoming_timestamp}: kept existing {curr_state.source} "
                            f"(weight={curr_weight}) over {incoming_source} (weight={in_weight})"
                        )
                    else:
                        conflicting_fields.append(metric)
                        updated_states[metric] = MetricState(
                            value=in_val,
                            timestamp=incoming_timestamp,
                            source=incoming_source,
                            confidence=in_weight
                        )
                        merged_readings[metric] = in_val
                        resolution_notes.append(
                            f"Metric '{metric}' updated: accepted {incoming_source} (val={in_val}, weight={in_weight}) "
                            f"over previous {curr_state.source} (val={curr_state.value}, weight={curr_weight})"
                        )
                else:
                    # Incoming is older (out-of-order event)
                    if in_weight > curr_weight * 1.5:
                        # Much higher authority source even if slightly delayed
                        conflicting_fields.append(metric)
                        resolution_notes.append(
                            f"Metric '{metric}' out-of-order high-authority override: {incoming_source} "
                            f"(val={in_val}) at {incoming_timestamp} logged"
                        )
                    else:
                        resolution_notes.append(
                            f"Metric '{metric}' out-of-order older reading ignored for current state: "
                            f"{incoming_source} timestamp ({incoming_timestamp}) < current ({curr_state.timestamp})"
                        )

        trace = ConflictDecisionTrace(
            strategy_used="SourcePriorityResolver",
            conflicting_fields=conflicting_fields,
            resolution_notes=resolution_notes,
            merged_readings=merged_readings
        )
        return merged_readings, updated_states, trace


class ConfidenceWeightedResolver(ConflictResolutionStrategy):
    """
    Weighted Bayesian/Quality blending: When competing readings arrive for the same time window,
    blends readings proportionally to source confidence and quality metrics.
    """

    DEFAULT_SOURCE_WEIGHTS: Dict[str, float] = {
        SensorSource.LAB.value: 0.99,
        SensorSource.CALIBRATION.value: 0.95,
        SensorSource.FIELD.value: 0.80,
        SensorSource.MOBILE.value: 0.65,
        SensorSource.BACKUP.value: 0.50,
    }

    def __init__(self, source_weights: Optional[Dict[str, float]] = None):
        self.source_weights = source_weights or self.DEFAULT_SOURCE_WEIGHTS

    def resolve(
        self,
        sensor_id: str,
        incoming_readings: Dict[str, float],
        incoming_source: str,
        incoming_timestamp: str,
        current_metric_states: Dict[str, MetricState]
    ) -> Tuple[Dict[str, float], Dict[str, MetricState], ConflictDecisionTrace]:
        merged_readings: Dict[str, float] = {k: v.value for k, v in current_metric_states.items()}
        updated_states: Dict[str, MetricState] = dict(current_metric_states)
        conflicting_fields: List[str] = []
        resolution_notes: List[str] = []

        in_weight = self.source_weights.get(incoming_source.lower(), 0.5)
        in_dt = datetime.fromisoformat(incoming_timestamp.replace("Z", "+00:00"))

        for metric, in_val in incoming_readings.items():
            if metric not in updated_states:
                updated_states[metric] = MetricState(
                    value=in_val,
                    timestamp=incoming_timestamp,
                    source=incoming_source,
                    confidence=in_weight
                )
                merged_readings[metric] = in_val
                resolution_notes.append(f"Metric '{metric}' added from {incoming_source} with confidence {in_weight:.2f}")
            else:
                curr_state = updated_states[metric]
                curr_weight = self.source_weights.get(curr_state.source.lower(), 0.5)
                curr_dt = datetime.fromisoformat(curr_state.timestamp.replace("Z", "+00:00"))

                # Check if readings are concurrent within 60 seconds
                time_diff_sec = abs((in_dt - curr_dt).total_seconds())

                if time_diff_sec <= 60.0 and in_dt == curr_dt:
                    # Concurrent simultaneous reading conflict -> Confidence-Weighted Fusion
                    conflicting_fields.append(metric)
                    total_w = in_weight + curr_weight
                    fused_val = (in_val * in_weight + curr_state.value * curr_weight) / total_w
                    fused_val = round(fused_val, 4)
                    
                    winner_source = incoming_source if in_weight >= curr_weight else curr_state.source
                    updated_states[metric] = MetricState(
                        value=fused_val,
                        timestamp=incoming_timestamp,
                        source=f"weighted_fusion({curr_state.source}+{incoming_source})",
                        confidence=min(1.0, (in_weight + curr_weight) / 1.5)
                    )
                    merged_readings[metric] = fused_val
                    resolution_notes.append(
                        f"Metric '{metric}' weighted fusion: {curr_state.value} ({curr_state.source}, w={curr_weight}) + "
                        f"{in_val} ({incoming_source}, w={in_weight}) -> {fused_val}"
                    )
                elif in_dt >= curr_dt:
                    # New reading takes precedence
                    updated_states[metric] = MetricState(
                        value=in_val,
                        timestamp=incoming_timestamp,
                        source=incoming_source,
                        confidence=in_weight
                    )
                    merged_readings[metric] = in_val
                    resolution_notes.append(f"Metric '{metric}' updated to new value {in_val} from {incoming_source}")
                else:
                    resolution_notes.append(f"Metric '{metric}' older reading at {incoming_timestamp} preserved in timeline")

        trace = ConflictDecisionTrace(
            strategy_used="ConfidenceWeightedResolver",
            conflicting_fields=conflicting_fields,
            resolution_notes=resolution_notes,
            merged_readings=merged_readings
        )
        return merged_readings, updated_states, trace


class LatestResolver(ConflictResolutionStrategy):
    """
    Simple, high-speed resolver that assigns metric state to the reading with the latest timestamp.
    Preserves other non-overlapping metrics (partial merges).
    """

    def resolve(
        self,
        sensor_id: str,
        incoming_readings: Dict[str, float],
        incoming_source: str,
        incoming_timestamp: str,
        current_metric_states: Dict[str, MetricState]
    ) -> Tuple[Dict[str, float], Dict[str, MetricState], ConflictDecisionTrace]:
        merged_readings: Dict[str, float] = {k: v.value for k, v in current_metric_states.items()}
        updated_states: Dict[str, MetricState] = dict(current_metric_states)
        conflicting_fields: List[str] = []
        resolution_notes: List[str] = []

        in_dt = datetime.fromisoformat(incoming_timestamp.replace("Z", "+00:00"))

        for metric, in_val in incoming_readings.items():
            if metric not in updated_states:
                updated_states[metric] = MetricState(
                    value=in_val,
                    timestamp=incoming_timestamp,
                    source=incoming_source,
                    confidence=1.0
                )
                merged_readings[metric] = in_val
                resolution_notes.append(f"Metric '{metric}' initial value {in_val}")
            else:
                curr_state = updated_states[metric]
                curr_dt = datetime.fromisoformat(curr_state.timestamp.replace("Z", "+00:00"))

                if in_dt >= curr_dt:
                    conflicting_fields.append(metric)
                    updated_states[metric] = MetricState(
                        value=in_val,
                        timestamp=incoming_timestamp,
                        source=incoming_source,
                        confidence=1.0
                    )
                    merged_readings[metric] = in_val
                    resolution_notes.append(
                        f"Metric '{metric}' latest value updated: {curr_state.value} -> {in_val} "
                        f"(at {incoming_timestamp})"
                    )
                else:
                    resolution_notes.append(
                        f"Metric '{metric}' out-of-order reading {in_val} at {incoming_timestamp} "
                        f"bypassed current state ({curr_state.timestamp})"
                    )

        trace = ConflictDecisionTrace(
            strategy_used="LatestResolver",
            conflicting_fields=conflicting_fields,
            resolution_notes=resolution_notes,
            merged_readings=merged_readings
        )
        return merged_readings, updated_states, trace


def get_resolver(strategy_name: str = "source_priority") -> ConflictResolutionStrategy:
    """Factory method to get a conflict resolution strategy by name."""
    s = strategy_name.lower().strip()
    if s in ("source_priority", "source", "priority"):
        return SourcePriorityResolver()
    elif s in ("confidence_weighted", "weighted", "confidence"):
        return ConfidenceWeightedResolver()
    elif s in ("latest", "timestamp"):
        return LatestResolver()
    else:
        return SourcePriorityResolver()
