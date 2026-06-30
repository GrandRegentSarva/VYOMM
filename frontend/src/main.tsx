import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import ReactFlow, { Background, Controls, Edge, Node, Position } from "reactflow";
import "reactflow/dist/style.css";
import { motion } from "framer-motion";
import { Activity, AlertTriangle, BrainCircuit, Check, Clock3, Cpu, Gauge, Shield, X } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import "./styles.css";

type Device = {
  hostname: string;
  role: "router" | "switch" | "firewall" | "gateway";
  cpu: number;
  memory: number;
  bandwidth: number;
  temperature: number;
  latency: number;
  packet_loss: number;
  uptime: number;
  status: "healthy" | "warning" | "critical";
};

type Forecast = {
  device: string;
  current_trend: string;
  confidence: number;
  risk_level: string;
  points: { label: string; cpu: number; latency: number; packet_loss: number }[];
};

type Incident = {
  id: string;
  severity: string;
  affected_devices: string[];
  root_cause: string;
  status: string;
  confidence: number;
  predicted_sla_breach: string;
  recommended_action: string;
};

type Llm = {
  incident_id: string;
  summary: string;
  root_cause: string;
  confidence: number;
  recommended_fix: string;
  business_impact: string;
  next_steps: string[];
};

type Snapshot = {
  devices: Device[];
  logs: string[];
  metrics: Record<string, number | string>;
  timeline: { time: string; kind: string; message: string }[];
  server_time: string;
};

type DataPoint = { time: string; cpu: number; latency: number; loss: number };
type FlowStep = { id: string; label: string; status: string; detail: string };
type FlowState = {
  provider: { provider: string; model: string; mode: string };
  steps: FlowStep[];
};

const emptySnapshot: Snapshot = {
  devices: [],
  logs: [],
  metrics: {},
  timeline: [],
  server_time: new Date().toISOString()
};

const emptyFlow: FlowState = {
  provider: { provider: "copilot", model: "llama-3.3-70b-versatile", mode: "demo-fallback" },
  steps: []
};

