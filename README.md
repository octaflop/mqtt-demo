# MQTT + Python: Real-Time IoT Data Pipelines

A hands-on demo for the Python meetup. We'll go from "what is MQTT?" to a live multi-source weather dashboard in four progressive steps.

---

## What We're Building

```
[OpenWeatherMap API] ──► [MQTT Broker] ──► [Unified Dashboard]
[Local Weather Station] ──►      ▲
[Meshtastic Mesh Radio] ──►      │
                                 └── (any subscriber can tap in)
```

MQTT is a lightweight publish/subscribe protocol used everywhere in IoT — Home Assistant, AWS IoT Core, factory sensors, emergency mesh networks. The broker is the hub: publishers send data to *topics*, subscribers listen to topics. They never talk directly to each other.

---

## Setup

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/)

```bash
# Clone and install dependencies
git clone <this-repo>
cd mqtt-demo
uv sync

# Copy the config template
cp .env.example .env
```

Edit `.env` and add your [OpenWeatherMap API key](https://openweathermap.org/api) (free tier is fine):

```env
OPENWEATHER_API_KEY=your_key_here
MQTT_BROKER=test.mosquitto.org
MQTT_PORT=1883
MQTT_TOPIC_PREFIX=meetup/weather
```

---

## Demo 1 — Hello, MQTT

**Concept:** Publish/subscribe basics on a public test broker.

Open two terminals:

```bash
# Terminal 1: start listening
uv run demo1_hello_mqtt.py --mode subscribe

# Terminal 2: send messages
uv run demo1_hello_mqtt.py --mode publish
```

Watch Terminal 1 receive the messages as they arrive. The publisher and subscriber don't know about each other — they only know about the broker and the topic name.

**What to notice:**
- The subscriber starts before the publisher, yet receives all messages
- Topic: `meetup/weather/test` — hierarchical, like a file path
- Connection goes to `test.mosquitto.org` — a public broker, no auth needed

---

## Demo 2 — Cloud Weather Bridge

**Concept:** The *bridge pattern* — translate a REST API into a live MQTT stream.

```bash
uv run demo2_cloud_weather.py
```

This polls OpenWeatherMap every 60 seconds for Salt Lake City, Denver, and Las Vegas, then publishes each reading to individual topics:

```
meetup/weather/salt_lake_city/temperature
meetup/weather/salt_lake_city/humidity
meetup/weather/denver/temperature
...
```

**What to notice:**
- One publisher, many topics — subscribers can choose which cities/fields they care about
- The REST API has no idea MQTT exists; the bridge script is the translator
- Any MQTT client in the room can subscribe and see the same live data

---

## Demo 3 — Self-Hosted Broker + Local Sensor

**Concept:** Run your own broker. Simulate a sensor. Build a live dashboard.

First, start a local Mosquitto broker:

```bash
# Docker (easiest)
docker run -it -p 1883:1883 eclipse-mosquitto

# Or Homebrew
brew install mosquitto && mosquitto
```

Then open two more terminals:

```bash
# Terminal 1: simulated weather station (publisher)
uv run demo3_self_hosted/server.py

# Terminal 2: live dashboard (subscriber)
uv run demo3_self_hosted/subscriber.py
```

The server publishes realistic temperature/humidity data with natural-looking variation (sine wave + noise). The subscriber renders a live-updating terminal dashboard.

**What to notice:**
- The subscriber uses the wildcard topic `home/weather/#` — it catches everything under that prefix
- You own the broker: no data leaves your machine
- The dashboard updates in-place using `rich` — no web server, no browser

---

## Demo 4 — Full Pipeline

**Concept:** Multiple publishers, one broker, one dashboard — this is the MQTT payoff.

You need three terminals running simultaneously:

```bash
# Terminal 1: local simulated sensor (from Demo 3)
uv run demo3_self_hosted/server.py

# Terminal 2: cloud weather bridge (from Demo 2)
uv run demo2_cloud_weather.py

# Terminal 3: unified dashboard
uv run demo4_pipeline.py
```

The dashboard shows cloud data and local sensor data side-by-side, all sourced from the same broker.

**What to notice:**
- The two publishers don't know about each other or the dashboard
- Adding a new data source means writing one new publisher — nothing else changes
- This is how production IoT systems work: sensors, cloud APIs, and dashboards are fully decoupled

---

## Bonus — Meshtastic Mesh Radio

**Hardware required:** Meshtastic LoRa device + BME280 sensor (I2C)

```bash
uv run bonus_meshtastic.py --port /dev/ttyUSB0
```

Receives environment telemetry (temperature, humidity, pressure) from mesh network nodes over LoRa radio and publishes it to MQTT — same pipeline, new data source.

**Real-world use case:** Off-grid sensor networks, emergency communications, remote monitoring with no cell coverage.

---

## Core MQTT Concepts

| Concept | What it means |
|---------|---------------|
| **Broker** | Central hub — routes messages between publishers and subscribers |
| **Topic** | Address string, hierarchical: `home/floor1/bedroom/temp` |
| **`+` wildcard** | One level: `home/+/bedroom/temp` matches any floor |
| **`#` wildcard** | All remaining levels: `home/#` matches everything under home |
| **QoS 0** | Fire-and-forget — fastest, no delivery guarantee |
| **QoS 1** | At-least-once — retried until acknowledged |
| **QoS 2** | Exactly-once — slowest, guaranteed no duplicates |
| **Retain** | Broker stores the last message; new subscribers get it immediately |

---

## Why MQTT Instead of HTTP?

- **Push vs. pull:** Subscribers receive data instantly; no polling loop required
- **Always-on connection:** ~2x smaller packet overhead than HTTP
- **Fan-out built in:** One publish reaches thousands of subscribers simultaneously
- **Decoupled:** Publishers and subscribers are independent — add or remove either without changing the other

---

## Project Structure

```
mqtt-demo/
├── demo1_hello_mqtt.py        # Basic pub/sub (~88 lines)
├── demo2_cloud_weather.py     # Cloud API → MQTT bridge (~162 lines)
├── demo3_self_hosted/
│   ├── server.py              # Simulated weather station (~79 lines)
│   └── subscriber.py          # Live terminal dashboard (~93 lines)
├── demo4_pipeline.py          # Unified multi-source dashboard (~133 lines)
├── bonus_meshtastic.py        # Meshtastic mesh → MQTT (~159 lines)
├── mqtt_weather_meetup.md     # Full theory, discussion prompts, references
├── pyproject.toml             # Dependencies (managed by uv)
└── .env.example               # Config template
