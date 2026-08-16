"""
Bi-Temporal State Store and Timeline Manager.
Manages per-sensor state evolution, out-of-order event re-anchoring, partial reading merges,
and point-in-time deterministic historical state reconstruction.
"""

from __future__ import annotations
from bisect import bisect_right, insort_right
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from engine.models import ConflictDecisionTrace, MetricState, SensorState, TelemetryEvent
from engine.resolver import ConflictResolutionStrategy, SourcePriorityResolver, get_resolver


class TimelineEntry:
    """Represents a single point-in-time telemetry event in the sensor's timeline."""

    def __init__(self, event: TelemetryEvent, fingerprint: str):
        self.event = event
        self.fingerprint = fingerprint
        self.timestamp_dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))

    def __lt__(self, other: TimelineEntry) -> bool:
        return self.timestamp_dt < other.timestamp_dt

    def __le__(self, other: TimelineEntry) -> bool:
        return self.timestamp_dt <= other.timestamp_dt


class SensorTimeline:
    """Ordered event history for an individual sensor."""

    def __init__(self, sensor_id: str):
        self.sensor_id = sensor_id
        self.entries: List[TimelineEntry] = []

    def insert_event(self, event: TelemetryEvent, fingerprint: str) -> Tuple[bool, int]:
        """
        Inserts an event in chronological order.
        Returns: (is_out_of_order: bool, index: int)
        """
        new_entry = TimelineEntry(event, fingerprint)
        if not self.entries:
            self.entries.append(new_entry)
            return False, 0

        latest_dt = self.entries[-1].timestamp_dt
        if new_entry.timestamp_dt >= latest_dt:
            self.entries.append(new_entry)
            return False, len(self.entries) - 1

        # Out-of-order insertion using bisect
        idx = bisect_right([e.timestamp_dt for e in self.entries], new_entry.timestamp_dt)
        self.entries.insert(idx, new_entry)
        return True, idx

    def get_events_up_to(self, target_dt: datetime) -> List[TimelineEntry]:
        """Returns all timeline entries up to and including target_dt."""
        idx = bisect_right([e.timestamp_dt for e in self.entries], target_dt)
        return self.entries[:idx]


