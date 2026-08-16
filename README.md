# Aetheris
## A Real-Time IoT Telemetry & Anomaly Resolution Engine with Bi-Temporal State Reconstruction and Cryptographically Chained Audit Ledgers

> Simple dashboards display what sensors say. Aetheris verifies that what they say is authentic, resolves contradictions from competing sources, and mathematically proves the integrity of the historical record.

---

## Executive Summary

Monitoring river basins and agricultural runoff requires distributing low-power water quality sensors across wide geographic regions. In these deployments, unstable network connections introduce severe packet jitter, duplication packet storms, out-of-order telemetry arrival, and fragmented readings.

**Aetheris** is a high-performance, deterministic IoT telemetry processing and anomaly resolution engine built for distributed water quality monitoring grids measuring pH, turbidity, conductivity, and temperature. The system integrates:
1. **Idempotent Cryptographic Ingestion** to prevent state corruption during duplicate packet storms.
2. **Bi-Temporal State Reconstruction** using an in-memory chronological index to correctly sequence out-of-order events.
3. **Multi-Source Conflict & Identity Resolution** via strategy-pattern confidence fusion.
4. **Pure NumPy/Pandas Statistical ML** executing multivariate Mahalanobis distance outlier checks, CUSUM drift detection, and spatial topology corroboration.
5. **SHA-256 Cryptographic Audit Ledger** establishing an immutable, tamper-evident block chain.
6. **High-Aesthetic Floating Dashboard** with real-time gauges, bi-temporal scrubbers, and a temporal replay studio.

---

## The Problem

In environmental monitoring, water sensor telemetry suffers from high failure rates and network anomalies:
- **Packet storms and retries**: Low-quality cell nodes resend identical packets multiple times, causing state drift if ingestion is not idempotent.
- **Out-of-order arrival**: Packets queue up at remote routers and arrive hours late, making traditional time-series indexing report incorrect current readings.
- **Competing data sources**: A single physical sensor point may have conflicting readings from a manual field probe, a backup telemetry node, and a local laboratory analysis.
- **Hardware degradation vs. environmental anomalies**: Distinguishing between slow electrode drift (sensor decay) and localized chemical spikes is impossible without spatial topology correlation.
- **Lack of auditability**: Unscrupulous operators can alter database records to hide contamination events unless the entire history is cryptographically immutable.

Existing systems often rely on cloud-dependent databases or lack the analytical edge needed to process bi-temporal states. Aetheris resolves these issues with a local-first, high-throughput engine.

---

## Key Features & Contributions

- **Bi-Temporal State Indexing** – Tracks measurements across two axes: *Event Time* (when the event occurred) and *Processing Time* (when the packet was ingested).
- **Multi-Source Identity Resolution** – Configurable strategies (`source_priority`, `confidence_weighted`, and `latest`) to resolve competing data streams.
- **Lossless Partial Metric Fusion** – Sequentially merges fragmented packets (e.g. pH-only followed by turbidity-only) without losing historical metrics.
- **Statistical Machine Learning** – Local multivariate Mahalanobis distance calculation against Chi-Square thresholds to flag anomalies.
- **CUSUM Electrode Drift Detection** – Standardized residual tracking to detect slow sensor degradation.
- **Spatial topology corroboration** – Cross-checks anomalies across local catchment basins to differentiate isolated hardware faults from systemic pollution plumes.
- **SHA-256 Cryptographic Audit Chain** – Every state change is hashed and linked to the previous block, creating a verifiable audit trail.

---

## System Architecture

The Aetheris engine is structured as a decoupled four-layer pipeline to ensure separation of concerns, high throughput, and air-gapped security.

### 1. The Four-Layer Data Pipeline

<div align="center">

