from __future__ import annotations

import json
import logging

import httpx

from .models import Forecast, Incident, LlmAnalysis

logger = logging.getLogger(__name__)


class LocalLlmClient:
    def __init__(self, base_url: str, model: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    async def analyze(self, incident: Incident, forecast: Forecast, telemetry: list[dict], runbooks: list[dict[str, str]]) -> LlmAnalysis:
        if not self._has_real_key():
            return self.fallback(incident, forecast, runbooks)

        prompt = self._prompt(incident, forecast, telemetry, runbooks)
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a senior NOC copilot. Return only valid JSON.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.2,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                payload = response.json()
                raw = payload["choices"][0]["message"]["content"]
                data = json.loads(raw)
                return LlmAnalysis(
                    incident_id=incident.id,
                    summary=data.get("summary", ""),
                    root_cause=data.get("root_cause", incident.root_cause),
                    confidence=float(data.get("confidence", incident.confidence)),
                    recommended_fix=data.get("recommended_fix", incident.recommended_action),
                    business_impact=data.get("business_impact", "Potential customer-facing degradation if unresolved."),
                    next_steps=list(data.get("next_steps", []))[:5],
                )
        except Exception:
            logger.exception("Copilot analysis failed; returning deterministic demo explanation")
            return self.fallback(incident, forecast, runbooks)

    def provider_status(self) -> dict[str, str]:
        return {
            "provider": "copilot",
            "model": self.model,
            "mode": "live" if self._has_real_key() else "demo-fallback",
        }

    def fallback(self, incident: Incident, forecast: Forecast, runbooks: list[dict[str, str]]) -> LlmAnalysis:
        source = runbooks[0]["source"] if runbooks else "correlation rules"
        return LlmAnalysis(
            incident_id=incident.id,
            summary=f"Demo Copilot classified {incident.root_cause} across {', '.join(incident.affected_devices)} with {incident.severity} severity.",
            root_cause=f"Correlation rules matched telemetry pressure, forecast risk, and retrieved runbook evidence from {source}.",
            confidence=incident.confidence,
            recommended_fix=incident.recommended_action,
            business_impact=f"SLA breach predicted in {incident.predicted_sla_breach}; traffic may experience elevated latency or drops.",
            next_steps=[
                "Validate telemetry against the primary and neighbor devices.",
                "Apply the recommended mitigation through the change window guardrail.",
                "Watch CPU, latency, and packet loss for five minutes after remediation.",
            ],
        )

    def _prompt(self, incident: Incident, forecast: Forecast, telemetry: list[dict], runbooks: list[dict[str, str]]) -> str:
        return (
            "You are VYOMM, a Copilot-powered predictive NOC copilot for a demonstration environment. "
            "Return strict JSON with keys summary, root_cause, confidence, recommended_fix, business_impact, next_steps.\n\n"
            f"Incident:\n{incident.model_dump_json()}\n\n"
            f"Forecast:\n{forecast.model_dump_json()}\n\n"
            f"Telemetry:\n{json.dumps(telemetry[:8])}\n\n"
            f"Retrieved runbooks:\n{json.dumps(runbooks[:2])}\n"
        )

    def _has_real_key(self) -> bool:
        return bool(self.api_key and self.api_key != "demo-mode" and self.api_key.startswith("gsk_"))
