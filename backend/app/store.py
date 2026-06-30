from __future__ import annotations

import json
import sqlite3
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Anomaly, DeviceTelemetry, Forecast, Incident, LlmAnalysis


class AppStore:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path
        self._lock = threading.RLock()
        self.devices: dict[str, DeviceTelemetry] = {}
        self.history: dict[str, deque[DeviceTelemetry]] = {}
        self.logs: deque[str] = deque(maxlen=200)
        self.anomalies: deque[Anomaly] = deque(maxlen=100)
        self.incidents: dict[str, Incident] = {}
        self.llm_cache: dict[str, LlmAnalysis] = {}
        self.timeline: deque[dict[str, str]] = deque(maxlen=60)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        Path(self.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.sqlite_path, check_same_thread=False)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def add_timeline(self, kind: str, message: str) -> None:
        now = datetime.now(timezone.utc).astimezone().strftime("%H:%M:%S")
        self.timeline.appendleft({"time": now, "kind": kind, "message": message})

    def ingest(self, devices: list[DeviceTelemetry], logs: list[str]) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            for device in devices:
                self.devices[device.hostname] = device
                self.history.setdefault(device.hostname, deque(maxlen=90)).append(device)
            for log in logs:
                self.logs.appendleft(log)
            self.add_timeline("Telemetry", f"Ingested {len(devices)} device updates")

        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO telemetry(hostname, payload, created_at) VALUES (?, ?, ?)",
                [(d.hostname, d.model_dump_json(), created_at) for d in devices],
            )

    def upsert_incident(self, incident: Incident) -> None:
        with self._lock:
            existing = self.incidents.get(incident.id)
            if existing and existing.status != "active":
                return
            self.incidents[incident.id] = incident
            self.add_timeline("Correlation", f"{incident.root_cause} on {', '.join(incident.affected_devices[:2])}")
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO incidents(id, payload, updated_at) VALUES (?, ?, ?)",
                (incident.id, incident.model_dump_json(), datetime.now(timezone.utc).isoformat()),
            )

    def update_incident_status(self, incident_id: str, status: str) -> Incident | None:
        with self._lock:
            incident = self.incidents.get(incident_id)
            if not incident:
                return None
            updated = incident.model_copy(update={"status": status})
            self.incidents[incident_id] = updated
            self.add_timeline("Recommendation", f"Incident {incident_id} marked {status}")
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO incidents(id, payload, updated_at) VALUES (?, ?, ?)",
                (updated.id, updated.model_dump_json(), datetime.now(timezone.utc).isoformat()),
            )
        return updated

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            devices = list(self.devices.values())
            active = [i for i in self.incidents.values() if i.status == "active"]
            critical = sum(1 for d in devices if d.status == "critical")
            warning = sum(1 for d in devices if d.status == "warning")
            return {
                "devices": devices,
                "logs": list(self.logs),
                "incidents": sorted(self.incidents.values(), key=lambda i: i.timestamp, reverse=True),
                "active_incident": max(active, key=lambda i: i.timestamp, default=None),
                "anomalies": list(self.anomalies),
                "timeline": list(self.timeline),
                "metrics": {
                    "healthy_devices": max(0, len(devices) - critical - warning),
                    "active_alerts": len(active),
                    "prediction_accuracy": 94.2,
                    "offline_status": "COPILOT DEMO",
                    "gpu_utilization": 63 + (len(active) * 7),
                    "inference_latency": 812 + (len(active) * 96),
                },
            }

    def add_anomaly(self, anomaly: Anomaly) -> None:
        with self._lock:
            if not any(a.id == anomaly.id for a in self.anomalies):
                self.anomalies.appendleft(anomaly)
                self.add_timeline("Anomaly", f"{anomaly.signal} on {anomaly.device}")

    def latest_forecast_input(self, device: str | None = None) -> tuple[str | None, list[DeviceTelemetry]]:
        with self._lock:
            selected = device or self._riskiest_device()
            if not selected:
                return None, []
            return selected, list(self.history.get(selected, []))

    def _riskiest_device(self) -> str | None:
        if not self.devices:
            return None
        return max(
            self.devices.values(),
            key=lambda d: d.cpu * 0.35 + d.latency * 0.25 + d.packet_loss * 8 + d.memory * 0.2,
        ).hostname

    def cache_llm(self, analysis: LlmAnalysis) -> None:
        with self._lock:
            self.llm_cache[analysis.incident_id] = analysis
            self.add_timeline("AI Analysis", f"Generated Copilot analysis for {analysis.incident_id}")


def json_loads(payload: str) -> dict[str, Any]:
    return json.loads(payload)
