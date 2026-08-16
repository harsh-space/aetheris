"""
FastAPI REST API Server for Real-Time IoT Anomaly Resolution with Temporal Replay.
"""

from __future__ import annotations
import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from engine.models import (
    AnomalyReport,
    AuditRecord,
    ConflictDecisionTrace,
    ReplayResult,
    SensorState,
    TelemetryEvent,
)
from engine.processor import TelemetryProcessor
from engine.replay_engine import ReplayEngine

app = FastAPI(
    title="Aetheris - Real-Time IoT Anomaly Resolution & Temporal Replay API",
    description="High-throughput deterministic IoT data processing engine with ML anomaly detection, temporal state reconstruction, and immutable audit trail.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global processor instance
processor = TelemetryProcessor(strategy_name="source_priority", db_path="iot_audit_ledger.db")
replay_engine = ReplayEngine(strategy_name="source_priority")


# Request/Response schemas
class IngestResponse(BaseModel):
    status: str
    is_duplicate: bool
    is_out_of_order: bool
    sensor_id: str
    event_timestamp: str
    resulting_state: SensorState
    anomaly_report: AnomalyReport
    conflict_trace: ConflictDecisionTrace
    audit_hash: Optional[str] = None


class StrategyConfigRequest(BaseModel):
    strategy: str = Field(..., description="Strategy: 'source_priority', 'confidence_weighted', or 'latest'")


class ReplayRequest(BaseModel):
    fixture_name: Optional[str] = Field(default=None, description="Preset fixture name (e.g. 01_duplicate_packet_storm.json)")
    events: Optional[List[TelemetryEvent]] = Field(default=None, description="Custom event list")
    strategy: Optional[str] = Field(default="source_priority")
    shuffle: bool = Field(default=False, description="Shuffle event stream before replay")
    verify_invariance: bool = Field(default=False, description="Run multi-permutation order invariance verification")
    persist: bool = Field(default=False, description="If True, ingests replay events into the main shared processor/audit ledger instead of an isolated sandbox.")


# API Endpoints
@app.post("/events", response_model=IngestResponse, tags=["Telemetry Ingestion"])
def ingest_event(event: TelemetryEvent):
    """
    Ingests an IoT telemetry event.
    Guarantees idempotent deduplication, partial metric merging,
    multi-source conflict resolution, and deterministic ML anomaly evaluation.
    """
    try:
        state, anomaly, trace, audit_rec, is_dup, is_ooo = processor.process_event(event)
        audit_hash = audit_rec.current_hash if audit_rec else None

        status_str = "DUPLICATE_SKIPPED" if is_dup else ("OUT_OF_ORDER_RECONSTRUCTED" if is_ooo else "PROCESSED")
        return IngestResponse(
            status=status_str,
            is_duplicate=is_dup,
            is_out_of_order=is_ooo,
            sensor_id=event.sensor_id,
            event_timestamp=event.timestamp,
            resulting_state=state,
            anomaly_report=anomaly,
            conflict_trace=trace,
            audit_hash=audit_hash
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sensors", response_model=Dict[str, SensorState], tags=["Fleet State"])
def get_all_sensors():
    """Returns the current resolved state for all active sensors."""
    return processor.get_all_states()


@app.get("/sensors/{sensor_id}", response_model=SensorState, tags=["Fleet State"])
def get_sensor(sensor_id: str):
    """Returns state for a specific sensor node."""
    state = processor.get_sensor_state(sensor_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Sensor '{sensor_id}' not found.")
    return state


@app.get("/sensors/{sensor_id}/timeline", tags=["Fleet State"])
def get_sensor_timeline(sensor_id: str):
    """Returns the full chronological event timeline for a sensor."""
    events = processor.state_store.get_timeline_events(sensor_id)
    return {
        "sensor_id": sensor_id,
        "total_events": len(events),
        "timeline": [e.model_dump() for e in events]
    }


@app.get("/sensors/{sensor_id}/historical", response_model=SensorState, tags=["Temporal Reconstruction"])
def get_historical_state(
    sensor_id: str,
    timestamp: str = Query(..., description="Target UTC ISO-8601 timestamp to reconstruct state at")
):
    """
    Bi-temporal state reconstruction: computes the deterministic state of the sensor
    as it existed at any historical timestamp.
    """
    state = processor.get_historical_state(sensor_id, timestamp)
    if not state:
        raise HTTPException(status_code=404, detail=f"No telemetry found for {sensor_id} at or before {timestamp}")
    return state


@app.post("/replay", tags=["Temporal Replay"])
def execute_replay(req: ReplayRequest):
    """
    Executes a temporal replay simulation using custom events or pre-built edge-case fixtures.
    """
    events: List[TelemetryEvent] = []

    if req.fixture_name:
        fixture_path = Path("fixtures") / req.fixture_name
        if not fixture_path.exists():
            # Try with .json extension
            fixture_path = Path("fixtures") / f"{req.fixture_name}.json"
        if not fixture_path.exists():
            raise HTTPException(status_code=404, detail=f"Fixture '{req.fixture_name}' not found.")
        
        with open(fixture_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            events = [TelemetryEvent(**item) for item in raw_data]
    elif req.events:
        events = req.events
    else:
        raise HTTPException(status_code=400, detail="Must provide either 'fixture_name' or 'events' list.")

    strat = req.strategy or processor.resolver.__class__.__name__

    if req.persist:
        # Persist mode: replay through the shared global processor so events
        # appear in the main audit ledger (same DB as live ingest).
        import random
        import time
        event_list = list(events)
        if req.shuffle:
            rng = random.Random(42)
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

        from engine.models import ReplayResult
        replay_res = ReplayResult(
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
    else:
        # Sandbox mode (default): isolated processor, no ledger writes
        _, replay_res = replay_engine.replay_stream(
            events=events,
            strategy_name=strat,
            shuffle=req.shuffle
        )

    invariance_report = None
    if req.verify_invariance:
        is_inv, msg, details = replay_engine.verify_order_invariance(events, permutations=5)
        invariance_report = {
            "order_invariant": is_inv,
            "message": msg,
            "details": details
        }

    return {
        "replay_summary": replay_res.model_dump(),
        "invariance_report": invariance_report,
        "persisted_to_ledger": req.persist
    }


@app.get("/fixtures", tags=["Temporal Replay"])
def list_fixtures():
    """Lists all available test fixtures in the repository."""
    fixtures_dir = Path("fixtures")
    if not fixtures_dir.exists():
        return {"fixtures": []}
    files = sorted([f.name for f in fixtures_dir.glob("*.json")])
    return {"fixtures": files}


@app.get("/audit", tags=["Audit Ledger"])
def get_audit_trail(
    sensor_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Returns cryptographic audit trail records."""
    records = processor.get_audit_trail(sensor_id=sensor_id, limit=limit)
    return {
        "total_records": processor.audit_ledger.get_record_count(),
        "latest_hash": processor.audit_ledger.get_latest_hash(),
        "records": [r.model_dump() for r in records]
    }


@app.post("/verify-integrity", tags=["Audit Ledger"])
def verify_audit_integrity():
    """
    Cryptographically verifies the entire SHA-256 hash chain from genesis block to head.
    Detects any payload tampering or data corruption.
    """
    is_valid, msg = processor.verify_ledger()
    return {
        "chain_intact": is_valid,
        "latest_block_hash": processor.audit_ledger.get_latest_hash(),
        "total_blocks": processor.audit_ledger.get_record_count(),
        "verification_message": msg
    }


@app.get("/analytics/correlations", tags=["Spatial Analytics"])
def get_spatial_correlations():
    """Returns spatial cluster health summaries and multi-sensor plume alerts."""
    all_states = processor.get_all_states()
    summary = processor.spatial_correlator.get_cluster_status_summary(all_states)
    return {
        "fleet_overview": {
            "total_sensors": len(all_states),
            "anomalous_sensors": sum(1 for s in all_states.values() if s.is_anomalous),
            "total_events_processed": processor.total_received,
            "duplicates_filtered": processor.total_duplicates,
            "out_of_order_reordered": processor.total_out_of_order,
        },
        "clusters": summary
    }


@app.post("/config/strategy", tags=["System Configuration"])
def configure_strategy(req: StrategyConfigRequest):
    """Dynamically updates the active conflict resolution strategy."""
    processor.set_strategy(req.strategy)
    return {
        "status": "SUCCESS",
        "active_strategy": processor.resolver.__class__.__name__,
        "message": f"Conflict resolution strategy set to '{req.strategy}' and existing states rebuilt."
    }


@app.post("/demo/load-master-dataset", tags=["Demo & Datasets"])
def load_master_dataset():
    """Loads the comprehensive multi-sensor master dataset covering all PRD edge cases."""
    fixture_path = Path("fixtures/00_master_fleet_simulation.json")
    if not fixture_path.exists():
        raise HTTPException(status_code=404, detail="Master dataset fixture not found.")
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        events_data = json.load(f)
    
    ingest_count = 0
    dup_count = 0
    ooo_count = 0
    anom_count = 0

    for item in events_data:
        ev = TelemetryEvent(**item)
        state, anom, trace, audit_rec, is_dup, is_ooo = processor.process_event(ev)
        ingest_count += 1
        if is_dup: dup_count += 1
        if is_ooo: ooo_count += 1
        if anom.is_anomaly: anom_count += 1

    return {
        "status": "SUCCESS",
        "message": f"Loaded {ingest_count} telemetry packets across 8 fleet sensor nodes.",
        "summary": {
            "total_ingested": ingest_count,
            "duplicates_filtered": dup_count,
            "out_of_order_reordered": ooo_count,
            "anomalies_detected": anom_count,
            "active_sensors": len(processor.get_all_states()),
            "audit_blocks": processor.audit_ledger.get_record_count()
        }
    }


@app.post("/demo/generate-stream-tick", tags=["Demo & Datasets"])
def generate_stream_tick():
    """Generates a dynamic real-time telemetry tick across a random active sensor node."""
    import random
    from datetime import datetime, timezone
    
    sensors = ["WQ-S101", "WQ-S102", "WQ-S103", "WQ-S123", "WQ-S201", "WQ-S202", "WQ-IND01"]
    sensor_id = random.choice(sensors)
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 10% chance of random anomaly
    if random.random() < 0.12:
        readings = {
            "pH": round(random.uniform(3.5, 5.2), 2),
            "turbidity": round(random.uniform(45.0, 110.0), 1),
            "conductivity": round(random.uniform(900.0, 1800.0), 1),
            "temperature": round(random.uniform(22.0, 29.0), 1)
        }
    else:
        readings = {
            "pH": round(random.uniform(7.15, 7.55), 2),
            "turbidity": round(random.uniform(1.8, 3.2), 2),
            "conductivity": round(random.uniform(410.0, 440.0), 1),
            "temperature": round(random.uniform(19.5, 21.8), 1)
        }

    ev = TelemetryEvent(
        sensor_id=sensor_id,
        timestamp=now_iso,
        readings=readings,
        source="field"
    )
    state, anom, trace, audit_rec, is_dup, is_ooo = processor.process_event(ev)
    return {
        "sensor_id": sensor_id,
        "timestamp": now_iso,
        "is_anomaly": anom.is_anomaly,
        "anomaly_type": anom.anomaly_type.value,
        "readings": state.readings
    }


@app.post("/reset", tags=["System Configuration"])
def reset_system():
    """Resets all engine state and audit records for fresh testing."""
    processor.reset()
    return {"status": "SUCCESS", "message": "Engine state and audit ledger cleared."}


@app.get("/export/csv", tags=["Data Export"])
def export_csv():
    """Exports complete historical telemetry and audit event logs to downloadable CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "audit_id",
        "action",
        "sensor_id",
        "event_timestamp",
        "received_timestamp",
        "pH",
        "turbidity",
        "conductivity",
        "temperature",
        "source",
        "is_anomaly",
        "anomaly_type",
        "anomaly_score",
        "conflict_strategy",
        "current_hash",
        "prev_hash"
    ])
    
    # Export full audit ledger history
    records = processor.audit_ledger.get_records(limit=100000)
    for r in records:
        ev = r.raw_event or {}
        readings = ev.get("readings", {})
        anom = r.anomaly_report or AnomalyReport()
        trace = r.conflict_trace or ConflictDecisionTrace(strategy_used="N/A")
        
        writer.writerow([
            r.audit_id,
            r.action,
            r.sensor_id,
            r.event_timestamp,
            r.received_timestamp,
            readings.get("pH", ""),
            readings.get("turbidity", ""),
            readings.get("conductivity", ""),
            readings.get("temperature", ""),
            ev.get("source", "field"),
            anom.is_anomaly,
            anom.anomaly_type.value if hasattr(anom.anomaly_type, "value") else str(anom.anomaly_type),
            anom.anomaly_score,
            trace.strategy_used,
            r.current_hash,
            r.prev_hash
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aetheris_telemetry_audit_history.csv"}
    )


# Serve Static Frontend Dashboard
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse, tags=["Dashboard UI"])
def get_dashboard():
    index_file = static_dir / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>IoT Telemetry Engine Running. Dashboard static files loading...</h1>"