<table width="100%" style="text-align: center; border-collapse: collapse;">
  <thead>
    <tr style="border-bottom: 2px solid #ccc; background-color: rgba(255, 255, 255, 0.03);">
      <th style="padding: 12px;">Layer</th>
      <th style="padding: 12px;">Primary Components</th>
      <th style="padding: 12px;">Key Engine & Cloud Responsibilities</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>1. Ingestion</b></td>
      <td style="padding: 12px;">FastAPI Ingestion Endpoint, SHA-256 Deduplicator</td>
      <td style="padding: 12px;">Generates unique event fingerprints to filter identical duplicates; blocks redundant state updates.</td>
    </tr>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>2. State Resolution</b></td>
      <td style="padding: 12px;">Bi-Temporal Store, Resolution Strategy Matrix</td>
      <td style="padding: 12px;">Chronological index re-alignment via binary search; merges partial sensor fields; resolves source hierarchy conflicts.</td>
    </tr>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>3. Analytics & ML</b></td>
      <td style="padding: 12px;">NumPy/Pandas Outlier Module, Spatial Corroborator</td>
      <td style="padding: 12px;">Computes Mahalanobis distances, CUSUM drift scores, rate-of-change derivatives, and catchment plume correlations.</td>
    </tr>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>4. Audit & Replay</b></td>
      <td style="padding: 12px;">Cryptographic Ledger, Replay Studio CLI</td>
      <td style="padding: 12px;">Chains block hashes to enforce ledger immutability; supports deterministic historical replay under shuffled orders.</td>
    </tr>
  </tbody>
</table>

<p style="margin-top: 10px;"><b>Table 1. Decoupled architectural layers of the Aetheris engine.</b></p>

</div>

```
+-----------------------------------------------------------------------------------+
|                            IoT Telemetry Source Fleet                             |
|       (WQ-S101, WQ-S102... [Field / Backup / Lab] with Network Jitter & Drops)    |
+------------------------------------------+----------------------------------------+
                                           | POST /events (JSON)
                                           v
+-----------------------------------------------------------------------------------+
|                               Ingestion & Deduplication Layer                     |
|  - Idempotency Hash (SHA-256 fingerprint of sensor_id + event_time + payload)     |
|  - Deduplication Cache & Storage Filter (Zero state drift on duplicate ingestion) |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                        State Reconstruction & Identity Resolution                 |
|  - Bi-Temporal State Timeline per Sensor (Ordered by event_time)                  |
|  - Out-of-order Insertion & Historical State Recomputation                        |
|  - Partial Reading Merge Matrix (Selective field fusion without data loss)        |
|  - Multi-Source Conflict Resolution (Configurable: Confidence/Quality-Weighted,   |
|    Source Hierarchy [Lab > Field > Backup], Time-decayed confidence)              |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                   Deterministic Anomaly & Drift Engine (NumPy / Pandas)           |
|  - Temporal Rate-of-Change Monitor (ΔpH/Δt, Thermal Shock Trigger)                |
|  - Multivariate Covariance / Mahalanobis Distance Metric                          |
|  - CUSUM Cumulative Sum Drift Detector (Electrode degradation / slow drift)       |
|  - Multi-Sensor Spatial Corroborator (Systemic Plume vs Local Sensor Failure)     |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                      Immutable Audit Ledger & Replay Engine                       |
|  - Hash-Chained Audit Trail (SHA-256 prev_hash -> current_hash)                   |
|  - Full Explainability Trace (Weights, anomaly scores, conflict decisions)        |
|  - Temporal Replay Engine (Replays shuffled/chronological streams & verifies)    |
+------------------------------------------+----------------------------------------+
```

---

## Edge & Engine Intelligence: Mathematical Formulation

Aetheris replaces simple thresholding rules with statistical estimators computed using NumPy and Pandas.

### 1. Multivariate Mahalanobis Distance
To detect anomalous readings while accounting for the covariance between different metrics (e.g. how turbidity and conductivity rise together during rain events), the engine evaluates the Mahalanobis distance of incoming reading vectors $\mathbf{x}$:

$$D_M(\mathbf{x}) = \sqrt{(\mathbf{x} - \boldsymbol{\mu})^T \boldsymbol{\Sigma}^{-1} (\mathbf{x} - \boldsymbol{\mu})}$$

Where:
- $\mathbf{x} = [pH, turbidity, conductivity, temperature]^T$
- $\boldsymbol{\mu}$ is the historical baseline vector of means.
- $\boldsymbol{\Sigma}^{-1}$ is the inverse of the baseline covariance matrix.

