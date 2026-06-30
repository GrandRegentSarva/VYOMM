# VYOMM

Predictive NOC Copilot demonstration with simulated telemetry, forecasting, anomaly detection, incident correlation, runbook retrieval, and Groq-powered incident analysis.

## Run

```bash
docker compose up --build
```

Open:

```text
http://localhost:8080
```

No manual setup is required for demo mode. A `.env` file can provide `GROQ_API_KEY`; when the key is present the backend calls Groq's OpenAI-compatible chat completions endpoint. If the key is missing, the demo uses a deterministic Groq-style fallback so the judges still see the complete flow.

## Services

- `frontend`: React, TypeScript, Vite, TailwindCSS, React Flow, Recharts, Framer Motion
- `backend`: FastAPI API, SQLite event storage, correlation, forecast, anomaly, RAG, Groq orchestration
- `simulator`: Python telemetry generator for 50 routers, 20 switches, 10 firewalls, and 5 gateways
- `chromadb`: vector store for runbook retrieval
- `nginx`: single public entrypoint on port `8080`

## Demo Behavior

The system starts healthy, then triggers realistic incidents every 30-60 seconds. During an incident the topology highlights affected nodes, charts spike, correlation creates an incident, runbooks are retrieved, and the Groq copilot endpoint returns a structured recommendation. Approving an incident marks it resolved and the next simulator cycle naturally recovers.

## Flow

The dashboard includes a NOC Copilot Flow panel:

1. Telemetry Ingest
2. Chronos-style Forecast
3. Anomaly Detection
4. Incident Correlation
5. Runbook Retrieval
6. Groq Copilot Reasoning
7. Human Approval

## API

- `GET /api/telemetry`
- `POST /api/telemetry`
- `GET /api/forecast`
- `GET /api/anomalies`
- `GET /api/incidents`
- `POST /api/incidents/{incident_id}`
- `GET /api/topology`
- `GET /api/llm`
- `GET /api/runbook`
- `GET /api/flow`
