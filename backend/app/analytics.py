from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone

import numpy as np

from .models import Anomaly, DeviceTelemetry, Forecast, ForecastPoint, Incident


def build_forecast(device: str | None, history: list[DeviceTelemetry]) -> Forecast:
    if not device or not history:
        points = [ForecastPoint(label=f"+{i * 5}m", cpu=0, latency=0, packet_loss=0) for i in range(1, 7)]
        return Forecast(device="pending", current_trend="Awaiting telemetry", confidence=0.0, risk_level="low", points=points)

    recent = history[-18:]
    cpu = np.array([d.cpu for d in recent], dtype=float)
    latency = np.array([d.latency for d in recent], dtype=float)
    loss = np.array([d.packet_loss for d in recent], dtype=float)

    def project(values: np.ndarray, minutes: int) -> float:
        if len(values) < 2:
            return float(values[-1])
        slope = (values[-1] - values[0]) / max(1, len(values) - 1)
        return float(max(0, values[-1] + slope * minutes + math.sin(minutes) * 0.7))

    points = [
        ForecastPoint(
            label=f"+{i * 5}m",
            cpu=round(min(100, project(cpu, i)), 2),
            latency=round(max(0, project(latency, i) + i * 1.8), 2),
            packet_loss=round(max(0, project(loss, i) + i * 0.08), 2),
        )
        for i in range(1, 7)
    ]
    terminal = points[-1]
    risk_score = terminal.cpu * 0.4 + terminal.latency * 0.25 + terminal.packet_loss * 8
    risk = "critical" if risk_score > 90 else "high" if risk_score > 72 else "medium" if risk_score > 54 else "low"
    trend = "Escalating" if risk in {"high", "critical"} else "Stable with watch conditions" if risk == "medium" else "Healthy"
    confidence = min(98, 74 + len(recent) * 1.1 + (8 if risk != "low" else 0))
    return Forecast(device=device, current_trend=trend, confidence=round(confidence, 1), risk_level=risk, points=points)


def detect_anomalies(devices: list[DeviceTelemetry]) -> list[Anomaly]:
    anomalies: list[Anomaly] = []
    now = datetime.now(timezone.utc)
    for d in devices:
        checks = [
            ("CPU saturation", d.cpu, 88, 97),
            ("Memory pressure", d.memory, 86, 96),
            ("High latency", d.latency, 85, 150),
            ("Packet loss", d.packet_loss, 3.5, 8),
            ("Thermal drift", d.temperature, 72, 86),
        ]
        for signal, value, warning, critical in checks:
            if value >= warning:
                score = min(1.0, value / critical)
                severity = "critical" if value >= critical else "high" if score > 0.82 else "medium"
                digest = hashlib.sha1(f"{d.hostname}:{signal}:{int(now.timestamp() // 20)}".encode()).hexdigest()[:10]
                anomalies.append(
                    Anomaly(
                        id=f"anom-{digest}",
                        score=round(score, 3),
                        severity=severity,
                        device=d.hostname,
                        timestamp=now,
                        signal=signal,
                    )
                )
    return anomalies


def correlate_incidents(devices: list[DeviceTelemetry]) -> list[Incident]:
    by_host = {d.hostname: d for d in devices}
    incidents: list[Incident] = []
    now = datetime.now(timezone.utc)

    for d in devices:
        neighbors = _neighbors(d, by_host)
        neighbor_latency = max((n.latency for n in neighbors), default=d.latency)
        neighbor_loss = max((n.packet_loss for n in neighbors), default=d.packet_loss)
        incident_type: str | None = None
        severity = "high"
        action = "Drain traffic from the affected path and apply QoS shaping."
        sla = "22 minutes"

        if d.role == "router" and d.cpu > 95 and neighbor_latency > 100 and neighbor_loss > 5:
            incident_type = "Congestion Incident"
            severity = "critical"
        elif d.role == "firewall" and (d.cpu > 90 or d.bandwidth > 92) and d.latency > 90:
            incident_type = "Firewall Saturation"
            action = "Move inspection-heavy flows to standby firewall and verify policy hit counters."
            sla = "18 minutes"
        elif d.memory > 94 and d.cpu > 80:
            incident_type = "Memory Leak"
            action = "Fail over services, collect process table, and restart the affected network daemon."
        elif d.packet_loss > 7 and d.latency > 120:
            incident_type = "Packet Loss Degradation"
            action = "Check interface errors, optical levels, and upstream queue drops."
        elif d.temperature > 84 and d.role == "switch":
            incident_type = "Switch Overheating"
            action = "Shift access load, validate fan telemetry, and inspect rack airflow."
            sla = "12 minutes"
        elif d.role == "gateway" and d.latency > 140 and d.packet_loss > 4:
            incident_type = "BGP Edge Instability"
            action = "Prefer secondary edge route, verify BGP timers, and compare route dampening events."
            severity = "critical"
            sla = "15 minutes"

        if incident_type:
            affected = [d.hostname] + [n.hostname for n in neighbors[:2]]
            digest = hashlib.sha1(f"{incident_type}:{d.hostname}".encode()).hexdigest()[:8]
            incidents.append(
                Incident(
                    id=f"INC-{digest.upper()}",
                    severity=severity,  # type: ignore[arg-type]
                    affected_devices=affected,
                    root_cause=incident_type,
                    status="active",
                    timestamp=now,
                    confidence=round(0.78 + min(0.18, (d.cpu + d.latency / 2 + d.packet_loss * 6) / 1000), 2),
                    predicted_sla_breach=sla,
                    recommended_action=action,
                )
            )
    return incidents[:4]


def _neighbors(device: DeviceTelemetry, by_host: dict[str, DeviceTelemetry]) -> list[DeviceTelemetry]:
    role_prefixes = ["rtr", "sw", "fw", "gw"]
    suffix = "".join(ch for ch in device.hostname if ch.isdigit())
    index = int(suffix or "1")
    candidates = []
    for prefix in role_prefixes:
        for offset in (0, 1, -1):
            name = f"{prefix}-{max(1, index + offset):02d}"
            if name in by_host and name != device.hostname:
                candidates.append(by_host[name])
    return candidates
