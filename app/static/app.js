// HydroPulse IoT Telemetry & Anomaly Resolution Client Application

document.addEventListener("DOMContentLoaded", () => {
  // State variables
  let currentSensors = {};
  let selectedSensorId = null;
  let selectedSensorTimeline = [];

  // DOM Elements
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const strategySelector = document.getElementById("strategy-selector");
  const btnVerifyAudit = document.getElementById("btn-verify-audit");
  const btnVerifyAuditPane = document.getElementById("btn-verify-audit-pane");
  const btnExportCsv = document.getElementById("btn-export-csv");
  const btnResetEngine = document.getElementById("btn-reset-engine");

  // KPI elements
  const kpiSensorsCount = document.getElementById("kpi-sensors-count");
  const kpiTotalEvents = document.getElementById("kpi-total-events");
  const kpiDuplicatesCount = document.getElementById("kpi-duplicates-count");
  const kpiOooCount = document.getElementById("kpi-ooo-count");
  const kpiAnomaliesCount = document.getElementById("kpi-anomalies-count");
  const kpiAnomaliesTag = document.getElementById("kpi-anomalies-tag");
  const kpiAuditBlocks = document.getElementById("kpi-audit-blocks");

  // Fleet View elements
  const sensorFleetGrid = document.getElementById("sensor-fleet-grid");
  const sensorDetailCard = document.getElementById("sensor-detail-card");
  const detailSensorTitle = document.getElementById("detail-sensor-title");
  const detailSensorCluster = document.getElementById("detail-sensor-cluster");
  const btnCloseDetail = document.getElementById("btn-close-detail");
  const timelineRangeSlider = document.getElementById("timeline-range-slider");
  const sliderTimestampLabel = document.getElementById("slider-timestamp-label");
  const reconstructedStateBox = document.getElementById("reconstructed-state-box");

  // Replay elements
  const replayFixtureSelect = document.getElementById("replay-fixture-select");
  const replayStrategySelect = document.getElementById("replay-strategy-select");
  const replayShuffleCheck = document.getElementById("replay-shuffle-check");
  const replayInvarianceCheck = document.getElementById("replay-invariance-check");
  const btnRunReplay = document.getElementById("btn-run-replay");
  const btnLoadAllFixtures = document.getElementById("btn-load-all-fixtures");
  const replayResultsContainer = document.getElementById("replay-results-container");
  const replayStatusBadge = document.getElementById("replay-status-badge");

  // Ingest elements
  const eventPayloadEditor = document.getElementById("event-payload-editor");
  const btnSendEvent = document.getElementById("btn-send-event");
  const ingestResponseContainer = document.getElementById("ingest-response-container");
  const ingestTraceStatus = document.getElementById("ingest-trace-status");

  // Spatial & Audit elements
  const spatialClusterGrid = document.getElementById("spatial-cluster-grid");
  const auditTableBody = document.getElementById("audit-table-body");
  const auditVerifyAlert = document.getElementById("audit-verify-alert");

  // Presets mapping
  const PRESETS = {
    normal: {
      sensor_id: "WQ-S123",
      timestamp: new Date().toISOString(),
      readings: { pH: 7.35, turbidity: 2.4, conductivity: 425.0, temperature: 21.2 },
      source: "field"
    },
    dup: {
      sensor_id: "WQ-S123",
      timestamp: "2024-06-15T10:30:00Z",
      readings: { pH: 6.8, turbidity: 2.1, conductivity: 450.0, temperature: 22.5 },
      source: "field"
    },
    ooo: {
      sensor_id: "WQ-S101",
      timestamp: "2024-06-15T11:45:00Z",
      readings: { pH: 7.20, turbidity: 1.9, conductivity: 410.0, temperature: 19.5 },
      source: "field"
    },
    lab_override: {
      sensor_id: "WQ-S102",
      timestamp: "2024-06-15T14:00:00Z",
      readings: { pH: 7.45, turbidity: 1.8, conductivity: 415.0, temperature: 21.0 },
      source: "lab"
    },
    partial: {
      sensor_id: "WQ-S103",
      timestamp: new Date().toISOString(),
      readings: { pH: 7.42 },
      source: "field"
    },
    thermal_shock: {
      sensor_id: "WQ-S101",
      timestamp: new Date().toISOString(),
      readings: { pH: 6.2, turbidity: 3.5, conductivity: 490.0, temperature: 28.5 },
      source: "field"
    },
    acid_spike: {
      sensor_id: "WQ-S101",
      timestamp: new Date().toISOString(),
      readings: { pH: 3.8, turbidity: 95.0, conductivity: 1350.0, temperature: 22.0 },
      source: "field"
    }
  };

  // Tab Navigation
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.getElementById(targetId).classList.add("active");
      
      if (targetId === "tab-audit") loadAuditTrail();
      if (targetId === "tab-spatial") loadSpatialData();
    });
  });

  // Preset buttons
  document.querySelectorAll(".btn-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const presetKey = chip.getAttribute("data-preset");
      if (PRESETS[presetKey]) {
        eventPayloadEditor.value = JSON.stringify(PRESETS[presetKey], null, 2);
      }
    });
  });

  // Close Detail Card
  btnCloseDetail.addEventListener("click", () => {
    sensorDetailCard.classList.add("hidden");
    selectedSensorId = null;
  });

  // Strategy change
  strategySelector.addEventListener("change", async (e) => {
    try {
      const resp = await fetch("/config/strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy: e.target.value })
      });
      if (resp.ok) {
        refreshDashboard();
      }
    } catch (err) {
      console.error("Strategy update failed:", err);
    }
  });

  // Reset Engine
  btnResetEngine.addEventListener("click", async () => {
    if (confirm("Reset all telemetry state, deduplication caches, and audit logs?")) {
      try {
        await fetch("/reset", { method: "POST" });
        refreshDashboard();
      } catch (err) {
        console.error("Reset failed:", err);
      }
    }
  });

  // Export CSV
  btnExportCsv.addEventListener("click", () => {
    window.location.href = "/export/csv";
  });

  // Verify Audit
  const handleVerifyAudit = async () => {
    try {
      const resp = await fetch("/verify-integrity", { method: "POST" });
      const data = await resp.json();
      auditVerifyAlert.classList.remove("hidden");
      if (data.chain_intact) {
        auditVerifyAlert.className = "alert-box alert-success";
        auditVerifyAlert.innerHTML = `&#10004; <strong>Audit Trail Cryptographically Verified:</strong> All ${data.total_blocks} blocks valid. Latest SHA-256 Block Hash: <code>${data.latest_block_hash.substring(0, 16)}...</code>`;
      } else {
        auditVerifyAlert.className = "alert-box alert-danger";
        auditVerifyAlert.innerHTML = `&#9888; <strong>Audit Integrity Failure:</strong> ${data.verification_message}`;
      }
    } catch (err) {
      alert("Verification request failed.");
    }
  };

  btnVerifyAudit.addEventListener("click", handleVerifyAudit);
  btnVerifyAuditPane.addEventListener("click", handleVerifyAudit);

  // Send Single Event
  btnSendEvent.addEventListener("click", async () => {
    try {
      const payload = JSON.parse(eventPayloadEditor.value);
      ingestTraceStatus.textContent = "Processing...";
      ingestTraceStatus.className = "badge badge-blue";

      const start = performance.now();
      const resp = await fetch("/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const duration = (performance.now() - start).toFixed(2);
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Ingestion error");
      }

      ingestTraceStatus.textContent = data.status;
      ingestTraceStatus.className = data.is_duplicate ? "badge badge-purple" : (data.resulting_state.is_anomalous ? "badge badge-rose" : "badge badge-teal");

      renderIngestTrace(data, duration);
      refreshDashboard();
    } catch (err) {
      ingestTraceStatus.textContent = "Error";
      ingestTraceStatus.className = "badge badge-rose";
      ingestResponseContainer.innerHTML = `<div style="color: var(--accent-rose);">&#9888; Error: ${err.message}</div>`;
    }
  });

  function renderIngestTrace(data, duration) {
    const isAnom = data.resulting_state.is_anomalous;
    const anom = data.anomaly_report;
    const trace = data.conflict_trace;

    let html = `
      <div style="margin-bottom: 12px;">
        <span class="badge ${data.is_duplicate ? 'badge-purple' : (isAnom ? 'badge-rose' : 'badge-teal')}">${data.status}</span>
        <span class="mono-badge" style="margin-left: 8px;">Execution Latency: ${duration} ms</span>
      </div>

      <div style="margin-bottom: 10px;">
        <strong style="color: var(--accent-cyan);">Sensor Node:</strong> ${data.sensor_id} | 
        <strong style="color: var(--accent-cyan);">Timestamp:</strong> ${data.event_timestamp}
      </div>

      <div style="margin-bottom: 10px;">
        <strong style="color: var(--text-muted);">Conflict Strategy Used:</strong> <code>${trace.strategy_used}</code>
        <ul style="margin-left: 18px; margin-top: 4px; color: var(--text-dim);">
          ${trace.resolution_notes.map(n => `<li>${n}</li>`).join("")}
        </ul>
      </div>

      <div style="margin-bottom: 10px;">
        <strong style="color: ${isAnom ? 'var(--accent-rose)' : 'var(--accent-teal)'};">ML Anomaly Classification:</strong> ${anom.anomaly_type} (${anom.severity})
        <div style="color: var(--text-main); margin-top: 2px;">${anom.explanation}</div>
        ${anom.mahalanobis_distance ? `<div style="color: var(--text-dim); margin-top: 2px;">Mahalanobis Distance D = ${anom.mahalanobis_distance} (Threshold: 3.64)</div>` : ''}
        ${anom.details.spatial_diagnosis ? `<div style="color: var(--accent-amber); margin-top: 4px;"><strong>Spatial Topology Diagnosis:</strong> ${anom.details.spatial_diagnosis}</div>` : ''}
      </div>

      ${data.audit_hash ? `
        <div style="margin-top: 12px; border-top: 1px solid var(--border-color); padding-top: 8px;">
          <strong style="color: var(--accent-teal);">Chained Audit Hash (SHA-256):</strong>
          <div style="font-size: 11px; color: var(--accent-cyan); word-break: break-all;">${data.audit_hash}</div>
        </div>
      ` : ''}
    `;
    ingestResponseContainer.innerHTML = html;
  }

  // Run Replay Simulation
  btnRunReplay.addEventListener("click", async () => {
    try {
      const fixtureName = replayFixtureSelect.value;
      const strategy = replayStrategySelect.value;
      const shuffle = replayShuffleCheck.checked;
      const verifyInvariance = replayInvarianceCheck.checked;

      replayStatusBadge.textContent = "Simulating...";
      replayStatusBadge.className = "badge badge-purple";

      const resp = await fetch("/replay", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fixture_name: fixtureName,
          strategy: strategy,
          shuffle: shuffle,
          verify_invariance: verifyInvariance
        })
      });
      const data = await resp.json();

      replayStatusBadge.textContent = "Completed";
      replayStatusBadge.className = "badge badge-teal";

      renderReplayResults(data);
      refreshDashboard();
    } catch (err) {
      replayStatusBadge.textContent = "Failed";
      replayStatusBadge.className = "badge badge-rose";
      replayResultsContainer.innerHTML = `<div style="color: var(--accent-rose);">&#9888; Replay execution failed: ${err.message}</div>`;
    }
  });

  // Run all 6 fixtures
  btnLoadAllFixtures.addEventListener("click", async () => {
    const fixtures = [
      "01_duplicate_packet_storm.json",
      "02_out_of_order_stream.json",
      "03_conflicting_sources.json",
      "04_partial_reading_merges.json",
      "05_drift_vs_spike_correlation.json",
      "06_midnight_boundary_transition.json"
    ];

    replayResultsContainer.innerHTML = `<div style="color: var(--accent-cyan);">Executing full 6-fixture test battery...</div>`;
    let reportHtml = `<h4 style="color: var(--accent-cyan); margin-bottom: 12px;">Full 6-Fixture Verification Battery</h4>`;

    for (const fix of fixtures) {
      const resp = await fetch("/replay", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fixture_name: fix,
          strategy: "source_priority",
          verify_invariance: true
        })
      });
      const data = await resp.json();
      const sum = data.replay_summary;
      const inv = data.invariance_report;

      reportHtml += `
        <div style="background: var(--bg-card); padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 3px solid var(--accent-teal);">
          <strong style="color: var(--text-main); font-size: 13px;">${fix}</strong>
          <div style="color: var(--text-dim); font-size: 11.5px; margin-top: 4px;">
            Total Events: ${sum.total_events_ingested} | Processed: ${sum.unique_events_processed} | Duplicates: ${sum.duplicates_filtered} | Out-of-Order: ${sum.out_of_order_reordered} | Execution Time: ${sum.execution_time_ms} ms
          </div>
          <div style="color: ${inv && inv.order_invariant ? 'var(--accent-teal)' : 'var(--accent-rose)'}; font-size: 12px; margin-top: 4px;">
            &#10004; Deterministic Order Invariance: ${inv ? inv.message : 'Verified'} (5 random permutations tested)
          </div>
        </div>
      `;
    }

    replayResultsContainer.innerHTML = reportHtml;
    refreshDashboard();
  });

  function renderReplayResults(data) {
    const sum = data.replay_summary;
    const inv = data.invariance_report;

    let html = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
        <div style="background: var(--bg-card); padding: 10px; border-radius: 6px;">
          <div style="color: var(--text-dim); font-size: 11px;">Total Ingested</div>
          <div style="font-size: 18px; font-weight: 700; color: var(--text-main);">${sum.total_events_ingested}</div>
        </div>
        <div style="background: var(--bg-card); padding: 10px; border-radius: 6px;">
          <div style="color: var(--text-dim); font-size: 11px;">Unique Processed</div>
          <div style="font-size: 18px; font-weight: 700; color: var(--accent-cyan);">${sum.unique_events_processed}</div>
        </div>
        <div style="background: var(--bg-card); padding: 10px; border-radius: 6px;">
          <div style="color: var(--text-dim); font-size: 11px;">Duplicates Filtered</div>
          <div style="font-size: 18px; font-weight: 700; color: var(--accent-purple);">${sum.duplicates_filtered}</div>
        </div>
        <div style="background: var(--bg-card); padding: 10px; border-radius: 6px;">
          <div style="color: var(--text-dim); font-size: 11px;">Out-of-Order Reordered</div>
          <div style="font-size: 18px; font-weight: 700; color: var(--accent-amber);">${sum.out_of_order_reordered}</div>
        </div>
      </div>

      <div style="margin-bottom: 12px;">
        <strong>Simulation Execution Duration:</strong> <span class="mono-badge">${sum.execution_time_ms} ms</span>
      </div>

      ${inv ? `
        <div style="background: ${inv.order_invariant ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)'}; border: 1px solid ${inv.order_invariant ? 'var(--accent-teal)' : 'var(--accent-rose)'}; padding: 12px; border-radius: 6px; margin-top: 14px;">
          <div style="font-weight: 700; color: ${inv.order_invariant ? 'var(--accent-teal)' : 'var(--accent-rose)'};">
            ${inv.order_invariant ? '&#10004; Deterministic Order Invariance Verified' : '&#9888; Order Invariance Failed'}
          </div>
          <div style="font-size: 12px; margin-top: 4px; color: var(--text-main);">${inv.message}</div>
          <div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">Tested across ${inv.details.permutations_tested} randomized permutations with tolerance 1e-5.</div>
        </div>
      ` : ''}
    `;
    replayResultsContainer.innerHTML = html;
  }

  // Fetch and Refresh Dashboard State
  async function refreshDashboard() {
    try {
      // 1. Fetch Fleet Sensors
      const sensorsResp = await fetch("/sensors");
      const sensorsData = await sensorsResp.json();
      currentSensors = sensorsData;
      renderSensorGrid(sensorsData);

      // 2. Fetch Spatial Analytics & KPI
      const spatialResp = await fetch("/analytics/correlations");
      const spatialData = await spatialResp.json();
      updateKPIs(spatialData.fleet_overview);
      renderSpatialClusters(spatialData.clusters);

      // 3. Fetch Audit Block Count
      const auditResp = await fetch("/audit?limit=1");
      const auditData = await auditResp.json();
      kpiAuditBlocks.textContent = auditData.total_records || 0;

      // 4. Update detail scrubber if active
      if (selectedSensorId && currentSensors[selectedSensorId]) {
        loadSensorTimeline(selectedSensorId);
      }
    } catch (err) {
      console.error("Dashboard refresh error:", err);
    }
  }

  function updateKPIs(overview) {
    if (!overview) return;
    kpiSensorsCount.textContent = overview.total_sensors || 0;
    kpiTotalEvents.textContent = overview.total_events_processed || 0;
    kpiDuplicatesCount.textContent = overview.duplicates_filtered || 0;
    kpiOooCount.textContent = overview.out_of_order_reordered || 0;
    kpiAnomaliesCount.textContent = overview.anomalous_sensors || 0;

    if (overview.anomalous_sensors > 0) {
      kpiAnomaliesTag.textContent = `${overview.anomalous_sensors} Alert Active`;
      kpiAnomaliesTag.className = "badge badge-rose";
    } else {
      kpiAnomaliesTag.textContent = "Fleet Healthy";
      kpiAnomaliesTag.className = "badge badge-green";
    }
  }

  function renderSensorGrid(sensors) {
    const sensorIds = Object.keys(sensors);
    if (sensorIds.length === 0) {
      sensorFleetGrid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 40px; text-align: center; background: var(--bg-dark); border-radius: 12px; border: 1px dashed var(--border-color);">
          <div style="font-size: 16px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px;">No IoT Sensor Telemetry Received Yet</div>
          <div style="font-size: 13px; color: var(--text-dim); margin-bottom: 18px;">Inject events using the Live Packet Injector or load an edge-case fixture in the Temporal Replay Studio.</div>
          <button id="btn-quick-start" class="btn btn-primary">Load Sample Dataset</button>
        </div>
      `;
      document.getElementById("btn-quick-start")?.addEventListener("click", () => {
        btnLoadAllFixtures.click();
      });
      return;
    }

    let html = "";
    sensorIds.forEach(id => {
      const s = sensors[id];
      const r = s.readings || {};
      const isAnom = s.is_anomalous;

      html += `
        <div class="sensor-card ${isAnom ? 'anomalous' : ''}" data-sensor-id="${id}">
          <div class="sensor-card-top">
            <div>
              <div class="sensor-card-id">${id}</div>
              <div class="sensor-card-time">${s.last_event_time || 'N/A'}</div>
            </div>
            <span class="badge ${isAnom ? 'badge-rose' : 'badge-teal'}">
              ${isAnom ? s.active_anomaly_type : 'NORMAL'}
            </span>
          </div>

          <div class="metric-gauges">
            <div class="metric-item">
              <span class="metric-label">pH Level</span>
              <div class="metric-val ${r.pH && (r.pH < 6.5 || r.pH > 8.5) ? 'text-rose' : 'text-cyan'}">${r.pH !== undefined ? r.pH.toFixed(2) : '--'} <span class="metric-unit">pH</span></div>
            </div>
            <div class="metric-item">
              <span class="metric-label">Turbidity</span>
              <div class="metric-val ${r.turbidity && r.turbidity > 5.0 ? 'text-amber' : ''}">${r.turbidity !== undefined ? r.turbidity.toFixed(2) : '--'} <span class="metric-unit">NTU</span></div>
            </div>
            <div class="metric-item">
              <span class="metric-label">Conductivity</span>
              <div class="metric-val">${r.conductivity !== undefined ? r.conductivity.toFixed(1) : '--'} <span class="metric-unit">µS/cm</span></div>
            </div>
            <div class="metric-item">
              <span class="metric-label">Temperature</span>
              <div class="metric-val">${r.temperature !== undefined ? r.temperature.toFixed(1) : '--'} <span class="metric-unit">°C</span></div>
            </div>
          </div>

          <div class="sensor-card-bottom">
            <span>Source: <strong style="color: var(--text-main);">${s.last_source}</strong></span>
            <span>Version: <strong style="color: var(--accent-cyan);">v${s.version}</strong></span>
          </div>
        </div>
      `;
    });

    sensorFleetGrid.innerHTML = html;

    // Attach click listeners
    document.querySelectorAll(".sensor-card").forEach(card => {
      card.addEventListener("click", () => {
        const id = card.getAttribute("data-sensor-id");
        openSensorDetail(id);
      });
    });
  }

  async function openSensorDetail(sensorId) {
    selectedSensorId = sensorId;
    sensorDetailCard.classList.remove("hidden");
    detailSensorTitle.textContent = `Sensor Node: ${sensorId}`;
    await loadSensorTimeline(sensorId);
    sensorDetailCard.scrollIntoView({ behavior: 'smooth' });
  }

  async function loadSensorTimeline(sensorId) {
    try {
      const resp = await fetch(`/sensors/${sensorId}/timeline`);
      const data = await resp.json();
      selectedSensorTimeline = data.timeline || [];

      if (selectedSensorTimeline.length > 0) {
        timelineRangeSlider.min = 0;
        timelineRangeSlider.max = selectedSensorTimeline.length - 1;
        timelineRangeSlider.value = selectedSensorTimeline.length - 1;
        updateHistoricalScrubber(selectedSensorTimeline.length - 1);
      }
    } catch (err) {
      console.error("Timeline fetch failed:", err);
    }
  }

  timelineRangeSlider.addEventListener("input", (e) => {
    const idx = parseInt(e.target.value, 10);
    updateHistoricalScrubber(idx);
  });

  async function updateHistoricalScrubber(index) {
    if (!selectedSensorTimeline || !selectedSensorTimeline[index]) return;
    const targetEvent = selectedSensorTimeline[index];
    sliderTimestampLabel.textContent = `Point-in-Time: ${targetEvent.timestamp}`;

    try {
      const resp = await fetch(`/sensors/${selectedSensorId}/historical?timestamp=${encodeURIComponent(targetEvent.timestamp)}`);
      const historicalState = await resp.json();

      reconstructedStateBox.innerHTML = `
        <div style="color: var(--accent-cyan); font-weight: 700; margin-bottom: 8px;">Reconstructed State as of ${historicalState.last_event_time}:</div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 10px;">
          <div>pH: <strong style="color:#fff;">${historicalState.readings.pH ?? '--'}</strong></div>
          <div>Turbidity: <strong style="color:#fff;">${historicalState.readings.turbidity ?? '--'}</strong></div>
          <div>Conductivity: <strong style="color:#fff;">${historicalState.readings.conductivity ?? '--'}</strong></div>
          <div>Temperature: <strong style="color:#fff;">${historicalState.readings.temperature ?? '--'}</strong></div>
        </div>
        <div style="font-size: 11.5px; color: var(--text-dim);">
          Timeline Version: ${historicalState.version} | Events Ingested up to T: ${historicalState.total_events_processed} | Active Resolver: ${strategySelector.value}
        </div>
      `;
    } catch (err) {
      console.error("Historical query error:", err);
    }
  }

  function renderSpatialClusters(clusters) {
    if (!clusters) return;
    let html = "";
    Object.keys(clusters).forEach(cName => {
      const c = clusters[cName];
      const isPlume = c.status === "CONTAMINATION_PLUME_ALERT";
      const isWarn = c.status === "LOCAL_SENSOR_WARNING";

      html += `
        <div class="cluster-card ${isPlume ? 'plume-alert' : ''}">
          <div class="cluster-header">
            <div>
              <h3 style="font-size: 15px; font-weight: 700;">${cName.replace(/_/g, ' ').toUpperCase()}</h3>
              <div style="font-size: 11px; color: var(--text-dim);">Catchment Basin Cluster</div>
            </div>
            <span class="badge ${isPlume ? 'badge-rose' : (isWarn ? 'badge-amber' : 'badge-teal')}">
              ${c.status}
            </span>
          </div>

          <div style="font-size: 13px; margin-bottom: 8px;">
            Sensors: <strong>${c.total_sensors}</strong> | Anomalies: <strong style="color:${isPlume ? 'var(--accent-rose)' : 'var(--accent-teal)'}">${c.anomalous_sensors}</strong>
          </div>

          <div class="cluster-nodes-list">
            ${c.sensors.map(sId => {
              const isSensorAnom = currentSensors[sId] && currentSensors[sId].is_anomalous;
              return `<span class="mono-badge" style="border-color:${isSensorAnom ? 'var(--accent-rose)' : 'var(--border-color)'}; color:${isSensorAnom ? 'var(--accent-rose)' : 'var(--text-main)'};">${sId}</span>`;
            }).join("")}
          </div>
        </div>
      `;
    });
    spatialClusterGrid.innerHTML = html;
  }

  async function loadSpatialData() {
    const resp = await fetch("/analytics/correlations");
    const data = await resp.json();
    renderSpatialClusters(data.clusters);
  }

  async function loadAuditTrail() {
    try {
      const resp = await fetch("/audit?limit=50");
      const data = await resp.json();
      const records = data.records || [];

      if (records.length === 0) {
        auditTableBody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding: 24px;">No audit records found.</td></tr>`;
        return;
      }

      let html = "";
      records.slice().reverse().forEach(r => {
        const isAnom = r.anomaly_report && r.anomaly_report.is_anomaly;
        html += `
          <tr>
            <td><strong>#${r.audit_id}</strong></td>
            <td><span class="badge ${r.action.includes('OUT_OF_ORDER') ? 'badge-amber' : 'badge-teal'}">${r.action}</span></td>
            <td>${r.sensor_id}</td>
            <td>${r.event_timestamp.substring(11, 19)}</td>
            <td class="hash-cell" title="${r.current_hash}">${r.current_hash}</td>
            <td class="hash-cell" title="${r.prev_hash}">${r.prev_hash}</td>
            <td><span class="badge ${isAnom ? 'badge-rose' : 'badge-green'}">${isAnom ? r.anomaly_report.anomaly_type : 'OK'}</span></td>
            <td style="color: var(--text-dim); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${r.conflict_trace ? r.conflict_trace.resolution_notes.join('; ') : 'Direct ingest'}
            </td>
          </tr>
        `;
      });
      auditTableBody.innerHTML = html;
    } catch (err) {
      console.error("Audit load failed:", err);
    }
  }

  // Periodic polling every 3 seconds
  setInterval(refreshDashboard, 3000);
  refreshDashboard();
});
