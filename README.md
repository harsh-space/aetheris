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
| `01_duplicate_packet_storm.json` | 5x identical packet storm with network retries | Idempotency; zero state drift; version incremented only on unique events |
| `02_out_of_order_stream.json` | Jittered and delayed telemetry arrival | Binary search re-indexing; bi-temporal state reconstruction |
| `03_conflicting_sources.json` | Simultaneous competing readings (`field` vs `lab` vs `backup`) | Source priority overrides & confidence-weighted fusion |
| `04_partial_reading_merges.json` | Fragmented packets (pH only $\to$ turbidity only $\to$ conductivity) | Lossless partial metric fusion |
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
| `POST` | `/config/strategy` | Switch active conflict resolver strategy |
| `POST` | `/reset` | Clear all telemetry caches and audit records |
| `GET` | `/export/csv` | Download fleet states as CSV |

---

## Engineering Evidence Documentation
For an in-depth breakdown of how this project satisfies the **Six Dimensions of Engineering Evidence**, see [`EVIDENCE.md`](./EVIDENCE.md).
