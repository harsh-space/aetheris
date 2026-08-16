"""
Aetheris Command-Line Interface (CLI).
Allows engineers to ingest telemetry, run replay simulations, verify audit chain integrity,
and inspect fleet states from the terminal.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from engine.models import TelemetryEvent
from engine.processor import TelemetryProcessor
from engine.replay_engine import ReplayEngine


def get_default_processor() -> TelemetryProcessor:
    return TelemetryProcessor(strategy_name="source_priority", db_path="iot_audit_ledger.db")


def cmd_ingest(args):
    processor = get_default_processor()
    readings = {}
    if args.ph is not None: readings["pH"] = args.ph
    if args.turbidity is not None: readings["turbidity"] = args.turbidity
    if args.conductivity is not None: readings["conductivity"] = args.conductivity
    if args.temperature is not None: readings["temperature"] = args.temperature

    timestamp = args.timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    event = TelemetryEvent(
        sensor_id=args.sensor,
        timestamp=timestamp,
        readings=readings,
        source=args.source
    )

    state, anom, trace, audit_rec, is_dup, is_ooo = processor.process_event(event)
    print("=" * 60)
    print(f" AETHERIS EVENT INGESTION REPORT")
    print("=" * 60)
    print(f"Status:             {'DUPLICATE_SKIPPED' if is_dup else ('OUT_OF_ORDER_REINDEXED' if is_ooo else 'PROCESSED')}")
    print(f"Sensor ID:          {state.sensor_id}")
    print(f"Event Timestamp:    {event.timestamp}")
    print(f"Resolved Readings:  {state.readings}")
    print(f"Strategy Used:      {trace.strategy_used}")
    print(f"Anomaly Detected:   {anom.is_anomaly} ({anom.anomaly_type.value})")
    print(f"Anomaly Detail:     {anom.explanation}")
    if audit_rec:
        print(f"Audit SHA-256 Hash: {audit_rec.current_hash}")
    print("=" * 60)


def cmd_replay(args):
    fixture_path = Path("fixtures") / args.fixture
    if not fixture_path.exists():
        fixture_path = Path("fixtures") / f"{args.fixture}.json"
    if not fixture_path.exists():
        print(f"Error: Fixture file '{args.fixture}' not found in fixtures/ directory.", file=sys.stderr)
        sys.exit(1)

    with open(fixture_path, "r", encoding="utf-8") as f:
        raw_events = json.load(f)
        events = [TelemetryEvent(**item) for item in raw_events]

    if args.persist:
        processor = get_default_processor()
        start_time = time.perf_counter()
        duplicates_count = 0
        out_of_order_count = 0
        anomalies_count = 0
        unique_processed = 0

        for event in events:
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

        print("=" * 60)
        print(f" AETHERIS TEMPORAL REPLAY (PERSISTED): {fixture_path.name}")
        print("=" * 60)
        print(f"Total Ingested:        {len(events)}")
        print(f"Unique Processed:      {unique_processed}")
        print(f"Duplicates Filtered:   {duplicates_count}")
        print(f"Out-of-Order Handled:  {out_of_order_count}")
        print(f"Anomalies Flagged:     {anomalies_count}")
        print(f"Execution Duration:    {round(exec_duration_ms, 2)} ms")
        print(f"Audit Chain Intact:    {ledger_valid}")
        print("=" * 60)
    else:
        replay_engine = ReplayEngine(strategy_name=args.strategy)
        _, result = replay_engine.replay_stream(events, strategy_name=args.strategy, shuffle=args.shuffle)

        print("=" * 60)
        print(f" AETHERIS TEMPORAL REPLAY SIMULATION: {fixture_path.name}")
        print("=" * 60)
        print(f"Total Ingested:        {result.total_events_ingested}")
        print(f"Unique Processed:      {result.unique_events_processed}")
        print(f"Duplicates Filtered:   {result.duplicates_filtered}")
        print(f"Out-of-Order Handled:  {result.out_of_order_reordered}")
        print(f"Anomalies Flagged:     {result.anomalies_detected}")
        print(f"Execution Duration:    {result.execution_time_ms} ms")
        print(f"Audit Chain Intact:    {result.audit_ledger_valid}")
        print("=" * 60)

    if args.verify:
        replay_engine = ReplayEngine(strategy_name=args.strategy)
        print("\nRunning 5-permutation random order invariance test...")
        is_inv, msg, details = replay_engine.verify_order_invariance(events, permutations=5)
        print(f"Result: {'[PASSED] ' + msg if is_inv else '[FAILED] ' + msg}")


def cmd_verify_audit(args):
    processor = get_default_processor()
    is_valid, msg = processor.verify_ledger()
    print("=" * 60)
    print(f" CRYPTOGRAPHIC AUDIT LEDGER INTEGRITY CHECK")
    print("=" * 60)
    print(f"Integrity Status:   {'VALID (Chain Intact)' if is_valid else 'TAMPERED / CORRUPTED'}")
    print(f"Total Blocks:       {processor.audit_ledger.get_record_count()}")
    print(f"Latest Block Hash:  {processor.audit_ledger.get_latest_hash()}")
    print(f"Verification Info:  {msg}")
    print("=" * 60)


def cmd_server(args):
    import uvicorn
    print(f"Starting Aetheris FastAPI Server on http://{args.host}:{args.port}")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)


def main():
    parser = argparse.ArgumentParser(description="Aetheris IoT Telemetry & Anomaly Resolution CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest a single telemetry event")
    p_ingest.add_argument("--sensor", required=True, help="Sensor ID (e.g. WQ-S101)")
    p_ingest.add_argument("--timestamp", help="ISO 8601 UTC timestamp")
    p_ingest.add_argument("--ph", type=float, help="pH reading")
    p_ingest.add_argument("--turbidity", type=float, help="Turbidity reading (NTU)")
    p_ingest.add_argument("--conductivity", type=float, help="Conductivity reading (uS/cm)")
    p_ingest.add_argument("--temperature", type=float, help="Temperature reading (C)")
    p_ingest.add_argument("--source", default="field", help="Source (field/lab/backup/calibration)")
    p_ingest.set_defaults(func=cmd_ingest)

    # Replay
    p_replay = subparsers.add_parser("replay", help="Replay a historical fixture dataset")
    p_replay.add_argument("--fixture", required=True, help="Fixture JSON filename (e.g. 02_out_of_order_stream.json)")
    p_replay.add_argument("--strategy", default="source_priority", help="Conflict strategy")
    p_replay.add_argument("--shuffle", action="store_true", help="Shuffle event stream before replay")
    p_replay.add_argument("--verify", action="store_true", help="Run multi-permutation order invariance verification")
    p_replay.add_argument("--persist", action="store_true", help="Ingest replay events into active audit ledger database")
    p_replay.set_defaults(func=cmd_replay)

    # Verify Audit
    p_audit = subparsers.add_parser("audit-verify", help="Verify cryptographic SHA-256 audit ledger")
    p_audit.set_defaults(func=cmd_verify_audit)

    # Server
    p_server = subparsers.add_parser("server", help="Start the FastAPI dashboard web server")
    p_server.add_argument("--host", default="127.0.0.1", help="Host address")
    p_server.add_argument("--port", type=int, default=8000, help="Port")
    p_server.add_argument("--reload", action="store_true", help="Auto reload")
    p_server.set_defaults(func=cmd_server)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
