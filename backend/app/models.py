from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DeviceRole = Literal["router", "switch", "firewall", "gateway"]
HealthStatus = Literal["healthy", "warning", "critical"]
Severity = Literal["low", "medium", "high", "critical"]


class DeviceTelemetry(BaseModel):
    hostname: str
    role: DeviceRole
    cpu: float = Field(ge=0, le=100)
    memory: float = Field(ge=0, le=100)
    bandwidth: float = Field(ge=0, le=100)
    temperature: float
    latency: float
    packet_loss: float = Field(ge=0)
    uptime: int
    status: HealthStatus
    timestamp: datetime


class TelemetryBatch(BaseModel):
    devices: list[DeviceTelemetry]
    logs: list[str] = []


class ForecastPoint(BaseModel):
    label: str
    cpu: float
    latency: float
    packet_loss: float


class Forecast(BaseModel):
    device: str
    current_trend: str
    confidence: float
    risk_level: Severity
    points: list[ForecastPoint]


class Anomaly(BaseModel):
    id: str
    score: float
    severity: Severity
    device: str
    timestamp: datetime
    signal: str


class Incident(BaseModel):
    id: str
    severity: Severity
    affected_devices: list[str]
    root_cause: str
    status: Literal["active", "resolved", "ignored"]
    timestamp: datetime
    confidence: float
    predicted_sla_breach: str
    recommended_action: str


class IncidentDecision(BaseModel):
    status: Literal["resolved", "ignored"]


class LlmAnalysis(BaseModel):
    incident_id: str
    summary: str
    root_cause: str
    confidence: float
    recommended_fix: str
    business_impact: str
    next_steps: list[str]


class TopologyNode(BaseModel):
    id: str
    label: str
    role: DeviceRole
    status: HealthStatus
    cpu: float
    latency: float
    packet_loss: float


class TopologyEdge(BaseModel):
    id: str
    source: str
    target: str


class Topology(BaseModel):
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]
