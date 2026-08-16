"""
Idempotent Event Deduplication Engine.
Computes deterministic cryptographic fingerprints for telemetry events to eliminate duplicate packet storms.
"""

from __future__ import annotations
import hashlib
import json
from typing import Any, Dict, Optional, Set
from engine.models import TelemetryEvent


class Deduplicator:
    """
    Guarantees idempotent processing by computing a deterministic SHA-256 fingerprint
    for each telemetry event based on sensor_id, normalized timestamp, sorted readings, and source.
    """

    def __init__(self) -> None:
        self._seen_fingerprints: Set[str] = set()

    @staticmethod
    def compute_fingerprint(event: TelemetryEvent) -> str:
        """
        Produces a canonical, deterministic hash of the telemetry event.
        Two events with the same sensor_id, timestamp, readings, and source
        will produce the exact same fingerprint.
        """
        canonical_readings = {
            k: round(float(v), 6)
            for k, v in sorted(event.readings.items())
            if v is not None
        }
        canonical_dict = {
            "sensor_id": event.sensor_id.strip(),
            "timestamp": event.timestamp.strip(),
            "readings": canonical_readings,
            "source": event.source.strip().lower()
        }
        serialized = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def is_duplicate(self, event: TelemetryEvent) -> tuple[bool, str]:
        """
        Checks if the event has already been seen.
        Returns: (is_duplicate: bool, fingerprint: str)
        """
        fp = self.compute_fingerprint(event)
        if fp in self._seen_fingerprints:
            return True, fp
        self._seen_fingerprints.add(fp)
        return False, fp

    def register(self, fingerprint: str) -> None:
        """Manually registers a fingerprint into the seen set."""
        self._seen_fingerprints.add(fingerprint)

    def contains(self, fingerprint: str) -> bool:
        """Checks if a fingerprint is registered."""
        return fingerprint in self._seen_fingerprints

    def clear(self) -> None:
        """Resets the deduplication cache."""
        self._seen_fingerprints.clear()

    @property
    def total_seen(self) -> int:
        return len(self._seen_fingerprints)
