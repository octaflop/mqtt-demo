"""
Bonus: Meshtastic + BME280 → MQTT Bridge

This script:
1. Connects to your Meshtastic device (USB serial or BLE)
2. Receives environment telemetry (temp, humidity, pressure from BME280)
3. Publishes it to MQTT — feeding our same weather pipeline!

Requirements:
  - Meshtastic device connected via USB
  - BME280 wired and detected (run 'meshtastic --info' to verify)
  - uv add meshtastic paho-mqtt rich

Usage:
  uv run bonus_meshtastic.py --port /dev/ttyUSB0          # Linux
  uv run bonus_meshtastic.py --port /dev/cu.usbserial-0001  # macOS
  uv run bonus_meshtastic.py --port COM3                   # Windows
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from rich import print
from rich.console import Console

# Meshtastic imports
import meshtastic
import meshtastic.serial_interface
from pubsub import pub  # meshtastic uses pypubsub for callbacks

load_dotenv()
console = Console()

BROKER       = os.getenv("MQTT_BROKER", "localhost")
PORT         = int(os.getenv("MQTT_PORT", 1883))
TOPIC_PREFIX = "meshtastic/weather"

mqtt_client: mqtt.Client | None = None


# ─── Meshtastic Callbacks ───────────────────────────────────────────────────────

def on_receive(packet, interface):
    """Called every time ANY packet arrives from the mesh network."""
    try:
        # We only care about telemetry packets with environment data
        if "decoded" not in packet:
            return

        decoded = packet["decoded"]

        # Meshtastic telemetry portnum = 67 (TELEMETRY_APP)
        if decoded.get("portnum") != "TELEMETRY_APP":
            return

        telemetry = decoded.get("telemetry", {})
        env = telemetry.get("environmentMetrics", {})

        if not env:
            return  # Not an environment reading

        # Extract BME280 data
        # Note: Meshtastic reports temperature in Celsius
        temp_c   = env.get("temperature")
        humidity = env.get("relativeHumidity")
        pressure = env.get("barometricPressure")

        if temp_c is None:
            return

        temp_f = round(temp_c * 9 / 5 + 32, 2)

        payload = {
            "node_id":      packet.get("fromId", "unknown"),
            "node_num":     packet.get("from"),
            "temp_c":       round(temp_c, 2),
            "temp_f":       temp_f,
            "humidity_pct": round(humidity, 2) if humidity else None,
            "pressure_hpa": round(pressure, 2) if pressure else None,
            "snr":          packet.get("rxSnr"),   # Signal-to-noise ratio
            "rssi":         packet.get("rxRssi"),  # Signal strength
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "source":       "meshtastic_bme280",
        }

        print(
            f"[bold magenta]📡 Meshtastic node {payload['node_id']}:[/bold magenta] "
            f"[yellow]{payload['temp_f']}°F[/yellow]  "
            f"💧{payload.get('humidity_pct', '—')}%  "
            f"⬇ {payload.get('pressure_hpa', '—')} hPa  "
            f"[dim]SNR={payload.get('snr')} RSSI={payload.get('rssi')}[/dim]"
        )

        # Publish to MQTT!
        if mqtt_client:
            node = payload["node_id"].lstrip("!")
            topic = f"{TOPIC_PREFIX}/{node}/all"
            mqtt_client.publish(topic, json.dumps(payload), qos=1, retain=True)
            print(f"[green]  ↳ Published to {topic}[/green]")

    except Exception as e:
        print(f"[red]Error processing packet: {e}[/red]")


def on_connection(interface, topic=pub.AUTO_TOPIC):
    print("[green]✓ Connected to Meshtastic device[/green]")


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    global mqtt_client

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port",
        default=None,
        help="Serial port (e.g. /dev/ttyUSB0, COM3). Omit to auto-detect.",
    )
    args = parser.parse_args()

    # Connect MQTT
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = lambda c, u, f, rc, p: print(
        f"[green]✓ MQTT connected to {BROKER}[/green]" if rc == 0
        else f"[red]✗ MQTT connect failed: {rc}[/red]"
    )
    mqtt_client.connect(BROKER, PORT)
    mqtt_client.loop_start()

    # Register Meshtastic callbacks
    pub.subscribe(on_receive, "meshtastic.receive")
    pub.subscribe(on_connection, "meshtastic.connection.established")

    # Connect to device
    print(f"[cyan]Connecting to Meshtastic device on {args.port or 'auto'}...[/cyan]")
    iface = meshtastic.serial_interface.SerialInterface(args.port)

    print("[bold]Listening for BME280 telemetry (interval: ~60s per node)...[/bold]")
    print("[dim]Press Ctrl+C to stop.[/dim]\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[yellow]Shutting down...[/yellow]")
    finally:
        iface.close()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
