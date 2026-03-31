"""
Demo 3b: Weather Dashboard Subscriber
- Subscribes to our local weather station
- Displays a live updating terminal dashboard

Usage: uv run demo3_self_hosted/subscriber.py
"""

import paho.mqtt.client as mqtt
import json
import threading
import time
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

BROKER = "localhost"
PORT   = 1883
TOPIC  = "home/weather/#"   # Wildcard — all home weather topics

console = Console()
latest_readings: dict[str, dict] = {}  # station_id → latest data
_lock = threading.Lock()


def build_dashboard() -> Panel:
    with _lock:
        snapshot = dict(latest_readings)

    if not snapshot:
        return Panel("[dim]Waiting for data...[/dim]", title="🌡️  Live Weather Dashboard")

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Station",     style="bold white")
    table.add_column("Temp (°F)",   justify="right", style="yellow")
    table.add_column("Humidity",    justify="right", style="cyan")
    table.add_column("Pressure",    justify="right")
    table.add_column("Last Update", style="dim")

    for station_id, data in snapshot.items():
        ts = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        age = int((datetime.now(ts.tzinfo) - ts).total_seconds())

        table.add_row(
            data.get("location", station_id),
            f"{data['temp_f']}°F",
            f"{data['humidity_pct']}%",
            f"{data['pressure_hpa']} hPa",
            f"{age}s ago",
        )

    return Panel(table, title="🌡️  Live Weather Dashboard", border_style="green")


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe(TOPIC)
        console.print(f"[green]✓ Subscribed to: {TOPIC}[/green]")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        station_id = data.get("station_id", msg.topic)
        with _lock:
            latest_readings[station_id] = data
    except json.JSONDecodeError:
        pass


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)
    client.loop_start()

    with Live(build_dashboard(), refresh_per_second=2, console=console) as live:
        try:
            while True:
                live.update(build_dashboard())
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
