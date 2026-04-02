"""
Demo 5: KB2040 → Serial → MQTT Bridge
- Reads JSON telemetry from a KB2040 running kb2040/code.py over USB serial
- Publishes each reading to home/sensors/kb2040 on the local broker
- Demonstrates CircuitPython as a lightweight MQTT edge device via a serial bridge

Usage:
    uv run demo5_kb2040.py                      # auto-detect KB2040
    uv run demo5_kb2040.py --port /dev/cu.usbmodem101
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import serial
import serial.tools.list_ports
from dotenv import load_dotenv
from rich import print
from rich.table import Table
from rich import box
import os

load_dotenv()

BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT   = int(os.getenv("MQTT_PORT", "1883"))
TOPIC  = "home/sensors/kb2040"

# Adafruit KB2040 USB VID/PID (CircuitPython CDC)
KB2040_VID = 0x239A
KB2040_PID = 0x8115


# ── Serial port detection ─────────────────────────────────────────────────────

def find_kb2040() -> str | None:
    """Return the first serial port that looks like a KB2040."""
    for port in serial.tools.list_ports.comports():
        if port.vid == KB2040_VID and port.pid == KB2040_PID:
            return port.device
        # Fallback: match by description string
        desc = (port.description or "").lower()
        if "kb2040" in desc or ("circuitpython" in desc and "cdc" in desc):
            return port.device
    return None


# ── MQTT ──────────────────────────────────────────────────────────────────────

def make_client() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def on_connect(c, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"[green]✓ MQTT connected[/green] → {BROKER}:{PORT}")
        else:
            print(f"[red]✗ MQTT connect failed[/red] (rc={reason_code})")

    client.on_connect = on_connect
    client.connect(BROKER, PORT)
    client.loop_start()
    return client


# ── Rich table ────────────────────────────────────────────────────────────────

def make_table(data: dict, raw_topic: str) -> Table:
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column("key",   style="dim cyan",  no_wrap=True)
    t.add_column("value", style="bold white", no_wrap=True)

    t.add_row("topic",          raw_topic)
    t.add_row("device",         data.get("device", "?"))
    t.add_row("counter",        str(data.get("counter", "?")))
    t.add_row("voltage",        f"{data.get('voltage_v', '?')} V")
    t.add_row("button presses", str(data.get("button_presses", "?")))
    t.add_row("uptime",         f"{data.get('uptime_s', '?')} s")
    t.add_row("published at",   datetime.now(timezone.utc).strftime("%H:%M:%S UTC"))
    return t


# ── Main ──────────────────────────────────────────────────────────────────────

def main(serial_port: str | None) -> None:
    if serial_port is None:
        serial_port = find_kb2040()

    if serial_port is None:
        print("[red]No KB2040 found.[/red] Plug in the board or pass --port manually.")
        print("\nAvailable ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device:20s}  {p.description}")
        sys.exit(1)

    print(f"[bold green]KB2040 → MQTT Bridge[/bold green]")
    print(f"[dim]Serial:[/dim] {serial_port}  →  [dim]MQTT:[/dim] {BROKER}:{PORT}/{TOPIC}\n")

    client = make_client()
    time.sleep(0.5)   # let MQTT connect

    try:
        with serial.Serial(serial_port, baudrate=115200, timeout=2) as ser:
            print("[dim]Waiting for data…[/dim]\n")
            while True:
                raw = ser.readline()
                if not raw:
                    continue

                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("{"):
                    # CircuitPython boot messages, errors, etc. — pass through
                    print(f"[dim yellow]{line}[/dim yellow]")
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    print(f"[red]bad JSON:[/red] {line}")
                    continue

                # Add a server-side timestamp before publishing
                data["received_at"] = datetime.now(timezone.utc).isoformat()

                client.publish(TOPIC, json.dumps(data), qos=1, retain=True)
                print(make_table(data, TOPIC))

    except serial.SerialException as exc:
        print(f"[red]Serial error:[/red] {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[yellow]Bridge stopped.[/yellow]")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KB2040 serial → MQTT bridge")
    parser.add_argument("--port", help="Serial port (auto-detected if omitted)")
    args = parser.parse_args()
    main(args.port)
