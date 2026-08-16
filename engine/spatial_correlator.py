"""
Multi-Sensor Spatial and Topological Correlation Engine.
Corroborates localized sensor anomalies against neighboring cluster nodes
to distinguish between localized hardware failures and systemic contamination plumes.
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from engine.models import AnomalyReport, AnomalyType, SensorState


class SpatialCorrelator:
    """
    Analyzes spatial topology and cross-sensor temporal correlations
    across a distributed IoT water monitoring grid.
    """

    # Pre-configured sensor clusters / river catchment zones
    DEFAULT_CLUSTERS: Dict[str, List[str]] = {
        "cluster_basin_north": ["WQ-S101", "WQ-S102", "WQ-S103", "WQ-S123"],
        "cluster_basin_south": ["WQ-S201", "WQ-S202", "WQ-S203", "WQ-S204"],
        "cluster_industrial_inflow": ["WQ-IND01", "WQ-IND02", "WQ-S301"],
    }

    def __init__(self, clusters: Optional[Dict[str, List[str]]] = None):
        self.clusters = clusters or self.DEFAULT_CLUSTERS
        self.sensor_to_cluster: Dict[str, str] = {}
        for c_name, members in self.clusters.items():
            for s_id in members:
                self.sensor_to_cluster[s_id] = c_name

        # Recent anomaly cache: sensor_id -> list of (timestamp_dt, AnomalyReport)
        self._recent_anomalies: Dict[str, List[Tuple[datetime, AnomalyReport]]] = {}

    def record_anomaly(self, sensor_id: str, timestamp_str: str, report: AnomalyReport) -> None:
        """Records an anomaly event into the recent window cache."""
        if not report.is_anomaly:
            return
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        if sensor_id not in self._recent_anomalies:
            self._recent_anomalies[sensor_id] = []
        self._recent_anomalies[sensor_id].append((dt, report))

        # Evict records older than 3 hours
        cutoff = dt - timedelta(hours=3)
        self._recent_anomalies[sensor_id] = [
            (t, r) for (t, r) in self._recent_anomalies[sensor_id] if t >= cutoff
        ]

    def get_cluster_for_sensor(self, sensor_id: str) -> str:
        return self.sensor_to_cluster.get(sensor_id, "default_zone")

    def get_neighbors(self, sensor_id: str) -> List[str]:
        cluster = self.get_cluster_for_sensor(sensor_id)
        if cluster in self.clusters:
            return [s for s in self.clusters[cluster] if s != sensor_id]
        return []

    def evaluate_spatial_correlation(
        self,
        sensor_id: str,
        current_dt: datetime,
        current_report: AnomalyReport,
        all_states: Dict[str, SensorState],
        time_window_minutes: int = 30
    ) -> Tuple[bool, List[str], str]:
        """
        Evaluates whether an anomaly at sensor_id is corroborated by neighbors.
        Returns: (is_corroborated, affected_neighbors, diagnosis_summary)
        """
        if not current_report.is_anomaly:
            return False, [], "Normal - no spatial correlation needed."

        neighbors = self.get_neighbors(sensor_id)
        if not neighbors:
            return False, [], f"No topological neighbors found for {sensor_id}."

        corroborated_neighbors: List[str] = []
        window_start = current_dt - timedelta(minutes=time_window_minutes)
        window_end = current_dt + timedelta(minutes=time_window_minutes)

        for neighbor_id in neighbors:
            # Check 1: Did neighbor have a recent recorded anomaly in window?
            if neighbor_id in self._recent_anomalies:
                for n_dt, n_rep in self._recent_anomalies[neighbor_id]:
                    if window_start <= n_dt <= window_end and n_rep.is_anomaly:
                        corroborated_neighbors.append(neighbor_id)
                        break

            # Check 2: Does neighbor current state show anomalous metric values?
            if neighbor_id not in corroborated_neighbors and neighbor_id in all_states:
                n_state = all_states[neighbor_id]
                if n_state.is_anomalous:
                    corroborated_neighbors.append(neighbor_id)

        if len(corroborated_neighbors) >= 1:
            diagnosis = (
                f"SYSTEMIC PLUME DETECTED: Anomaly at {sensor_id} corroborated by {len(corroborated_neighbors)} "
                f"neighboring nodes ({', '.join(corroborated_neighbors)}) in cluster '{self.get_cluster_for_sensor(sensor_id)}'."
            )
            return True, corroborated_neighbors, diagnosis
        else:
            diagnosis = (
                f"LOCALIZED ISOLATED DEFECT: Anomaly at {sensor_id} has no neighbor corroboration. "
                f"Likely sensor-specific drift, biofilm fouling, or local tap point issue."
            )
            return False, [], diagnosis

    def get_cluster_status_summary(self, all_states: Dict[str, SensorState]) -> Dict[str, Any]:
        """Returns fleet-wide spatial cluster health analytics."""
        summary = {}
        for c_name, members in self.clusters.items():
            total = len(members)
            anomalous_count = sum(1 for m in members if m in all_states and all_states[m].is_anomalous)
            status = "HEALTHY"
            if anomalous_count >= 2:
                status = "CONTAMINATION_PLUME_ALERT"
            elif anomalous_count == 1:
                status = "LOCAL_SENSOR_WARNING"

            summary[c_name] = {
                "total_sensors": total,
                "anomalous_sensors": anomalous_count,
                "status": status,
                "sensors": members
            }
        return summary

    def clear(self) -> None:
        self._recent_anomalies.clear()
