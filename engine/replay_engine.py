"""
Deterministic Temporal Replay Engine.
Enables full reproducible simulation, auditing, order-invariance verification,
and drift detection across historical telemetry streams.
"""

from __future__ import annotations
import random
import time
from typing import Any, Dict, List, Optional, Tuple
from engine.models import ReplayResult, SensorState, TelemetryEvent
from engine.processor import TelemetryProcessor


class ReplayEngine:
    """
    Executes and validates deterministic temporal replays of IoT telemetry streams.
    """

    def __init__(self, strategy_name: str = "source_priority"):
        self.strategy_name = strategy_name

    def replay_stream(
        self,
        events: List[TelemetryEvent],
        strategy_name: Optional[str] = None,
        shuffle: bool = False,
        seed: Optional[int] = 42
    ) -> Tuple[TelemetryProcessor, ReplayResult]:
        """
        Replays a list of telemetry events through a fresh processor instance.
        """
        strat = strategy_name or self.strategy_name
        processor = TelemetryProcessor(strategy_name=strat)

        event_list = list(events)
        if shuffle:
            rng = random.Random(seed)
            rng.shuffle(event_list)

        start_time = time.perf_counter()
        duplicates_count = 0
        out_of_order_count = 0
        anomalies_count = 0
        unique_processed = 0

        for event in event_list:
            state, anom, trace, audit_rec, is_dup, is_ooo = processor.process_event(event)
            if is_dup:
                duplicates_count += 1
            else:
                unique_processed += 1
                if is_ooo:
                    out_of_order_count += 1
                if anom.is_anomaly:
                    anomalies_count += 1

        exec_duration_ms = (time.perf_counter() - start_time) * 1000.0
        ledger_valid, _ = processor.verify_ledger()

        all_states = processor.get_all_states()
        serialized_states = {s_id: s.model_dump() for s_id, s in all_states.items()}

        result = ReplayResult(
            total_events_ingested=len(event_list),
            unique_events_processed=unique_processed,
            duplicates_filtered=duplicates_count,
            out_of_order_reordered=out_of_order_count,
            anomalies_detected=anomalies_count,
            final_sensor_count=len(all_states),
            audit_ledger_valid=ledger_valid,
            execution_time_ms=round(exec_duration_ms, 2),
            sensor_states=serialized_states
        )
        return processor, result

    def verify_order_invariance(
        self,
        events: List[TelemetryEvent],
        permutations: int = 5,
        tolerance: float = 1e-5
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verifies that replaying the exact same set of events in multiple different random orderings
        produces identical final reconstructed states and readings.
        """
        if not events:
            return True, "Empty event list is trivially invariant.", {}

        # 1. Baseline Run: Chronological Order
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        _, baseline_res = self.replay_stream(sorted_events, shuffle=False)
        baseline_states = baseline_res.sensor_states

        mismatches: List[str] = []

        # 2. Permutation Runs
        for run_idx in range(permutations):
            _, perm_res = self.replay_stream(events, shuffle=True, seed=1000 + run_idx)
            perm_states = perm_res.sensor_states

            # Check sensor keys
            if set(baseline_states.keys()) != set(perm_states.keys()):
                mismatches.append(f"Run {run_idx}: Sensor ID set mismatch ({set(baseline_states.keys())} vs {set(perm_states.keys())})")
                continue

            for s_id, b_state in baseline_states.items():
                p_state = perm_states[s_id]
                b_readings = b_state.get("readings", {})
                p_readings = p_state.get("readings", {})

                for metric, b_val in b_readings.items():
                    if metric not in p_readings:
                        mismatches.append(f"Run {run_idx}, sensor {s_id}: missing metric '{metric}' in permuted replay")
                    else:
                        p_val = p_readings[metric]
                        if abs(b_val - p_val) > tolerance:
                            mismatches.append(
                                f"Run {run_idx}, sensor {s_id}, metric '{metric}': baseline={b_val} != permuted={p_val}"
                            )

        is_invariant = len(mismatches) == 0
        msg = "100% Deterministic & Order Invariant" if is_invariant else f"Order variance detected: {len(mismatches)} discrepancies"
        
        details = {
            "is_invariant": is_invariant,
            "permutations_tested": permutations,
            "total_events": len(events),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches[:10]
        }
        return is_invariant, msg, details