function App() {
  const [snapshot, setSnapshot] = useState<Snapshot>(emptySnapshot);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [llm, setLlm] = useState<Llm | null>(null);
  const [selected, setSelected] = useState<Device | null>(null);
  const [series, setSeries] = useState<DataPoint[]>([]);
  const [flow, setFlow] = useState<FlowState>(emptyFlow);
  const [clock, setClock] = useState(new Date());

  async function refresh() {
    const [telemetryRes, forecastRes, incidentsRes, flowRes] = await Promise.all([
      fetch("/api/telemetry"),
      fetch("/api/forecast"),
      fetch("/api/incidents"),
      fetch("/api/flow")
    ]);
    const telemetry = await telemetryRes.json();
    const nextForecast = await forecastRes.json();
    const incidents = await incidentsRes.json();
    const nextFlow = await flowRes.json();
    setSnapshot(telemetry);
    setForecast(nextForecast);
    setIncident(incidents.active ?? null);
    setFlow(nextFlow);
    const avg = average(telemetry.devices);
    setSeries((current) => [...current.slice(-35), { time: new Date().toLocaleTimeString(), ...avg }]);
  }

  useEffect(() => {
    refresh().catch(console.error);
    const dataTimer = window.setInterval(() => refresh().catch(console.error), 2000);
    const clockTimer = window.setInterval(() => setClock(new Date()), 1000);
    return () => {
      window.clearInterval(dataTimer);
      window.clearInterval(clockTimer);
    };
  }, []);

  useEffect(() => {
    fetch(`/api/llm${incident ? `?incident_id=${incident.id}` : ""}`)
      .then((r) => r.json())
      .then(setLlm)
      .catch(console.error);
  }, [incident?.id]);

  const topology = useMemo(() => buildTopology(snapshot.devices, setSelected), [snapshot.devices]);

  async function decide(status: "resolved" | "ignored") {
    if (!incident) return;
    await fetch(`/api/incidents/${incident.id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status })
    });
    setIncident(null);
    setLlm(null);
    await refresh();
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <Shield size={22} />
          <div>
            <strong>VYOMM</strong>
            <span>Predictive NOC Copilot</span>
          </div>
        </div>
        <div className="airgap"><BrainCircuit size={16} /> COPILOT DEMO MODE</div>
        <div className="status-strip">
          <span>{clock.toLocaleTimeString()}</span>
          <b>{incident ? "INCIDENT ACTIVE" : "SYSTEM NORMAL"}</b>
        </div>
      </header>

      <section className="metrics-grid">
        <Metric icon={<Check size={18} />} label="Healthy Devices" value={snapshot.metrics.healthy_devices ?? 0} />
        <Metric icon={<AlertTriangle size={18} />} label="Active Alerts" value={snapshot.metrics.active_alerts ?? 0} hot={Boolean(incident)} />
        <Metric icon={<Gauge size={18} />} label="Prediction Accuracy" value={`${snapshot.metrics.prediction_accuracy ?? 0}%`} />
        <Metric icon={<BrainCircuit size={18} />} label="Copilot Mode" value={flow.provider.mode === "live" ? "LIVE" : "DEMO"} />
        <Metric icon={<Cpu size={18} />} label="GPU Utilization" value={`${snapshot.metrics.gpu_utilization ?? 0}%`} />
        <Metric icon={<Clock3 size={18} />} label="Inference Latency" value={`${snapshot.metrics.inference_latency ?? 0}ms`} />
      </section>

      <section className="workspace">
        <div className="panel topology-panel">
          <PanelTitle title="Enterprise Network Topology" detail={`${snapshot.devices.length || 85} devices`} />
          <ReactFlow nodes={topology.nodes} edges={topology.edges} fitView minZoom={0.25} maxZoom={1.8}>
            <Background color="#2a3444" gap={18} />
            <Controls showInteractive={false} />
          </ReactFlow>
          {selected && (
            <div className="node-detail">
              <strong>{selected.hostname.toUpperCase()}</strong>
              <span>{selected.role} / {selected.status}</span>
              <span>CPU {selected.cpu}% / Latency {selected.latency}ms / Loss {selected.packet_loss}%</span>
            </div>
          )}
        </div>

        <div className="panel charts-panel">
          <PanelTitle title="Live Predictive Signals" detail={forecast ? `${forecast.device} / ${forecast.current_trend}` : "warming up"} />
          <Chart title="CPU" dataKey="cpu" color="#e48b3c" data={series} unit="%" />
          <Chart title="Latency" dataKey="latency" color="#5ea7d8" data={series} unit="ms" />
          <Chart title="Packet Loss" dataKey="loss" color="#d95d5d" data={series} unit="%" />
          <div className="forecast-band">
            <span>Forecast Confidence</span>
            <b>{forecast?.confidence ?? 0}%</b>
            <small>Risk: {forecast?.risk_level ?? "low"}</small>
          </div>
          <ResponsiveContainer width="100%" height={120}>
            <AreaChart data={forecast?.points ?? []}>
              <CartesianGrid stroke="#273243" strokeDasharray="3 3" />
              <XAxis dataKey="label" stroke="#8391a5" />
              <YAxis stroke="#8391a5" />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #2d3748", color: "#fff" }} />
              <Area type="monotone" dataKey="cpu" stroke="#e48b3c" fill="#e48b3c33" />
              <Area type="monotone" dataKey="latency" stroke="#5ea7d8" fill="#5ea7d833" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <motion.div className="panel incident-panel" animate={{ borderColor: incident ? "#d95d5d" : "#2b3442" }}>
          <PanelTitle title="Copilot Incident Summary" detail={llm?.incident_id ?? "NONE"} />
          {incident ? (
            <>
              <div className="severity">{incident.severity}</div>
              <h2>{incident.root_cause}</h2>
              <p>{llm?.summary ?? "Copilot analysis is being generated."}</p>
              <dl>
                <div><dt>Confidence</dt><dd>{Math.round((llm?.confidence ?? incident.confidence) * 100)}%</dd></div>
                <div><dt>Predicted SLA breach</dt><dd>{incident.predicted_sla_breach}</dd></div>
                <div><dt>Root Cause</dt><dd>{llm?.root_cause ?? incident.root_cause}</dd></div>
                <div><dt>Recommended Action</dt><dd>{llm?.recommended_fix ?? incident.recommended_action}</dd></div>
                <div><dt>Business Impact</dt><dd>{llm?.business_impact ?? "Assessing service exposure."}</dd></div>
              </dl>
              <div className="button-row">
                <button className="approve" onClick={() => decide("resolved")}><Check size={16} /> Approve</button>
                <button className="ignore" onClick={() => decide("ignored")}><X size={16} /> Ignore</button>
              </div>
            </>
          ) : (
            <div className="quiet-state">
              <Activity size={34} />
              <h2>No active incident</h2>
              <p>Telemetry, forecast, anomaly, correlation, RAG, and Copilot services are standing by.</p>
            </div>
          )}
        </motion.div>
      </section>

      <section className="lower-grid">
        <div className="panel log-panel">
          <PanelTitle title="Live Telemetry Log" detail="SNMP / Syslog / NetFlow / gNMI" />
          <div className="logs">
            {snapshot.logs.map((line, index) => <code key={`${line}-${index}`}>{line}</code>)}
          </div>
        </div>
        <div className="panel timeline-panel">
          <PanelTitle title="Incident Timeline" detail="forecast -> anomaly -> correlation -> analysis" />
          <div className="timeline">
            {snapshot.timeline.map((item, index) => (
              <div key={`${item.time}-${index}`}>
                <span>{item.time}</span>
                <b>{item.kind}</b>
                <p>{item.message}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="panel flow-panel">
        <PanelTitle title="NOC Copilot Flow" detail={`${flow.provider.model} / ${flow.provider.mode}`} />
        <div className="flow-grid">
          {(flow.steps.length ? flow.steps : demoFlow()).map((step, index) => (
            <div className="flow-step" key={step.id}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <b>{step.label}</b>
              <em>{step.status}</em>
              <p>{step.detail}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

function Metric({ icon, label, value, hot = false }: { icon: React.ReactNode; label: string; value: React.ReactNode; hot?: boolean }) {
  return (
    <div className={`metric ${hot ? "hot" : ""}`}>
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PanelTitle({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="panel-title">
      <h1>{title}</h1>
      <span>{detail}</span>
    </div>
  );
}

function Chart({ title, dataKey, color, data, unit }: { title: string; dataKey: "cpu" | "latency" | "loss"; color: string; data: DataPoint[]; unit: string }) {
  return (
    <div className="chart-box">
      <span>{title}</span>
      <ResponsiveContainer width="100%" height={92}>
        <LineChart data={data}>
          <CartesianGrid stroke="#273243" strokeDasharray="3 3" />
          <XAxis dataKey="time" hide />
          <YAxis stroke="#8391a5" width={34} />
          <Tooltip formatter={(value: number | string) => [`${value}${unit}`, title]} contentStyle={{ background: "#111827", border: "1px solid #2d3748", color: "#fff" }} />
          <Line type="monotone" dataKey={dataKey} dot={false} strokeWidth={2} stroke={color} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function average(devices: Device[]) {
  if (!devices.length) return { cpu: 0, latency: 0, loss: 0 };
  const total = devices.reduce(
    (acc, d) => ({ cpu: acc.cpu + d.cpu, latency: acc.latency + d.latency, loss: acc.loss + d.packet_loss }),
    { cpu: 0, latency: 0, loss: 0 }
  );
  return {
    cpu: Number((total.cpu / devices.length).toFixed(2)),
    latency: Number((total.latency / devices.length).toFixed(2)),
    loss: Number((total.loss / devices.length).toFixed(2))
  };
}

function buildTopology(devices: Device[], setSelected: (device: Device) => void): { nodes: Node[]; edges: Edge[] } {
  const roleY = { gateway: 40, firewall: 170, router: 310, switch: 480 };
  const counters = { gateway: 0, firewall: 0, router: 0, switch: 0 };
  const nodes = devices.map((device) => {
    const count = counters[device.role]++;
    const rowWidth = device.role === "router" ? 10 : device.role === "switch" ? 10 : 5;
    const x = 50 + (count % rowWidth) * 118;
    const y = roleY[device.role] + Math.floor(count / rowWidth) * 54;
    return {
      id: device.hostname,
      position: { x, y },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      data: { label: `${device.hostname.toUpperCase()}` },
      className: `flow-node ${device.status}`,
      style: { width: 86, height: 30 },
      selectable: true
    } satisfies Node;
  });

  const edges: Edge[] = [];
  const byRole = (role: Device["role"]) => devices.filter((d) => d.role === role);
  byRole("router").forEach((router, index) => {
    const gw = byRole("gateway")[index % Math.max(1, byRole("gateway").length)];
    const fw = byRole("firewall")[index % Math.max(1, byRole("firewall").length)];
    const sw = byRole("switch")[index % Math.max(1, byRole("switch").length)];
    if (gw) edges.push(edge(gw.hostname, router.hostname));
    if (fw) edges.push(edge(router.hostname, fw.hostname));
    if (sw) edges.push(edge(router.hostname, sw.hostname));
  });

  return {
    nodes: nodes.map((node) => ({
      ...node,
      data: {
        label: (
          <button className="node-button" onClick={() => setSelected(devices.find((d) => d.hostname === node.id)!)}>
            {node.id.toUpperCase()}
          </button>
        )
      }
    })),
    edges
  };
}

function edge(source: string, target: string): Edge {
  return { id: `${source}-${target}`, source, target, animated: false, style: { stroke: "#334155", strokeWidth: 1.3 } };
}

function demoFlow(): FlowStep[] {
  return [
    { id: "ingest", label: "Telemetry Ingest", status: "warming", detail: "Waiting for simulator batches" },
    { id: "forecast", label: "Forecast", status: "warming", detail: "Preparing risk projection" },
    { id: "anomaly", label: "Anomaly Detection", status: "watching", detail: "Monitoring normalized signals" },
    { id: "correlate", label: "Correlation", status: "watching", detail: "Waiting for incident pattern" },
    { id: "rag", label: "Runbook Retrieval", status: "ready", detail: "Runbooks indexed in ChromaDB" },
    { id: "copilot", label: "Copilot Reasoning", status: "demo-fallback", detail: "Copilot chat-completions client configured" },
    { id: "recommend", label: "Approval", status: "standby", detail: "Human-in-the-loop action ready" }
  ];
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
