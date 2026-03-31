# 🌦️ MQTT + Python: Real-Time Weather Data for Beginners
## Python Meetup Outline

> **Format:** ~90 min talk + demos  
> **Level:** Beginner-friendly (basic Python assumed)  
> **Repo setup:** Uses `uv` — no more "it works on my machine"

---

## 📋 Table of Contents

1. [What is MQTT?](#1-what-is-mqtt)
2. [Project Setup with uv](#2-project-setup-with-uv)
3. [Demo 1 — Hello MQTT (Basic Pub/Sub)](#3-demo-1--hello-mqtt)
4. [Demo 2 — Fetch Cloud Weather & Publish to MQTT](#4-demo-2--cloud-weather-api--mqtt)
5. [Demo 3 — Self-Hosted Weather Server (Mosquitto)](#5-demo-3--self-hosted-weather-server)
6. [Demo 4 — Full Pipeline: Cloud + Local + Live Dashboard](#6-demo-4--full-pipeline)
7. [Bonus — Meshtastic + BME280 Hardware Sensor](#7-bonus--meshtastic--bme280)
8. [Q&A Prompts & Resources](#8-qa-prompts--resources)

---

## 1. What is MQTT?

**MQTT** (Message Queuing Telemetry Transport) is a lightweight publish/subscribe messaging protocol designed for constrained devices and low-bandwidth, high-latency networks. It's the backbone of a huge chunk of IoT.

### Key Concepts (5 min)

```
Publisher ──► Broker ──► Subscriber
  (weather      (hub)    (dashboard,
   sensor)               database,
                         alert system)
```

| Concept   | Description                                                  |
|-----------|--------------------------------------------------------------|
| **Broker** | The central server. Mosquitto, HiveMQ, EMQX are common choices |
| **Topic**  | A string address like `weather/utah/temperature`. Uses `/` hierarchy |
| **Publish**| Send a message to a topic                                    |
| **Subscribe** | Listen to a topic (or wildcard like `weather/#`)         |
| **QoS**    | Quality of Service: 0 = fire-and-forget, 1 = at-least-once, 2 = exactly-once |
| **Retain** | Broker saves the last message so new subscribers get it immediately |

### Why MQTT over REST/HTTP?

- HTTP: Request → Wait → Response (pull model, stateless)
- MQTT: Fire-and-forget, persistent connection, ~2x smaller packets
- Perfect for sensors that publish every few seconds

### Public MQTT Brokers for Testing

- `test.mosquitto.org:1883` — open, no auth (great for demos!)
- `broker.hivemq.com:1883` — open test broker
- `mqtt.eclipseprojects.io:1883` — Eclipse foundation

---

## 2. Project Setup with uv

**Why uv?** It replaces `pip`, `virtualenv`, `pyenv`, and `poetry` in one fast Rust-based tool. Perfect for meetup demos — one command gets everyone running.

### Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip (if you already have Python)
pip install uv
```

### Initialize the Project

```bash
uv init mqtt-weather
cd mqtt-weather
```

### Add Dependencies

```bash
# Core MQTT client
uv add paho-mqtt

# HTTP requests for cloud APIs
uv add requests

# For our simple self-hosted server
uv add fastapi uvicorn

# Pretty terminal output
uv add rich

# For the Meshtastic bonus section
uv add meshtastic

# Optional: .env file support
uv add python-dotenv
```

This creates a `pyproject.toml` — share the repo and anyone runs `uv sync` to get an identical environment. No more dependency hell!

### Project Structure

```
mqtt-weather/
├── pyproject.toml          # uv manages this
├── .env                    # API keys (git-ignored!)
├── .gitignore
├── demo1_hello_mqtt.py
├── demo2_cloud_weather.py
├── demo3_self_hosted/
│   ├── server.py           # Our fake weather station
│   └── subscriber.py
├── demo4_pipeline.py
└── bonus_meshtastic.py
```

### `.env` file

```dotenv
OPENWEATHER_API_KEY=your_key_here
MQTT_BROKER=test.mosquitto.org
MQTT_PORT=1883
MQTT_TOPIC_PREFIX=meetup/weather
```

> Get a free OpenWeatherMap API key at https://openweathermap.org/api

---

## 3. Demo 1 — Hello MQTT

**Goal:** Understand pub/sub in 30 lines of Python.

### `demo1_hello_mqtt.py`

```python
"""
Demo 1: Hello MQTT
- Connect to a public test broker
- Subscribe to a topic
- Publish a message
- See it come back to us

Run two terminals:
  Terminal 1: uv run demo1_hello_mqtt.py --mode subscribe
  Terminal 2: uv run demo1_hello_mqtt.py --mode publish
"""

import paho.mqtt.client as mqtt
import json
import time
import argparse
from datetime import datetime
from rich import print

BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC = "meetup/weather/hello"  # Change this to something unique!


# ─── Subscriber ────────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[green]✓ Connected to broker: {BROKER}[/green]")
        client.subscribe(TOPIC)
        print(f"[cyan]👂 Listening on topic: {TOPIC}[/cyan]")
    else:
        print(f"[red]✗ Connection failed: {reason_code}[/red]")


def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    print(f"\n[yellow]📨 Message received![/yellow]")
    print(f"   Topic   : [bold]{msg.topic}[/bold]")
    print(f"   Payload : {payload}")
    print(f"   QoS     : {msg.qos}")


def run_subscriber():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_forever()  # Blocking — keeps listening


# ─── Publisher ─────────────────────────────────────────────────────────────────

def run_publisher():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(BROKER, PORT)
    client.loop_start()

    for i in range(5):
        payload = {
            "message": f"Hello from Python meetup! #{i+1}",
            "timestamp": datetime.utcnow().isoformat(),
            "fake_temp_f": round(72.0 + i * 0.5, 1),
        }
        result = client.publish(TOPIC, json.dumps(payload), qos=1)
        print(f"[green]📤 Published:[/green] {payload}")
        time.sleep(2)

    client.loop_stop()
    client.disconnect()


# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["publish", "subscribe"], required=True)
    args = parser.parse_args()

    if args.mode == "subscribe":
        run_subscriber()
    else:
        run_publisher()
```

### 🗣️ Talk Points
- Show both terminals side-by-side
- Explain that the broker is `test.mosquitto.org` — a public server running in the cloud
- Highlight: subscriber doesn't know *who* published, publisher doesn't know *who* is subscribed
- Ask: "What happens if we publish before anyone is subscribed?" → message is lost (QoS 0)
- Introduce `retain=True` as a fix

---

## 4. Demo 2 — Cloud Weather API → MQTT

**Goal:** Pull real weather data from OpenWeatherMap REST API and publish it to MQTT. Show the "bridge" pattern.

### `demo2_cloud_weather.py`

```python
"""
Demo 2: Cloud Weather → MQTT Bridge
- Polls OpenWeatherMap every 60 seconds
- Publishes structured weather data to MQTT topics
- Shows the "data bridge" pattern — REST API → MQTT

Setup:
  1. Get free API key: https://openweathermap.org/api
  2. Add to .env: OPENWEATHER_API_KEY=your_key
  3. uv run demo2_cloud_weather.py
"""

import paho.mqtt.client as mqtt
import requests
import json
import time
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from rich import print
from rich.table import Table
from rich.console import Console

load_dotenv()
console = Console()

# ─── Config ────────────────────────────────────────────────────────────────────
BROKER       = os.getenv("MQTT_BROKER", "test.mosquitto.org")
PORT         = int(os.getenv("MQTT_PORT", 1883))
TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "meetup/weather")
OWM_API_KEY  = os.getenv("OPENWEATHER_API_KEY")
CITIES       = ["Salt Lake City,US", "Denver,US", "Las Vegas,US"]
POLL_SECONDS = 60


# ─── Fetch Weather ─────────────────────────────────────────────────────────────

def fetch_weather(city: str) -> dict | None:
    """Fetch current weather from OpenWeatherMap."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": OWM_API_KEY,
        "units": "imperial",   # °F — we're in Utah after all
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        raw = response.json()

        # Normalize to a clean, flat payload
        return {
            "city":        raw["name"],
            "country":     raw["sys"]["country"],
            "temp_f":      round(raw["main"]["temp"], 1),
            "feels_like_f": round(raw["main"]["feels_like"], 1),
            "humidity_pct": raw["main"]["humidity"],
            "pressure_hpa": raw["main"]["pressure"],
            "wind_mph":    round(raw["wind"]["speed"], 1),
            "condition":   raw["weather"][0]["description"],
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "source":      "openweathermap",
        }
    except requests.RequestException as e:
        print(f"[red]API error for {city}: {e}[/red]")
        return None


# ─── Publish ───────────────────────────────────────────────────────────────────

def publish_weather(client: mqtt.Client, data: dict):
    """
    Publish to multiple granular topics AND one combined topic.
    
    Topic structure:
      meetup/weather/{city}/temperature
      meetup/weather/{city}/humidity
      meetup/weather/{city}/all
    """
    city_slug = data["city"].lower().replace(" ", "_")

    # Granular topics (great for subscribing to just one field)
    fields = {
        "temperature": data["temp_f"],
        "humidity":    data["humidity_pct"],
        "pressure":    data["pressure_hpa"],
        "wind":        data["wind_mph"],
        "condition":   data["condition"],
    }
    for field, value in fields.items():
        topic = f"{TOPIC_PREFIX}/{city_slug}/{field}"
        client.publish(topic, str(value), qos=1, retain=True)

    # Combined payload for dashboards
    combined_topic = f"{TOPIC_PREFIX}/{city_slug}/all"
    client.publish(combined_topic, json.dumps(data), qos=1, retain=True)

    print(f"[green]📤 Published {city_slug} → {combined_topic}[/green]")


# ─── Display ───────────────────────────────────────────────────────────────────

def show_weather_table(weather_list: list[dict]):
    table = Table(title="☁️  Current Weather", show_header=True, header_style="bold cyan")
    table.add_column("City",       style="bold white")
    table.add_column("Temp (°F)",  justify="right")
    table.add_column("Humidity",   justify="right")
    table.add_column("Wind (mph)", justify="right")
    table.add_column("Condition")

    for w in weather_list:
        table.add_row(
            w["city"],
            str(w["temp_f"]),
            f"{w['humidity_pct']}%",
            str(w["wind_mph"]),
            w["condition"],
        )
    console.print(table)


# ─── Main Loop ─────────────────────────────────────────────────────────────────

def main():
    if not OWM_API_KEY:
        print("[red]✗ OPENWEATHER_API_KEY not set in .env![/red]")
        return

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = lambda c, u, f, rc, p: print(
        f"[green]✓ Connected to MQTT broker[/green]" if rc == 0
        else f"[red]✗ MQTT connect failed: {rc}[/red]"
    )
    client.connect(BROKER, PORT)
    client.loop_start()

    print(f"[bold cyan]🌐 Polling {len(CITIES)} cities every {POLL_SECONDS}s...[/bold cyan]\n")

    try:
        while True:
            results = []
            for city in CITIES:
                data = fetch_weather(city)
                if data:
                    publish_weather(client, data)
                    results.append(data)

            if results:
                show_weather_table(results)

            print(f"\n[dim]Next update in {POLL_SECONDS}s... (Ctrl+C to stop)[/dim]\n")
            time.sleep(POLL_SECONDS)

    except KeyboardInterrupt:
        print("\n[yellow]Shutting down...[/yellow]")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
```

### 🗣️ Talk Points
- Show the **topic hierarchy** — `meetup/weather/salt_lake_city/temperature` vs `meetup/weather/salt_lake_city/all`
- Wildcard subscriptions: `meetup/weather/+/temperature` (all cities, just temp)
- `retain=True` means a new subscriber immediately gets the last value
- This is the **bridge pattern**: translating REST → MQTT. Very common in IoT.

---

## 5. Demo 3 — Self-Hosted Weather Server

**Goal:** Run our own MQTT broker + a simulated weather station. No internet required!

### Install Mosquitto (the broker)

```bash
# macOS
brew install mosquitto
brew services start mosquitto

# Ubuntu/Debian
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto

# Windows — download installer from https://mosquitto.org/download/

# Docker (easiest for demos!)
docker run -it -p 1883:1883 eclipse-mosquitto
```

### `demo3_self_hosted/server.py` — Simulated Weather Station

```python
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
```

### `demo3_self_hosted/subscriber.py` — Weather Dashboard

```python
"""
Demo 3b: Weather Dashboard Subscriber
- Subscribes to our local weather station
- Displays a live updating terminal dashboard

Usage: uv run demo3_self_hosted/subscriber.py
"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

BROKER = "localhost"
PORT   = 1883
TOPIC  = "home/weather/#"   # Wildcard — all home weather topics

console = Console()
latest_readings: dict[str, dict] = {}  # station_id → latest data


def build_dashboard() -> Panel:
    if not latest_readings:
        return Panel("[dim]Waiting for data...[/dim]", title="🌡️  Live Weather Dashboard")

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Station",     style="bold white")
    table.add_column("Temp (°F)",   justify="right", style="yellow")
    table.add_column("Humidity",    justify="right", style="cyan")
    table.add_column("Pressure",    justify="right")
    table.add_column("Last Update", style="dim")

    for station_id, data in latest_readings.items():
        # Parse ISO timestamp to friendly format
        ts = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        age = (datetime.now(ts.tzinfo) - ts).seconds

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
                import time; time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
```

### 🗣️ Talk Points
- **Show Mosquitto logs** in a third terminal: `mosquitto -v`
- The wildcard `home/weather/#` — `#` matches everything below that level
- `+` vs `#`: `home/weather/+/temp` matches exactly one level; `#` matches unlimited
- Run multiple "stations" by duplicating `server.py` with different station IDs

---

## 6. Demo 4 — Full Pipeline

**Goal:** Wire everything together — cloud API + local sensor → single broker → dashboard.

### `demo4_pipeline.py`

```python
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
    ("home/weather/#",    1),   # Local sensors
    ("meetup/weather/#",  1),   # Cloud API bridge
]

all_data: dict[str, dict] = {}


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
        
        # Key by city/station for deduplication
        key = data.get("station_id") or data.get("city") or msg.topic
        data["_topic"]   = msg.topic
        data["_source"]  = "local" if msg.topic.startswith("home/") else "cloud"
        data["_received"] = datetime.now(timezone.utc).isoformat()
        all_data[key] = data

    except (json.JSONDecodeError, KeyError):
        pass


def build_unified_dashboard() -> Panel:
    if not all_data:
        return Panel("[dim]Waiting for data from cloud + local sources...[/dim]",
                     title="🌍 Unified Weather Pipeline")

    table = Table(show_header=True, header_style="bold blue", expand=True)
    table.add_column("Source",    style="dim")
    table.add_column("Location",  style="bold white")
    table.add_column("Temp (°F)", justify="right", style="yellow")
    table.add_column("Humidity",  justify="right", style="cyan")
    table.add_column("Condition")
    table.add_column("Age",       style="dim", justify="right")

    for key, data in sorted(all_data.items()):
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
```

---

## 7. Bonus — Meshtastic + BME280

> ⚠️ **Hardware required:** A Meshtastic device (T-Beam, Heltec, RAK4631, etc.) + GY-BME280 module

### What is Meshtastic?

Meshtastic is an open-source, off-grid mesh radio network using LoRa radios. Devices relay messages through each other — no internet, no cell service. Think: neighborhood mesh network that can span miles.

With a BME280 wired up, each node becomes a **real weather station** that broadcasts readings over LoRa and via USB/BLE to Python.

### Wiring the GY-BME280 (I2C)

The GY-BME280 breakout board typically has 4 pins for I2C mode:

```
GY-BME280      Meshtastic Device
─────────────────────────────────────────
VCC (3.3V)  →  3.3V pin
GND         →  GND
SDA         →  SDA (I2C Data)
SCL         →  SCL (I2C Clock)

⚠️  Use 3.3V — NOT 5V. The GY-BME280 is 3.3V logic.
```

**Common pin mappings by board:**

| Board           | SDA  | SCL  |
|-----------------|------|------|
| T-Beam v1.1     | 21   | 22   |
| Heltec WiFi LoRa v3 | 17 | 18 |
| RAK4631         | 13   | 14   |
| T-Echo          | 15   | 14   |

### Enable BME280 in Meshtastic Firmware

Once wired, Meshtastic auto-detects I2C sensors. Verify via the app or CLI:

```bash
# Install Meshtastic CLI
uv tool install meshtastic

# Check detected sensors
meshtastic --info

# Enable telemetry (environment sensor module)
meshtastic --set telemetry.environment_measurement_enabled true
meshtastic --set telemetry.environment_update_interval 60
```

You should see `BME280` listed under detected sensors.

### `bonus_meshtastic.py` — Receive Sensor Data via Python

```python
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
  uv run bonus_meshtastic.py --port /dev/ttyUSB0  # Linux
  uv run bonus_meshtastic.py --port /dev/cu.usbserial-0001  # macOS
  uv run bonus_meshtastic.py --port COM3  # Windows
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
        temp_c    = env.get("temperature")
        humidity  = env.get("relativeHumidity")
        pressure  = env.get("barometricPressure")

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
            "snr":          packet.get("rxSnr"),      # Signal-to-noise ratio
            "rssi":         packet.get("rxRssi"),     # Signal strength
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
        help="Serial port (e.g. /dev/ttyUSB0, COM3). Omit to auto-detect."
    )
    args = parser.parse_args()

    # Connect MQTT
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = lambda c, u, f, rc, p: print(
        f"[green]✓ MQTT connected to {BROKER}[/green]"
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
```

### 🗣️ Talk Points

- Meshtastic uses **LoRa** — very long range (1–10+ miles), very low power
- The BME280 publishes telemetry automatically every 60s once detected
- Our Python bridge converts that to MQTT → it feeds the **same dashboard** from Demo 4!
- SNR and RSSI fields tell us about radio link quality
- Real use cases: remote hiking weather stations, emergency comms networks, neighborhood IoT
- The mesh part: if Node A → Node B → Node C, Node A's data hops through B to reach C

### Troubleshooting BME280

```bash
# Verify I2C device is detected on the host (not on the Meshtastic device)
# This is for Raspberry Pi / Linux only — Meshtastic handles the sensor directly
i2cdetect -y 1
# BME280 default address: 0x76 or 0x77

# Check Meshtastic sees it
meshtastic --info | grep -i bme

# Force sensor re-scan
meshtastic --set telemetry.environment_measurement_enabled false
meshtastic --set telemetry.environment_measurement_enabled true
```

---

## 8. Q&A Prompts & Resources

### Discussion Questions

1. **Security:** This demo uses no auth. How would you secure MQTT in production? (TLS, username/password, client certificates)
2. **Scale:** What happens when you have 1,000 sensors? Cloud MQTT brokers: AWS IoT Core, Azure IoT Hub, HiveMQ Cloud
3. **Persistence:** Right now data disappears when the process stops. How would you add a database? (TimescaleDB + Telegraf, InfluxDB are popular choices)
4. **Home Assistant:** Who uses Home Assistant? It's built on MQTT internally — your same broker works!

### Quick Reference: paho-mqtt Cheat Sheet

```python
import paho.mqtt.client as mqtt

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Callbacks
client.on_connect = lambda c, u, f, rc, p: print("Connected!")
client.on_message = lambda c, u, msg: print(msg.topic, msg.payload.decode())

# Connect & subscribe
client.connect("test.mosquitto.org", 1883)
client.subscribe("my/topic/#")           # Wildcard
client.subscribe([("t1", 0), ("t2", 1)]) # Multiple topics

# Publish
client.publish("my/topic", "hello",         qos=0)  # Fire and forget
client.publish("my/topic", "hello",         qos=1, retain=True)  # At least once + retain

# Event loop options
client.loop_start()    # Background thread (non-blocking)
client.loop_forever()  # Blocking loop
client.loop_stop()     # Stop background thread
```

### Topic Wildcard Quick Reference

```
home/weather/station1/temperature  — exact
home/weather/+/temperature         — any station, just temp
home/weather/#                     — all home weather data
#                                  — EVERYTHING (use with caution!)
```

### Resources

| Resource | URL |
|----------|-----|
| MQTT Spec (readable!) | https://mqtt.org |
| Mosquitto Broker | https://mosquitto.org |
| paho-mqtt docs | https://eclipse.dev/paho/index.php?page=clients/python/index.php |
| OpenWeatherMap free API | https://openweathermap.org/api |
| Meshtastic docs | https://meshtastic.org/docs |
| HiveMQ public broker | https://www.hivemq.com/public-mqtt-broker |
| MQTT Explorer (GUI tool) | https://mqtt-explorer.com |
| uv docs | https://docs.astral.sh/uv |

### `pyproject.toml` Reference

```toml
[project]
name = "mqtt-weather"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "paho-mqtt>=2.1.0",
    "requests>=2.32.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "rich>=13.9.0",
    "python-dotenv>=1.0.0",
    "meshtastic>=2.5.0",
]
```

```bash
# Reproduce this exact environment anywhere
uv sync

# Run any demo
uv run demo1_hello_mqtt.py --mode subscribe
uv run demo2_cloud_weather.py
uv run demo3_self_hosted/server.py
uv run demo3_self_hosted/subscriber.py
uv run demo4_pipeline.py
uv run bonus_meshtastic.py --port /dev/ttyUSB0
```

---

*Prepared for the Python Meetup | West Jordan, UT*  
*All code MIT licensed — take it, break it, improve it!*
