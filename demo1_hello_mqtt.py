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
from datetime import datetime, timezone
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
    try:
        payload = json.loads(msg.payload.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        print(f"[red]Bad payload on {msg.topic}[/red]")
        return
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fake_temp_f": round(72.0 + i * 0.5, 1),
        }
        client.publish(TOPIC, json.dumps(payload), qos=1)
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