class StateStore:
    """
    Central state store for IoT sensor fleet.
    Reconstructs states deterministically from ordered timelines.
    """

    def __init__(self, resolver: Optional[ConflictResolutionStrategy] = None):
        self.resolver: ConflictResolutionStrategy = resolver or SourcePriorityResolver()
        self.timelines: Dict[str, SensorTimeline] = {}
        self.current_states: Dict[str, SensorState] = {}

    def set_resolver(self, resolver: ConflictResolutionStrategy) -> None:
        """Dynamically update conflict resolution strategy and rebuild states."""
        self.resolver = resolver
        self.rebuild_all_states()

    def process_event(
        self,
        event: TelemetryEvent,
        fingerprint: str
    ) -> Tuple[SensorState, ConflictDecisionTrace, bool]:
        """
        Ingests an event, updates the timeline, merges partial readings,
        resolves conflicts, and returns the updated state.
        Returns: (updated_state, conflict_trace, is_out_of_order)
        """
        sensor_id = event.sensor_id
        if sensor_id not in self.timelines:
            self.timelines[sensor_id] = SensorTimeline(sensor_id)

        timeline = self.timelines[sensor_id]
        is_out_of_order, _ = timeline.insert_event(event, fingerprint)

        if is_out_of_order:
            # Reconstruct the entire timeline state to guarantee deterministic order
            state, trace = self._reconstruct_timeline_state(sensor_id)
        else:
            # Fast-path: incremental update
            state, trace = self._apply_incremental_event(sensor_id, event)

        self.current_states[sensor_id] = state
        return state, trace, is_out_of_order

    def _apply_incremental_event(
        self,
        sensor_id: str,
        event: TelemetryEvent
    ) -> Tuple[SensorState, ConflictDecisionTrace]:
        curr_state = self.current_states.get(sensor_id)
        metric_states = dict(curr_state.metric_states) if curr_state else {}

        readings_dict = {k: v for k, v in event.readings.items() if v is not None}
        merged_readings, updated_metric_states, trace = self.resolver.resolve(
            sensor_id=sensor_id,
            incoming_readings=readings_dict,
            incoming_source=event.source,
            incoming_timestamp=event.timestamp,
            current_metric_states=metric_states
        )

        version = (curr_state.version + 1) if curr_state else 1
        total_processed = (curr_state.total_events_processed + 1) if curr_state else 1

        new_state = SensorState(
            sensor_id=sensor_id,
            last_event_time=event.timestamp,
            readings=merged_readings,
            metric_states=updated_metric_states,
            version=version,
            total_events_processed=total_processed,
            last_source=event.source,
            last_updated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        return new_state, trace

    def _reconstruct_timeline_state(
        self,
        sensor_id: str,
        up_to_dt: Optional[datetime] = None
    ) -> Tuple[SensorState, ConflictDecisionTrace]:
        timeline = self.timelines.get(sensor_id)
        if not timeline or not timeline.entries:
            empty_state = SensorState(
                sensor_id=sensor_id,
                last_event_time="",
                readings={},
                metric_states={}
            )
            return empty_state, ConflictDecisionTrace(strategy_used=self.resolver.__class__.__name__)

        entries = timeline.entries
        if up_to_dt is not None:
            entries = timeline.get_events_up_to(up_to_dt)
            if not entries:
                empty_state = SensorState(
                    sensor_id=sensor_id,
                    last_event_time="",
                    readings={},
                    metric_states={}
                )
                return empty_state, ConflictDecisionTrace(strategy_used=self.resolver.__class__.__name__)

        metric_states: Dict[str, MetricState] = {}
        last_event: Optional[TelemetryEvent] = None
        last_trace: Optional[ConflictDecisionTrace] = None

        for entry in entries:
            event = entry.event
            last_event = event
            readings_dict = {k: v for k, v in event.readings.items() if v is not None}
            merged_readings, metric_states, last_trace = self.resolver.resolve(
                sensor_id=sensor_id,
                incoming_readings=readings_dict,
                incoming_source=event.source,
                incoming_timestamp=event.timestamp,
                current_metric_states=metric_states
            )

        merged_readings = {k: v.value for k, v in metric_states.items()}
        final_state = SensorState(
            sensor_id=sensor_id,
            last_event_time=last_event.timestamp if last_event else "",
            readings=merged_readings,
            metric_states=metric_states,
            version=len(entries),
            total_events_processed=len(entries),
            last_source=last_event.source if last_event else "field",
            last_updated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        return final_state, last_trace or ConflictDecisionTrace(strategy_used=self.resolver.__class__.__name__)

    def get_state(self, sensor_id: str) -> Optional[SensorState]:
        """Returns the current resolved state for a sensor."""
        return self.current_states.get(sensor_id)

    def get_state_at(self, sensor_id: str, target_timestamp: str) -> Optional[SensorState]:
        """
        Reconstructs the exact state of a sensor at a specific point in time in the past (bi-temporal).
        """
        if sensor_id not in self.timelines:
            return None
        clean_ts = target_timestamp.replace("Z", "+00:00")
        target_dt = datetime.fromisoformat(clean_ts)
        state, _ = self._reconstruct_timeline_state(sensor_id, up_to_dt=target_dt)
        return state

    def get_all_states(self) -> Dict[str, SensorState]:
        """Returns map of sensor_id -> SensorState."""
        return self.current_states

    def get_all_sensor_ids(self) -> List[str]:
        """Returns list of all active sensor IDs."""
        return sorted(list(self.timelines.keys()))

    def get_timeline_events(self, sensor_id: str) -> List[TelemetryEvent]:
        """Returns chronological list of events for a sensor."""
        if sensor_id not in self.timelines:
            return []
        return [entry.event for entry in self.timelines[sensor_id].entries]

    def rebuild_all_states(self) -> None:
        """Reconstructs state for all sensors from scratch."""
        for sensor_id in list(self.timelines.keys()):
            state, _ = self._reconstruct_timeline_state(sensor_id)
            self.current_states[sensor_id] = state

    def clear(self) -> None:
        """Clears all timelines and states."""
        self.timelines.clear()
        self.current_states.clear()