An anomaly is flagged if $D_M(\mathbf{x})^2$ exceeds the Chi-Square critical value $\chi^2_{4, 0.995} \approx 14.86$.

### 2. CUSUM Cumulative Sum Drift Detection
Slow chemical electrode fouling is identified by cumulative residual tracking. If the sensor values shift slowly over days, the cumulative sum triggers an alarm before hard thresholds are crossed:

$$S^+_t = \max(0, S^+_{t-1} + z_t - k)$$
$$S^-_t = \max(0, S^-_{t-1} - z_t - k)$$

Where:
- $z_t$ is the standardized residual of the reading against the baseline mean.
- $k$ is the slack parameter (typically set to $0.5$ standard deviations).
- An alert is raised if $S^+_t$ or $S^-_t$ exceeds the decision interval $h = 4.0$.

### 3. Temporal Sequence Derivatives
Chemical spikes and thermal shocks are captured by monitoring continuous rate-of-change derivatives:

$$\frac{\Delta x}{\Delta t} = \frac{x_t - x_{t-1}}{t_t - t_{t-1}}$$

If $\left|\frac{\Delta \text{temp}}{\Delta t}\right| > 1.5^\circ\text{C/min}$ and matches a corresponding drop in pH, a **Thermal-pH Coupling Shock** anomaly is registered.

---

## Resilience & Bi-Temporal Ingestion

To maintain historical continuity under network jitter, Aetheris splits the handling of telemetry ingestion into two core steps:

1. **Idempotency Fingerprinting**
   Every telemetry event computes a deterministic SHA-256 fingerprint:
   $$\text{Fingerprint} = \text{SHA-256}(\text{sensorID} \mathbin{\Vert} \text{timestamp} \mathbin{\Vert} \text{source} \mathbin{\Vert} \text{readings})$$
   Duplicate transmissions from network retries are filtered at the edge of the API, preventing state drift.

2. **Ordered Chronological Re-indexing**
   When packets arrive delayed or out of order, the engine inserts them into the sensor’s timeline using binary search (`bisect_right`).
   - If the inserted packet is historical, Aetheris triggers a retrospective state reconstruction.
   - It recomputes the historical state sequence and verifies that the chronological chain of events remains coherent.

---

## Cryptographic Audit Ledger & Database Schema

Aetheris writes all telemetry changes to a write-through SQLite database and simultaneously appends them to a cryptographically linked ledger.

### 1. Ledger Block Schema
Every entry in the ledger is a block containing the telemetry details, conflict resolution traces, anomaly report, and a SHA-256 link to the previous block:

```json
{
  "index": 128,
  "timestamp": "2026-08-16T17:15:30.120Z",
  "sensor_id": "WQ-S101",
  "source": "field",
  "readings": {
    "ph": 7.42,
    "turbidity": 2.1,
    "conductivity": 420.0,
    "temperature": 21.5
  },
  "anomaly_report": {
    "is_anomaly": false,
    "mahalanobis_distance": 1.12,
    "cusum_drift": 0.02
  },
  "conflict_trace": {
    "strategy": "source_priority",
    "status": "applied_override"
  },
  "prev_hash": "a4f8e91823abf102c349ef88...bc72",
  "hash": "c89b7201fd5a2301c9a87dbe...124d"
}
```

### 2. Block Chaining Validation
The integrity of the ledger is verified by re-computing the SHA-256 hash of each block and checking if it matches the `prev_hash` of the subsequent block:

$$\text{Hash}_k = \text{SHA256}(\text{Hash}_{k-1} \,\|\, \text{JSON}(\text{Block}_k))$$

The `POST /verify-integrity` endpoint traverses this chain from the genesis block (`0` $\times 64$) to the head to detect any unauthorized data modifications.

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

## Anomaly Classification & Thresholds

Aetheris classifies sensor metrics into four distinct warning levels based on a combination of individual thresholds and multivariate Mahalanobis statistics.

<div align="center">

