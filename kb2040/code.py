"""
KB2040 — CircuitPython MQTT bridge firmware
Runs on the device. Reads analog input + button, streams JSON over USB serial.
The host script (demo5_kb2040.py) picks this up and publishes to MQTT.

Hardware:
  - Built-in NeoPixel (board.NEOPIXEL) — pulses to show it's alive
  - Built-in BOOT button (board.BUTTON) — counts presses
  - A0 — analog input (potentiometer, photocell, or anything 0–3.3 V)

Flash this file to the KB2040 as code.py (drag-and-drop onto the CIRCUITPY drive).
Requires CircuitPython 9.x + the standard Adafruit bundle (neopixel).
"""

import board
import analogio
import digitalio
import neopixel
import json
import time
import supervisor

# ── Hardware setup ────────────────────────────────────────────────────────────

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.05, auto_write=True)

button = digitalio.DigitalInOut(board.BUTTON)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP  # LOW when pressed

adc = analogio.AnalogIn(board.A0)

# ── State ─────────────────────────────────────────────────────────────────────

counter = 0
button_presses = 0
last_button_state = True   # True = released (pulled up)
last_publish = -999.0
PUBLISH_INTERVAL = 1.0     # seconds between JSON lines

# Dim blue heartbeat while idle, green flash on publish
IDLE_COLOR  = (0, 0, 20)
PUB_COLOR   = (0, 40, 0)
OFF         = (0, 0, 0)


def read_voltage() -> float:
    """Convert raw ADC value to volts (0–3.3 V, 16-bit)."""
    return round((adc.value / 65535) * 3.3, 3)


# ── Main loop ─────────────────────────────────────────────────────────────────

pixel[0] = IDLE_COLOR

while True:
    now = time.monotonic()

    # Debounced button edge detection (falling edge = press)
    current = button.value
    if not current and last_button_state:
        button_presses += 1
    last_button_state = current

    if now - last_publish >= PUBLISH_INTERVAL:
        payload = {
            "device":         "kb2040",
            "counter":        counter,
            "voltage_v":      read_voltage(),
            "button_presses": button_presses,
            "uptime_s":       round(now, 1),
        }

        # JSON line → host reads this from serial
        print(json.dumps(payload))

        # Quick green flash so you can see activity on the device
        pixel[0] = PUB_COLOR
        time.sleep(0.05)
        pixel[0] = IDLE_COLOR

        counter += 1
        last_publish = now

    time.sleep(0.02)   # 50 Hz poll — responsive button, low CPU
