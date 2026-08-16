import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.models import TelemetryEvent
from engine.processor import TelemetryProcessor


def generate_synthetic_telemetry(count: int = 10000) -> list[TelemetryEvent]:
    sensors = [f"WQ-S{100 + (i % 20)}" for i in range(20)]
    sources = ["field", "field", "backup", "lab", "calibration"]
    events = []
    
    base_time = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    for i in range(count):
        s_id = random.choice(sensors)
        s_src = random.choice(sources)
        # Introduce 10% out-of-order jitter and 5% duplicate timestamps
        jitter_sec = random.randint(-120, 120) if random.random() < 0.10 else i * 2
        ts = (base_time + timedelta(seconds=jitter_sec)).isoformat().replace("+00:00", "Z")

        # 2% severe anomalies
        if random.random() < 0.02:
            readings = {
                "pH": round(random.uniform(3.0, 5.0), 2),
                "turbidity": round(random.uniform(40.0, 150.0), 1),
                "conductivity": round(random.uniform(1100.0, 2500.0), 1),
                "temperature": round(random.uniform(20.0, 32.0), 1),
            }
        else:
            readings = {
                "pH": round(random.uniform(7.1, 7.6), 2),
                "turbidity": round(random.uniform(1.8, 3.5), 1),
                "conductivity": round(random.uniform(380.0, 460.0), 1),
                "temperature": round(random.uniform(19.0, 23.0), 1),
            }

        events.append(TelemetryEvent(
            sensor_id=s_id,
            timestamp=ts,
            readings=readings,
            source=s_src
        ))
    return events


def run_benchmark():
    print("=" * 70)
    print(" HYDRO-PULSE SYSTEM BENCHMARK (10,000 EVENTS)")
    print("=" * 70)

    print("Generating 10,000 synthetic IoT events with jitter, bursts & anomalies...")
    events = generate_synthetic_telemetry(10000)

    processor = TelemetryProcessor(strategy_name="source_priority")

    print("Starting real-time pipeline ingestion benchmark...")
    t_start = time.perf_counter()

    for ev in events:
        processor.process_event(ev)

    t_total = time.perf_counter() - t_start
    throughput = len(events) / t_total
    avg_latency_us = (t_total / len(events)) * 1_000_000

    print("-" * 70)
    print(f"Total Events Ingested:       {len(events):,}")
    print(f"Total Execution Time:        {t_total:.3f} seconds")
    print(f"Throughput:                  {throughput:,.1f} events/second")
    print(f"Mean Latency per Event:      {avg_latency_us:.2f} microseconds ({avg_latency_us/1000:.4f} ms)")
    print(f"Duplicates Filtered:         {processor.total_duplicates:,}")
    print(f"Out-of-Order Reindexed:      {processor.total_out_of_order:,}")
    print(f"ML Anomalies Classified:     {processor.total_anomalies:,}")
    print(f"Audit Ledger Block Height:   {processor.audit_ledger.get_record_count():,}")

    print("\nVerifying 10,000-block SHA-256 cryptographic audit chain...")
    t_audit_start = time.perf_counter()
    is_valid, msg = processor.verify_ledger()
    t_audit = time.perf_counter() - t_audit_start

    print(f"Audit Chain Valid:           {is_valid}")
    print(f"Audit Verification Duration: {t_audit * 1000:.2f} ms")
    print("=" * 70)


if __name__ == "__main__":
    run_benchmark()
