"""
Demo 4: Full Pipeline
Combines Demo 2 (cloud API) and Demo 3 (local sensor) into one subscriber
that shows ALL weather data — cloud and local — on a unified dashboard.

This demonstrates the real power of MQTT:
  Multiple sources, one bus, many consumers.

Terminal layout:
  T1: uv run demo3_self_hosted/server.py       (local sensor)
  T2: uv run demo2_cloud_weather.py            (cloud bridge)
  T3: uv run demo4_pipeline.py                 (unified dashboard)
"""

import paho.mqtt.client as mqtt
import json
import os
import threading
import time
from datetime import datetime, timezone
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

load_dotenv()
console = Console()

BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT   = int(os.getenv("MQTT_PORT", 1883))

# Subscribe to BOTH our local station and cloud data
TOPICS = [
    ("home/weather/#",   1),   # Local sensors
    ("meetup/weather/#", 1),   # Cloud API bridge
]

all_data: dict[str, dict] = {}
_lock = threading.Lock()


def on_connect(client, userdata, flags, rc, props):
    if rc == 0:
        for topic, qos in TOPICS:
            client.subscribe(topic, qos)
        console.print(f"[green]✓ Subscribed to {len(TOPICS)} topic groups[/green]")


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()

        # Skip granular topics (e.g. .../temperature), only process /all or station topics
        if msg.topic.endswith(("/temperature", "/humidity", "/pressure", "/wind", "/condition")):
            return

        data = json.loads(payload)

        # Skip scalar payloads (e.g. retained numeric values from public brokers)
        if not isinstance(data, dict):
            return

        # Key by city/station for deduplication
        key = data.get("station_id") or data.get("city") or msg.topic
        data["_topic"]    = msg.topic
        data["_source"]   = "local" if msg.topic.startswith("home/") else "cloud"
        data["_received"] = datetime.now(timezone.utc).isoformat()
        with _lock:
            all_data[key] = data

    except (json.JSONDecodeError, KeyError):
        pass


def build_unified_dashboard() -> Panel:
    with _lock:
        snapshot = dict(all_data)

    if not snapshot:
        return Panel(
            "[dim]Waiting for data from cloud + local sources...[/dim]",
            title="🌍 Unified Weather Pipeline",
        )

    table = Table(show_header=True, header_style="bold blue", expand=True)
    table.add_column("Source",    style="dim")
    table.add_column("Location",  style="bold white")
    table.add_column("Temp (°F)", justify="right", style="yellow")
    table.add_column("Humidity",  justify="right", style="cyan")
    table.add_column("Condition")
    table.add_column("Age",       style="dim", justify="right")

    for key, data in sorted(snapshot.items()):
        source_tag = "[green]local[/green]" if data["_source"] == "local" else "[blue]cloud[/blue]"
        location   = data.get("location") or data.get("city", key)

        ts  = datetime.fromisoformat(data["_received"].replace("Z", "+00:00"))
        age = int((datetime.now(ts.tzinfo) - ts).total_seconds())

        table.add_row(
            source_tag,
            location,
            str(data.get("temp_f", "—")),
            f"{data.get('humidity_pct', '—')}%",
            data.get("condition", "sensor"),
            f"{age}s",
        )

    return Panel(
        table,
        title="🌍  Unified Weather Pipeline — Cloud ☁️  + Local 🏠",
        border_style="bold blue",
    )


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)
    client.loop_start()

    with Live(build_unified_dashboard(), refresh_per_second=2, console=console) as live:
        try:
            while True:
                live.update(build_unified_dashboard())
                time.sleep(0.5)
        except KeyboardInterrupt:
            console.print("\n[yellow]Dashboard closed.[/yellow]")

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
