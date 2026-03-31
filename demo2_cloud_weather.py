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
            "city":         raw["name"],
            "country":      raw["sys"]["country"],
            "temp_f":       round(raw["main"]["temp"], 1),
            "feels_like_f": round(raw["main"]["feels_like"], 1),
            "humidity_pct": raw["main"]["humidity"],
            "pressure_hpa": raw["main"]["pressure"],
            "wind_mph":     round(raw["wind"]["speed"], 1),
            "condition":    raw["weather"][0]["description"],
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "source":       "openweathermap",
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
