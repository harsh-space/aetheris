# Real-Time IoT Anomaly Resolution with Temporal Replay and Identity Resolution

Title:
Real-Time IoT Anomaly Resolution with Temporal Replay and Identity Resolution

Background:
You are tasked with building a system that processes telemetry data from a fleet of IoT water quality sensors deployed across a distributed network. The sensors transmit readings including pH, turbidity, conductivity, and temperature, but due to unreliable rural connectivity, data may arrive out of order, duplicated, or in fragmented bursts. Your system must reconstruct sensor states deterministically, detect anomalies, and resolve conflicts between conflicting or overlapping sensor readings using historical context and identity resolution logic. The system must be able to replay events to reproduce decisions and audit state changes. This builds upon your prior experience with IoT fault tolerance and anomaly detection, but introduces new complexity through identity ambiguity, delayed data, and state reconciliation.

Problem Statement:
Design and implement a real-time IoT data processing engine that ingests asynchronous telemetry from multiple sensors, reconstructs sensor states over time, detects anomalies using historical context, and resolves conflicting or ambiguous readings. The system must handle duplicate, out-of-order, and partial data reliably, and provide deterministic, auditable decisions. You must support replay of events to reproduce decisions and detect drift or state inconsistencies.

Scope:
The system must ingest sensor telemetry data, reconstruct sensor states, detect anomalies, and resolve conflicts between sensor readings. It must support event replay and maintain an audit trail of state changes. The system must be able to process data from multiple sensors, including those with overlapping or conflicting readings.

MVP Scope:
1. **Event Ingestion and Deduplication**: Accept JSON telemetry events via a local HTTP endpoint (`POST /events`). Each event contains: `sensor_id`, `timestamp`, `readings` (dictionary of `{'pH': float, 'turbidity': float, 'conductivity': float, 'temperature': float}`), and `source` (e.g., 'field', 'backup'). Events may be duplicated, out-of-order, or fragmented. Implement idempotent processing so that duplicate events do not alter the system state.  
2. **State Reconstruction and Identity Resolution**: Maintain a per-sensor state that evolves over time. If multiple readings for the same sensor arrive at different times, resolve them using a configurable strategy (e.g., latest, highest confidence, or weighted by data quality). Support merging of partial readings (e.g., only pH and temperature available).  
3. **Anomaly Detection with Temporal Reasoning**: Detect anomalies using a machine learning model trained on historical data. The model must consider temporal patterns (e.g., sudden pH drop after temperature rise) and sensor drift (e.g., gradual conductivity increase). The anomaly detection must be replayable and deterministic.  
4. **Audit and Replay**: Maintain an immutable audit log of all state changes and decisions. Support replaying events in any order to reproduce decisions.

Advanced/Bonus Scope:
- Add support for multi-sensor correlation (e.g., detecting if a pH anomaly in one sensor correlates with turbidity spikes in nearby sensors).  
- Implement a dashboard to visualize sensor states and anomalies.  
- Support partial event updates (e.g., adding new readings without overwriting existing ones).

Functional Requirements:
- The system must accept `POST /events` with JSON body:

- ```json
- {
- "sensor_id": "WQ-S123",
- "timestamp": "2024-06-15T10:30:00Z",
- "readings": {
- "pH": 6.8,
- "turbidity": 2.1,
- "conductivity": 450,
- "temperature": 22.5
- },
- "source": "field"
- }
- ```
- - The system must handle duplicate events (same `sensor_id`, `timestamp`, `readings`) without altering state.
- - The system must handle out-of-order events (e.g., `timestamp` earlier than current state) and update state accordingly.
- - The system must support partial readings (e.g., missing `conductivity`) and merge them with existing data.
- - The system must detect anomalies using a model trained on historical data. The model must consider temporal dependencies and drift.
- - The system must maintain an audit log of all state changes and decisions.
- - The system must support replaying events to reproduce decisions.

Non-Functional Requirements:
- The system must be deterministic: identical input and configuration → same decisions, final state, and audit output.  
- The system must be idempotent: duplicate events must not alter state.  
- The system must be replayable: events can be replayed in any order to reproduce decisions.  
- The system must maintain an immutable audit log of all state changes and decisions.  
- The system must process events in real-time with low latency.

Constraints:
- Use only the technologies in the candidate's stack: Python, C++, SQL, Firebase Firestore, MS Excel, NumPy, Pandas, Git.  
- Do not use external ML frameworks or APIs. Use NumPy/Pandas for ML.  
- Do not use distributed systems (e.g., Kafka, Kubernetes).  
- Do not use cloud services beyond Firebase Firestore.  
- Do not use ML/LLM for anomaly detection unless trained locally.

Deliverables:
1. Submission — Public GitHub repository URL (required).  
2. Repository contents — Backend/local API or CLI when the MVP exposes one; sample/fixture datasets covering the ≥5 interacting edge cases; audit/decision-trace output when decisions must be explainable; generated demo outputs as needed.  
3. Test Suite — Automated tests covering those fixtures/edge cases; include temporal boundary and midnight transition tests only when the problem is temporal.  
4. Documentation — README with clone → setup → run → test from the submitted GitHub URL, plus where fixtures and audit/demo outputs live.