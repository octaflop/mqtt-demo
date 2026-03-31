"""
Demo 3a: Self-Hosted Weather Station Simulator
- Acts like a physical sensor publishing to our LOCAL broker
- Simulates realistic temperature/humidity fluctuations
- Run this FIRST, then run subscriber.py

Usage: uv run demo3_self_hosted/server.py
"""

import paho.mqtt.client as mqtt
import json
import time
import random
import math
from datetime import datetime, timezone
from rich import print

BROKER = "localhost"   # Our local Mosquitto!
PORT   = 1883
TOPIC  = "home/weather/station1"

# Simulated "sensor baseline" for West Jordan, UT
BASE_TEMP_F   = 68.0
BASE_HUMIDITY = 35.0  # Utah is dry!
BASE_PRESSURE = 1013.0


def simulate_reading(t: float) -> dict:
    """
    Simulate realistic sensor readings using a sine wave + noise.
    t = elapsed seconds since start
    """
    # Slow drift (like time of day)
    temp     = BASE_TEMP_F   + 8 * math.sin(t / 300) + random.uniform(-0.5, 0.5)
    humidity = BASE_HUMIDITY + 5 * math.sin(t / 400) + random.uniform(-1, 1)
    pressure = BASE_PRESSURE + 2 * math.sin(t / 600) + random.uniform(-0.2, 0.2)

    return {
        "station_id":   "station1",
        "location":     "West Jordan, UT",
        "temp_f":       round(temp, 2),
        "humidity_pct": round(max(0, min(100, humidity)), 2),
        "pressure_hpa": round(pressure, 2),
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "source":       "simulated_sensor",
    }


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(BROKER, PORT)
    client.loop_start()

    print("[bold green]🌡️  Weather Station Simulator Running[/bold green]")
    print(f"[dim]Publishing to {BROKER}:{PORT} → {TOPIC}[/dim]\n")

    start = time.time()
    try:
        while True:
            t = time.time() - start
            reading = simulate_reading(t)
            client.publish(TOPIC, json.dumps(reading), qos=1, retain=True)
            print(
                f"[cyan]📤[/cyan] "
                f"[bold]{reading['temp_f']}°F[/bold]  "
                f"💧{reading['humidity_pct']}%  "
                f"⬇ {reading['pressure_hpa']}hPa"
            )
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n[yellow]Station offline.[/yellow]")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
