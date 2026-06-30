from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .analytics import build_forecast, correlate_incidents, detect_anomalies
from .config import Settings, get_settings
from .llm import LocalLlmClient
from .models import IncidentDecision, LlmAnalysis, TelemetryBatch, Topology, TopologyEdge, TopologyNode
from .rag import RunbookRag
from .store import AppStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("vyomm")


def get_store() -> AppStore:
    return app.state.store


def get_rag() -> RunbookRag:
    return app.state.rag


def get_llm() -> LocalLlmClient:
    return app.state.llm


@asynccontextmanager
async def lifespan(api: FastAPI):
    settings = get_settings()
    api.state.store = AppStore(settings.sqlite_path)
    api.state.rag = RunbookRag(settings.chroma_host, settings.chroma_port, settings.runbook_path)
    api.state.rag.startup()
    api.state.llm = LocalLlmClient(settings.groq_base_url, settings.groq_model, settings.groq_api_key)
    logger.info("VYOMM backend online")
    yield


app = FastAPI(title="VYOMM Predictive NOC Copilot", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(settings: Settings = Depends(get_settings), llm: LocalLlmClient = Depends(get_llm)) -> dict[str, str]:
    provider = llm.provider_status()
    return {"status": "ok", "mode": "groq-demo", "model": settings.groq_model, "llm_mode": provider["mode"]}


@app.post("/api/telemetry")
def ingest_telemetry(batch: TelemetryBatch, store: AppStore = Depends(get_store)) -> dict[str, int]:
    store.ingest(batch.devices, batch.logs)
    for anomaly in detect_anomalies(batch.devices):
        store.add_anomaly(anomaly)
    for incident in correlate_incidents(batch.devices):
        store.upsert_incident(incident)
    return {"devices": len(batch.devices), "logs": len(batch.logs)}


@app.get("/api/telemetry")
def telemetry(store: AppStore = Depends(get_store)) -> dict:
    snap = store.snapshot()
    return {
        "devices": snap["devices"],
        "logs": snap["logs"],
        "metrics": snap["metrics"],
        "timeline": snap["timeline"],
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/forecast")
def forecast(device: str | None = None, store: AppStore = Depends(get_store)) -> dict:
    selected, history = store.latest_forecast_input(device)
    result = build_forecast(selected, history)
    store.add_timeline("Forecast", f"{result.current_trend} risk forecast for {result.device}")
    return result.model_dump()


@app.get("/api/anomalies")
def anomalies(store: AppStore = Depends(get_store)) -> list[dict]:
    return [a.model_dump() for a in store.snapshot()["anomalies"]]


@app.get("/api/incidents")
def incidents(store: AppStore = Depends(get_store)) -> dict:
    snap = store.snapshot()
    return {
        "active": snap["active_incident"],
        "items": snap["incidents"],
    }


@app.post("/api/incidents/{incident_id}")
def decide_incident(incident_id: str, decision: IncidentDecision, store: AppStore = Depends(get_store)) -> dict:
    updated = store.update_incident_status(incident_id, decision.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Incident not found")
    return updated.model_dump()


@app.get("/api/topology")
def topology(store: AppStore = Depends(get_store)) -> Topology:
    devices = store.snapshot()["devices"]
    nodes = [
        TopologyNode(
            id=d.hostname,
            label=d.hostname.upper(),
            role=d.role,
            status=d.status,
            cpu=d.cpu,
            latency=d.latency,
            packet_loss=d.packet_loss,
        )
        for d in devices
    ]
    edges: list[TopologyEdge] = []
    routers = [n.id for n in nodes if n.role == "router"]
    switches = [n.id for n in nodes if n.role == "switch"]
    firewalls = [n.id for n in nodes if n.role == "firewall"]
    gateways = [n.id for n in nodes if n.role == "gateway"]
    for i, router in enumerate(routers):
        if gateways:
            edges.append(TopologyEdge(id=f"{gateways[i % len(gateways)]}-{router}", source=gateways[i % len(gateways)], target=router))
        if firewalls:
            edges.append(TopologyEdge(id=f"{router}-{firewalls[i % len(firewalls)]}", source=router, target=firewalls[i % len(firewalls)]))
        if switches:
            edges.append(TopologyEdge(id=f"{router}-{switches[i % len(switches)]}", source=router, target=switches[i % len(switches)]))
    return Topology(nodes=nodes, edges=edges[:120])


@app.get("/api/runbook")
def runbook(query: str = "network incident", rag: RunbookRag = Depends(get_rag)) -> list[dict[str, str]]:
    return rag.retrieve(query)


@app.get("/api/flow")
def decision_flow(store: AppStore = Depends(get_store), llm: LocalLlmClient = Depends(get_llm)) -> dict:
    snap = store.snapshot()
    active = snap["active_incident"]
    anomalies = snap["anomalies"]
    devices = snap["devices"]
    provider = llm.provider_status()
    return {
        "provider": provider,
        "steps": [
            {
                "id": "ingest",
                "label": "Telemetry Ingest",
                "status": "live" if devices else "warming",
                "detail": f"{len(devices)} devices updating each second",
            },
            {
                "id": "forecast",
                "label": "Chronos-Style Forecast",
                "status": "live" if devices else "warming",
                "detail": "CPU, latency, and loss risk projected over the next 30 minutes",
            },
            {
                "id": "anomaly",
                "label": "Anomaly Detection",
                "status": "active" if anomalies else "watching",
                "detail": f"{len(anomalies)} recent anomaly signals normalized",
            },
            {
                "id": "correlate",
                "label": "Incident Correlation",
                "status": "active" if active else "watching",
                "detail": active.root_cause if active else "Waiting for multi-signal incident pattern",
            },
            {
                "id": "rag",
                "label": "Runbook Retrieval",
                "status": "ready",
                "detail": "ChromaDB indexes CPU, latency, memory, BGP, firewall, and packet-loss runbooks",
            },
            {
                "id": "copilot",
                "label": "Copilot Reasoning",
                "status": provider["mode"],
                "detail": f"{provider['model']} via Copilot chat completions",
            },
            {
                "id": "recommend",
                "label": "Human Approval",
                "status": "pending" if active else "standby",
                "detail": "Approve resolves the incident and lets the simulated network recover",
            },
        ],
    }


@app.get("/api/llm")
async def llm_analysis(
    incident_id: str | None = None,
    store: AppStore = Depends(get_store),
    rag: RunbookRag = Depends(get_rag),
    llm: LocalLlmClient = Depends(get_llm),
) -> LlmAnalysis:
    snap = store.snapshot()
    incident = None
    if incident_id:
        incident = next((i for i in snap["incidents"] if i.id == incident_id), None)
    incident = incident or snap["active_incident"]
    if not incident:
        return LlmAnalysis(
            incident_id="NONE",
            summary="No active incident. The Copilot-enabled NOC is observing nominal telemetry.",
            root_cause="No correlated fault pattern detected.",
            confidence=0.91,
            recommended_fix="Continue monitoring.",
            business_impact="No current business impact.",
            next_steps=["Maintain watch on forecast risk", "Keep simulator telemetry flowing"],
        )
    cached = store.llm_cache.get(incident.id)
    if cached:
        return cached
    selected, history = store.latest_forecast_input(incident.affected_devices[0])
    fc = build_forecast(selected, history)
    runbooks = rag.retrieve(f"{incident.root_cause} {' '.join(incident.affected_devices)}")
    telemetry = [d.model_dump(mode="json") for d in history[-8:]]
    analysis = await llm.analyze(incident, fc, telemetry, runbooks)
    store.cache_llm(analysis)
    return analysis
