"""
Deterministic Pure NumPy & Pandas Machine Learning Anomaly Detection Engine.
Implements Multivariate Mahalanobis Distance, Temporal Rate-of-Change,
Thermal-pH Coupling Shock, and CUSUM Sensor Drift Detection.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from engine.models import AnomalyReport, AnomalySeverity, AnomalyType, TelemetryEvent


class StatisticalMLAnomalyDetector:
    """
    Pure NumPy/Pandas Machine Learning Engine for IoT Water Quality Telemetry.
    Zero external ML library dependencies. Deterministic, explainable, and replayable.
    """

    DEFAULT_METRIC_ORDER = ["pH", "turbidity", "conductivity", "temperature"]

    # Typical potable/river water quality baseline parameters (mean, std)
    DEFAULT_PRIORS: Dict[str, Tuple[float, float, float, float]] = {
        # metric: (mean, std, hard_min, hard_max)
        "pH": (7.3, 0.45, 0.0, 14.0),
        "turbidity": (3.5, 1.8, 0.0, 500.0),
        "conductivity": (420.0, 65.0, 10.0, 4000.0),
        "temperature": (21.0, 3.2, 0.0, 50.0),
    }

    def __init__(self, history_window_size: int = 50):
        self.history_window_size = history_window_size
        
        # Per-sensor historical buffers: sensor_id -> list of (timestamp_dt, readings_dict)
        self._sensor_history: Dict[str, List[Tuple[datetime, Dict[str, float]]]] = {}

        # Per-sensor CUSUM drift states: sensor_id -> {metric -> (s_pos, s_neg)}
        self._cusum_states: Dict[str, Dict[str, Tuple[float, float]]] = {}

        # Pre-calculate baseline statistical parameters using numpy
        self._init_baseline_model()

    def _init_baseline_model(self) -> None:
        """Initializes the baseline multivariate mean vector and covariance matrix."""
        means = [self.DEFAULT_PRIORS[m][0] for m in self.DEFAULT_METRIC_ORDER]
        stds = [self.DEFAULT_PRIORS[m][1] for m in self.DEFAULT_METRIC_ORDER]

        self.baseline_mean = np.array(means, dtype=np.float64)
        
        # Approximate baseline covariance matrix with realistic cross-metric correlations:
        # e.g. slight negative correlation between temp and dissolved pH stability, conductivity & temp positive correlation
        corr_matrix = np.array([
            [ 1.00,  0.15, -0.10, -0.20],  # pH
            [ 0.15,  1.00,  0.30,  0.05],  # turbidity
            [-0.10,  0.30,  1.00,  0.40],  # conductivity
            [-0.20,  0.05,  0.40,  1.00],  # temperature
        ], dtype=np.float64)

        d_matrix = np.diag(stds)
        self.baseline_cov = d_matrix @ corr_matrix @ d_matrix
        # Invert covariance matrix for Mahalanobis calculations
        self.baseline_cov_inv = np.linalg.pinv(self.baseline_cov)
        # Chi-Square critical threshold for 4 degrees of freedom at p=0.01 (99% confidence) is ~13.28
        # Squared Mahalanobis distance threshold
        self.mahalanobis_sq_threshold = 13.28

    def evaluate_event(
        self,
        event: TelemetryEvent,
        merged_readings: Dict[str, float]
    ) -> AnomalyReport:
        """
        Evaluates incoming telemetry for anomalies against physical limits,
        multivariate statistical distribution, temporal rate-of-change, and cumulative drift.
        """
        sensor_id = event.sensor_id
        event_dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        
        if sensor_id not in self._sensor_history:
            self._sensor_history[sensor_id] = []
            self._cusum_states[sensor_id] = {m: (0.0, 0.0) for m in self.DEFAULT_METRIC_ORDER}

        history = self._sensor_history[sensor_id]
        cusum = self._cusum_states[sensor_id]

        # 1. Check Hard Physical Out-of-Bounds
        for metric, val in merged_readings.items():
            if metric in self.DEFAULT_PRIORS:
                _, _, h_min, h_max = self.DEFAULT_PRIORS[metric]
                if val < h_min or val > h_max:
                    return AnomalyReport(
                        is_anomaly=True,
                        anomaly_type=AnomalyType.OUT_OF_BOUNDS,
                        severity=AnomalySeverity.CRITICAL,
                        anomaly_score=1.0,
                        contributing_metrics=[metric],
                        explanation=f"Metric '{metric}' reading {val} violates physical limits [{h_min}, {h_max}].",
                        details={"metric": metric, "value": val, "min": h_min, "max": h_max}
                    )

        # 2. Check Temporal Rate of Change and Thermal Shock
        if history:
            prev_dt, prev_readings = history[-1]
            time_delta_sec = max(1.0, (event_dt - prev_dt).total_seconds())

            # A. Rate of Change Checks
            for metric in ["pH", "turbidity", "conductivity"]:
                if metric in merged_readings and metric in prev_readings:
                    curr_v = merged_readings[metric]
                    prev_v = prev_readings[metric]
                    delta = curr_v - prev_v
                    rate_per_min = (delta / time_delta_sec) * 60.0

                    # Sudden pH drop/spike > 0.8 units / min
                    if metric == "pH" and abs(rate_per_min) > 0.8:
                        return AnomalyReport(
                            is_anomaly=True,
                            anomaly_type=AnomalyType.TEMPORAL_RATE_OF_CHANGE,
                            severity=AnomalySeverity.HIGH,
                            anomaly_score=min(1.0, abs(rate_per_min) / 1.5),
                            contributing_metrics=["pH"],
                            explanation=f"Sudden pH rate of change: {rate_per_min:+.2f} pH/min (threshold: ±0.8/min).",
                            details={"rate_per_min": rate_per_min, "delta": delta, "duration_sec": time_delta_sec}
                        )

                    # Sudden turbidity explosion > 15 NTU/min
                    if metric == "turbidity" and rate_per_min > 15.0:
                        return AnomalyReport(
                            is_anomaly=True,
                            anomaly_type=AnomalyType.TEMPORAL_RATE_OF_CHANGE,
                            severity=AnomalySeverity.HIGH,
                            anomaly_score=min(1.0, rate_per_min / 30.0),
                            contributing_metrics=["turbidity"],
                            explanation=f"Severe turbidity spike rate: {rate_per_min:+.2f} NTU/min.",
                            details={"rate_per_min": rate_per_min, "delta": delta}
                        )

            # B. Thermal-pH Coupling Shock (Sudden thermal rise >= 4C coupled with pH drop >= 0.5)
            if "temperature" in merged_readings and "temperature" in prev_readings and \
               "pH" in merged_readings and "pH" in prev_readings:
                temp_delta = merged_readings["temperature"] - prev_readings["temperature"]
                ph_delta = merged_readings["pH"] - prev_readings["pH"]
                if temp_delta >= 3.5 and ph_delta <= -0.4 and time_delta_sec <= 300.0:
                    return AnomalyReport(
                        is_anomaly=True,
                        anomaly_type=AnomalyType.THERMAL_PH_COUPLING,
                        severity=AnomalySeverity.CRITICAL,
                        anomaly_score=0.95,
                        contributing_metrics=["temperature", "pH"],
                        explanation=f"Thermal shock event: Temperature surged by {temp_delta:+.1f}°C triggering rapid pH drop of {ph_delta:+.2f}.",
                        details={"temp_delta": temp_delta, "ph_delta": ph_delta, "time_delta_sec": time_delta_sec}
                    )

        # 3. Multivariate Mahalanobis Distance Anomaly Check
        # Build vector using current merged readings or baseline priors for missing metrics
        vec = []
        for m in self.DEFAULT_METRIC_ORDER:
            val = merged_readings.get(m, self.DEFAULT_PRIORS[m][0])
            vec.append(val)
        
        vec_np = np.array(vec, dtype=np.float64)
        diff = vec_np - self.baseline_mean
        mahalanobis_sq = float(diff.T @ self.baseline_cov_inv @ diff)
        mahalanobis_dist = float(np.sqrt(max(0.0, mahalanobis_sq)))

        # 4. Sensor Drift via CUSUM (Cumulative Sum Control Chart)
        drift_flagged = False
        drift_metric = ""
        max_drift_score = 0.0

        for metric in self.DEFAULT_METRIC_ORDER:
            if metric in merged_readings:
                val = merged_readings[metric]
                mean_val, std_val, _, _ = self.DEFAULT_PRIORS[metric]
                z = (val - mean_val) / std_val
                
                # CUSUM parameters: slack k = 0.5, threshold h = 4.5
                k = 0.5
                h = 4.5
                s_pos, s_neg = cusum.get(metric, (0.0, 0.0))
                s_pos = max(0.0, s_pos + z - k)
                s_neg = max(0.0, s_neg - z - k)
                cusum[metric] = (s_pos, s_neg)

                drift_val = max(s_pos, s_neg)
                if drift_val > h:
                    drift_flagged = True
                    drift_metric = metric
                    max_drift_score = max(max_drift_score, drift_val / 8.0)

        # Update History Buffer
        history.append((event_dt, dict(merged_readings)))
        if len(history) > self.history_window_size:
            history.pop(0)

        # Determine if multivariate outlier
        if mahalanobis_sq > self.mahalanobis_sq_threshold:
            # Identify primary contributing metrics via absolute z-scores
            contributing = []
            z_scores = {}
            for idx, m in enumerate(self.DEFAULT_METRIC_ORDER):
                mean_v, std_v, _, _ = self.DEFAULT_PRIORS[m]
                z_score = abs(vec_np[idx] - mean_v) / std_v
                z_scores[m] = round(float(z_score), 2)
                if z_score > 2.0:
                    contributing.append(m)

            norm_score = min(1.0, mahalanobis_dist / 6.0)
            sev = AnomalySeverity.HIGH if norm_score > 0.75 else AnomalySeverity.MEDIUM

            return AnomalyReport(
                is_anomaly=True,
                anomaly_type=AnomalyType.MULTIVARIATE_OUTLIER,
                severity=sev,
                anomaly_score=round(norm_score, 3),
                mahalanobis_distance=round(mahalanobis_dist, 3),
                contributing_metrics=contributing,
                explanation=f"Multivariate statistical deviation (Mahalanobis D={mahalanobis_dist:.2f} > 3.64).",
                details={"z_scores": z_scores, "mahalanobis_sq": round(mahalanobis_sq, 2)}
            )

        # Determine if drift detected
        if drift_flagged:
            return AnomalyReport(
                is_anomaly=True,
                anomaly_type=AnomalyType.SENSOR_DRIFT,
                severity=AnomalySeverity.MEDIUM,
                anomaly_score=round(min(1.0, max_drift_score), 3),
                drift_score=round(max_drift_score, 2),
                contributing_metrics=[drift_metric],
                explanation=f"Persistent statistical drift detected on '{drift_metric}' electrode over temporal window.",
                details={"drift_metric": drift_metric, "cusum_score": round(max_drift_score, 2)}
            )

        # Normal telemetry
        return AnomalyReport(
            is_anomaly=False,
            anomaly_type=AnomalyType.NONE,
            severity=AnomalySeverity.NORMAL,
            anomaly_score=round(mahalanobis_dist / 10.0, 3),
            mahalanobis_distance=round(mahalanobis_dist, 3),
            contributing_metrics=[],
            explanation="Readings within standard statistical and temporal bounds.",
            details={"mahalanobis_dist": round(mahalanobis_dist, 2)}
        )

    def reset(self) -> None:
        """Resets all per-sensor histories and CUSUM states."""
        self._sensor_history.clear()
        self._cusum_states.clear()