<table width="100%" style="text-align: center; border-collapse: collapse;">
  <thead>
    <tr style="border-bottom: 2px solid #ccc; background-color: rgba(255, 255, 255, 0.03);">
      <th style="padding: 12px;">Level</th>
      <th style="padding: 12px;">pH Range</th>
      <th style="padding: 12px;">Turbidity (NTU)</th>
      <th style="padding: 12px;">Conductivity (µS/cm)</th>
      <th style="padding: 12px;">Mahalanobis $D_M$</th>
      <th style="padding: 12px;">Classification Label</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>Level 0</b></td>
      <td style="padding: 12px;">6.5 — 8.5</td>
      <td style="padding: 12px;">&lt; 5.0</td>
      <td style="padding: 12px;">&lt; 500</td>
      <td style="padding: 12px;">&lt; 2.5</td>
      <td style="padding: 12px;">No anomaly detected</td>
    </tr>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>Level 1</b></td>
      <td style="padding: 12px;">6.0 — 6.5 / 8.5 — 9.0</td>
      <td style="padding: 12px;">5.0 — 15.0</td>
      <td style="padding: 12px;">500 — 1000</td>
      <td style="padding: 12px;">2.5 — 3.8</td>
      <td style="padding: 12px;">Minor statistical deviation</td>
    </tr>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>Level 2</b></td>
      <td style="padding: 12px;">5.0 — 6.0 / 9.0 — 10.0</td>
      <td style="padding: 12px;">15.0 — 50.0</td>
      <td style="padding: 12px;">1000 — 2000</td>
      <td style="padding: 12px;">3.8 — 5.0</td>
      <td style="padding: 12px;">Physical threshold breach</td>
    </tr>
    <tr style="border-bottom: 1px solid #ddd;">
      <td style="padding: 12px;"><b>Level 3</b></td>
      <td style="padding: 12px;">&lt; 5.0 / &gt; 10.0</td>
      <td style="padding: 12px;">&gt; 50.0</td>
      <td style="padding: 12px;">&gt; 2000</td>
      <td style="padding: 12px;">&gt; 5.0</td>
      <td style="padding: 12px;">Significant anomaly breach</td>
    </tr>
  </tbody>
</table>

<p style="margin-top: 10px;"><b>Table 2. Aetheris anomaly classification matrix.</b></p>

</div>

- **Level 0 (Safe Baseline)**: Standard water conditions.
- **Level 1 (Minor Deviation)**: Indicated by early CUSUM alerts or mild covariance drift. Retesting suggested.
- **Level 2 (Physical Breach)**: Crosses standard safe guidelines. Corroborated with neighbors to check for plumes.
- **Level 3 (Severe Breach)**: Rapid chemical shift or high-scoring Mahalanobis anomaly. Trigger immediate inspection.

---

## Setup & Execution

### 1. Installation
Ensure Python 3.10+ is installed. Clone the repository and install the standard dependencies:
```bash
pip install numpy pandas fastapi uvicorn pydantic
```

### 2. Run the Verification Tests
Execute the full test battery covering OOO streams, deduplication, conflict strategies, and ledger verification:
```bash
python -m unittest discover tests
```

### 3. Launch the Server
Start the local FastAPI instance:
```bash
python cli.py server --port 8000
```
Open `http://127.0.0.1:8000` to interact with the dashboard.

### 4. Deterministic Replay CLI
Replay any offline edge-case fixture file and verify the system's order invariance:
```bash
python cli.py replay --fixture 02_out_of_order_stream.json --verify
```

---

## Conclusion & Limitations

### Conclusion
Aetheris demonstrates how complex bi-temporal synchronization and multivariate anomaly resolution can be implemented in a lightweight, local-first engine. By decoupling ingestion, state resolution, statistical modeling, and cryptographically chained logging, it ensures that telemetry records remain verified and tamper-proof.

### Limitations
- **Local SQLite Write-Through**: Designed for small-to-medium catchment fleets. Extremely large industrial configurations (10,000+ events/sec) will require migrating the write-through layer to PostgreSQL or a specialized timeseries database.
- **Mahalanobis Matrix Initialization**: Requires an initial 100-event clean baseline history to construct the covariance matrix $\boldsymbol{\Sigma}$ before high-confidence multivariate outlier scoring becomes active.

---

For an in-depth breakdown of how this project satisfies the **Six Dimensions of Engineering Evidence**, see [`EVIDENCE.md`](./EVIDENCE.md).
