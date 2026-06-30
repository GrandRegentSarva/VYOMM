from __future__ import annotations

import asyncio
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")


@dataclass
class Device:
    hostname: str
    role: str
    cpu: float
    memory: float
    bandwidth: float
    temperature: float
    latency: float
    packet_loss: float
    uptime: int
    incident_bias: float = 0

    def tick(self, active_incident: str | None) -> dict:
        self.uptime += 1
        self.cpu = drift(self.cpu, 0.9, 18, 88)
        self.memory = drift(self.memory, 0.45, 22, 84)
        self.bandwidth = drift(self.bandwidth, 1.1, 12, 90)
        self.temperature = drift(self.temperature, 0.25, 38, 79)
        self.latency = drift(self.latency, 1.4, 8, 86)
        self.packet_loss = drift(self.packet_loss, 0.08, 0, 2.9)

        if active_incident:
            self.apply_incident(active_incident)

        status = "critical" if self.cpu > 94 or self.latency > 125 or self.packet_loss > 6 or self.temperature > 84 else "warning" if self.cpu > 82 or self.latency > 76 or self.packet_loss > 2.7 or self.memory > 82 else "healthy"
        return {
            "hostname": self.hostname,
            "role": self.role,
            "cpu": round(self.cpu, 2),
            "memory": round(self.memory, 2),
            "bandwidth": round(self.bandwidth, 2),
            "temperature": round(self.temperature, 2),
            "latency": round(self.latency, 2),
            "packet_loss": round(self.packet_loss, 2),
            "uptime": self.uptime,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def apply_incident(self, incident: str) -> None:
        if incident == "cpu":
            self.cpu = min(99, self.cpu + random.uniform(7, 15))
            self.latency = min(155, self.latency + random.uniform(7, 16))
        elif incident == "congestion":
            self.bandwidth = min(99, self.bandwidth + random.uniform(8, 18))
            self.latency = min(180, self.latency + random.uniform(16, 32))
            self.packet_loss = min(9.5, self.packet_loss + random.uniform(0.8, 2.3))
        elif incident == "memory":
            self.memory = min(99, self.memory + random.uniform(5, 12))
            self.cpu = min(96, self.cpu + random.uniform(2, 7))
        elif incident == "bgp":
            self.latency = min(190, self.latency + random.uniform(18, 38))
            self.packet_loss = min(8, self.packet_loss + random.uniform(0.6, 1.9))
        elif incident == "thermal":
            self.temperature = min(91, self.temperature + random.uniform(4, 9))
            self.cpu = min(93, self.cpu + random.uniform(2, 8))
        elif incident == "firewall":
            self.cpu = min(99, self.cpu + random.uniform(8, 14))
            self.bandwidth = min(99, self.bandwidth + random.uniform(7, 14))
            self.latency = min(150, self.latency + random.uniform(10, 26))


def drift(value: float, step: float, floor: float, ceiling: float) -> float:
    pull = (floor + ceiling) / 2
    value += random.uniform(-step, step) + (pull - value) * 0.015
    return max(floor, min(ceiling, value))


def create_devices() -> list[Device]:
    devices: list[Device] = []
    for i in range(1, 51):
        devices.append(Device(f"rtr-{i:02d}", "router", random.uniform(25, 62), random.uniform(32, 68), random.uniform(22, 72), random.uniform(42, 62), random.uniform(12, 46), random.uniform(0, 0.7), random.randint(90000, 600000)))
    for i in range(1, 21):
        devices.append(Device(f"sw-{i:02d}", "switch", random.uniform(18, 48), random.uniform(26, 58), random.uniform(18, 64), random.uniform(38, 58), random.uniform(5, 24), random.uniform(0, 0.4), random.randint(120000, 900000)))
    for i in range(1, 11):
        devices.append(Device(f"fw-{i:02d}", "firewall", random.uniform(30, 66), random.uniform(38, 74), random.uniform(28, 76), random.uniform(43, 66), random.uniform(14, 52), random.uniform(0, 0.8), random.randint(70000, 500000)))
    for i in range(1, 6):
        devices.append(Device(f"gw-{i:02d}", "gateway", random.uniform(28, 58), random.uniform(30, 66), random.uniform(34, 78), random.uniform(40, 61), random.uniform(18, 58), random.uniform(0, 0.8), random.randint(110000, 800000)))
    return devices


def select_incident(devices: list[Device]) -> tuple[str, set[str], int]:
    incident = random.choice(["cpu", "congestion", "memory", "bgp", "thermal", "firewall"])
    role = {"cpu": "router", "congestion": "router", "memory": "router", "bgp": "gateway", "thermal": "switch", "firewall": "firewall"}[incident]
    primary = random.choice([d for d in devices if d.role == role])
    index = int(primary.hostname.split("-")[1])
    affected = {primary.hostname}
    for d in devices:
        if d.role in {"router", "switch", "firewall", "gateway"} and abs(int(d.hostname.split("-")[1]) - index) <= 1:
            if len(affected) < 5:
                affected.add(d.hostname)
    return incident, affected, random.randint(18, 30)


def build_logs(devices: list[dict], active_incident: str | None) -> list[str]:
    now = datetime.now().strftime("%H:%M:%S")
    samples = random.sample(devices, k=min(8, len(devices)))
    protocols = ["SNMP", "Syslog", "NetFlow", "gNMI"]
    logs = []
    for item in samples:
        protocol = random.choice(protocols)
        msg = f"{now} {protocol} {item['hostname']} cpu={item['cpu']} lat={item['latency']}ms loss={item['packet_loss']}% status={item['status']}"
        logs.append(msg)
    if active_incident:
        hot = max(devices, key=lambda d: d["cpu"] + d["latency"] + d["packet_loss"] * 10)
        logs.insert(0, f"{now} Syslog {hot['hostname']} correlated {active_incident} signature detected by simulator")
    return logs


async def wait_for_backend(client: httpx.AsyncClient) -> None:
    while True:
        try:
            response = await client.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(2)


async def main() -> None:
    devices = create_devices()
    active_incident: str | None = None
    affected: set[str] = set()
    incident_ttl = 0
    next_incident = random.randint(8, 16)

    async with httpx.AsyncClient(timeout=10) as client:
        await wait_for_backend(client)
        while True:
            if incident_ttl <= 0:
                active_incident = None
                affected = set()
                next_incident -= 1
                if next_incident <= 0:
                    active_incident, affected, incident_ttl = select_incident(devices)
                    next_incident = random.randint(30, 60)
            else:
                incident_ttl -= 1

            payload_devices = [d.tick(active_incident if d.hostname in affected else None) for d in devices]
            payload = {"devices": payload_devices, "logs": build_logs(payload_devices, active_incident)}
            try:
                await client.post(f"{BACKEND_URL}/api/telemetry", json=payload)
            except httpx.HTTPError:
                pass
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
