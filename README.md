# Aetheris: Real-Time IoT Telemetry & Anomaly Resolution Engine

**Aetheris** is a high-performance, deterministic IoT telemetry processing and anomaly resolution engine built for distributed water quality monitoring grids (`pH`, `turbidity`, `conductivity`, `temperature`).

It solves the challenges of unreliable rural network connectivity (packet jitter, packet storms, severe out-of-order arrival, and partial sensor telemetry) using:
1. **Idempotent Cryptographic Ingestion**: Zero state drift during duplicate packet storms.
2. **Bi-Temporal State Reconstruction**: Accurate event-time vs. processing-time historical reconstruction.
3. **Multi-Source Conflict & Identity Resolution**: Configurable hierarchical and Bayesian-weighted conflict strategies (`lab` > `calibration` > `field` > `backup`).
4. **Pure NumPy/Pandas Statistical ML**: Multivariate Mahalanobis Distance outlier detection, temporal sequence derivatives, thermal shock triggers, and CUSUM cumulative sum electrode drift detection.
5. **Multi-Sensor Spatial Corroboration**: Distinguishes isolated sensor hardware failure from systemic river-basin contamination plumes.
6. **Immutable SHA-256 Chained Audit Ledger**: Cryptographically linked tamper-evident audit trail with automated chain verification and deterministic temporal replay.
7. **Interactive Real-Time Dashboard**: High-aesthetic dark-mode UI with live telemetry gauges, historical timeline scrubber, replay studio, and audit verifier.

---

## Quick Start Guide

### 1. Requirements
- Python 3.10+ (Tested on Python 3.13)
- `numpy`, `pandas`, `fastapi`, `uvicorn`, `pydantic` (all free, standard open-source tools)

### 2. Run Automated Test Suite
Run the full test battery covering all 6 interacting edge cases:
```bash
python -m unittest discover tests
```
*Output: 22/22 tests passing in < 0.4 seconds.*

### 3. Launch Web API & Real-Time Dashboard
Start the local FastAPI server:
```bash
python cli.py server --port 8000
```
Open your browser at: **`http://127.0.0.1:8000`** (or open Swagger UI at **`http://127.0.0.1:8000/docs`**).

---

## Command-Line Interface (CLI)

### Ingest Telemetry Event
```bash
python cli.py ingest --sensor WQ-S101 --ph 7.3 --turbidity 2.1 --conductivity 420 --temperature 21.5 --source field
```

### Replay Edge-Case Fixture Dataset & Verify Order Invariance
```bash
python cli.py replay --fixture 02_out_of_order_stream.json --verify
```

### Cryptographic Audit Ledger Verification
```bash
python cli.py audit-verify
```

### Performance Latency Benchmark (10,000 Events)
```bash
python scripts/benchmark.py
```

---

## Edge-Case Fixtures (`fixtures/`)

| Fixture File | Scenario Covered | Key Verification |
| :--- | :--- | :--- |
| `00_master_fleet_simulation.json` | **All 6 PRD scenarios combined** across 8 sensors, 3 catchment basins | Full end-to-end integration test: deduplication, OOO, conflicts, partial merges, drift, plume, midnight UTC |
| `01_duplicate_packet_storm.json` | 5x identical packet storm with network retries | Idempotency; zero state drift; version incremented only on unique events |
| `02_out_of_order_stream.json` | Jittered and delayed telemetry arrival | Binary search re-indexing; bi-temporal state reconstruction |
| `03_conflicting_sources.json` | Simultaneous competing readings (`field` vs `lab` vs `backup`) | Source priority overrides & confidence-weighted fusion |
| `04_partial_reading_merges.json` | Fragmented packets (pH only → turbidity only → conductivity) | Lossless partial metric fusion |
| `05_drift_vs_spike_correlation.json` | CUSUM slow electrode drift vs dual-sensor chemical spike | Spatial topology corroboration & systemic plume alerts |
| `06_midnight_boundary_transition.json` | Telemetry straddling UTC midnight ($23:59:45\text{Z} \to 00:00:15\text{Z}$) | Temporal sequence continuity across date boundaries |

---

## REST API Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/events` | Ingest single telemetry event with deduplication and ML anomaly check |
| `GET` | `/sensors` | Get current fleet states for all active sensors |
| `GET` | `/sensors/{id}` | Get state for a specific sensor |
| `GET` | `/sensors/{id}/timeline` | Get chronological event history for a sensor |
| `GET` | `/sensors/{id}/historical?timestamp=...` | Point-in-time historical state reconstruction |
| `POST` | `/replay` | Run temporal replay on fixtures or custom event streams |
| `GET` | `/audit` | Query cryptographic audit trail records |
| `POST` | `/verify-integrity` | Verify full SHA-256 hash chain from genesis block |
| `GET` | `/analytics/correlations` | Get multi-sensor spatial cluster health & plume alerts |
| `POST` | `/config/strategy` | Switch active conflict resolver strategy (`source_priority` / `confidence_weighted` / `latest`) |
| `POST` | `/reset` | Clear all telemetry caches and audit records |
| `GET` | `/export/csv` | Download **full historical telemetry audit log** (all events, timestamps, anomaly scores, SHA-256 hashes) as CSV |
| `POST` | `/demo/load-master-dataset` | Load the master 8-sensor fleet fixture in one click for live demonstration |
| `POST` | `/demo/generate-stream-tick` | Generate a single synthetic live telemetry tick for the fleet simulator |

---

## Dashboard Features

The interactive dashboard at `http://127.0.0.1:8000` includes:

- **Fleet Live Monitor** — real-time sensor cards with HTML5 canvas sparklines, live metric gauges, and cluster filter pills
- **Bi-Temporal Scrubber** — point-in-time historical state reconstruction slider per sensor node
- **Temporal Replay Studio** — run any edge-case fixture with automated 5-permutation deterministic invariance verification
- **Live Packet Injector** — POST arbitrary telemetry JSON with quick-preset templates (thermal shock, acid spill, lab override, etc.)
- **Spatial Corroboration Map** — catchment basin cluster cards distinguishing sensor defects from contamination plumes
- **Cryptographic Audit Ledger** — full SHA-256 blockchain table with one-click chain integrity verification
- **Live Simulator** — auto-generates synthetic telemetry ticks every 1.2 seconds across the fleet
- **Master Dataset Loader** — populates all 8 sensors with comprehensive PRD test data in one click

---

## Engineering Evidence Documentation
For an in-depth breakdown of how this project satisfies the **Six Dimensions of Engineering Evidence**, see [`EVIDENCE.md`](./EVIDENCE.md).
