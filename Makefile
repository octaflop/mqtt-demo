UF2_BOOTLOADER ?= /Volumes/RPI-RP2
CIRCUITPY       ?= /Volumes/CIRCUITPY

# CircuitPython 9.x UF2 for the KB2040
CP_VERSION  ?= 9.2.1
CP_UF2_URL  ?= https://downloads.circuitpython.org/bin/adafruit_kb2040/en_US/adafruit-circuitpython-adafruit_kb2040-en_US-$(CP_VERSION).uf2
CP_UF2_FILE ?= /tmp/circuitpython-kb2040-$(CP_VERSION).uf2

.PHONY: flash-kb2040 copy-kb2040 libs-kb2040 watch-kb2040 check-kb2040

## ── One-time setup ───────────────────────────────────────────────────────────

## Step 1: Flash CircuitPython firmware (double-tap RESET first → RPI-RP2 mounts)
flash-kb2040:
	@test -d $(UF2_BOOTLOADER) || { \
		echo "Error: $(UF2_BOOTLOADER) not found."; \
		echo "Double-tap the RESET button to enter bootloader mode."; \
		exit 1; \
	}
	@test -f $(CP_UF2_FILE) || { \
		echo "Downloading CircuitPython $(CP_VERSION) for KB2040…"; \
		curl -L -o $(CP_UF2_FILE) $(CP_UF2_URL); \
	}
	cp $(CP_UF2_FILE) $(UF2_BOOTLOADER)/
	@echo "Flashed! Board will reboot → wait for CIRCUITPY to mount, then run: make libs-kb2040"

## Step 2: Install required CircuitPython libraries (single RESET tap → CIRCUITPY mounts)
libs-kb2040:
	@test -d $(CIRCUITPY) || { \
		echo "Error: $(CIRCUITPY) not found."; \
		echo "Single-tap RESET (or wait after flashing) for CircuitPython mode."; \
		exit 1; \
	}
	uvx circup --path $(CIRCUITPY) install neopixel

## ── Development ──────────────────────────────────────────────────────────────

## Copy code.py to the board (CIRCUITPY must be mounted — single RESET tap)
copy-kb2040:
	@test -d $(CIRCUITPY) || { \
		echo "Error: $(CIRCUITPY) not found."; \
		echo "Single-tap RESET for CircuitPython mode. Need to flash first? Run: make flash-kb2040"; \
		exit 1; \
	}
	cp kb2040/code.py $(CIRCUITPY)/code.py
	@echo "Copied kb2040/code.py → $(CIRCUITPY)/code.py"

## Watch kb2040/code.py and auto-copy on save (requires fswatch: brew install fswatch)
watch-kb2040:
	@test -d $(CIRCUITPY) || { echo "Error: $(CIRCUITPY) not found."; exit 1; }
	@command -v fswatch >/dev/null || { echo "Error: fswatch not found. Install with: brew install fswatch"; exit 1; }
	@echo "Watching kb2040/code.py — saving will auto-copy to $(CIRCUITPY)/code.py"
	@fswatch -o kb2040/code.py | xargs -I{} sh -c 'cp kb2040/code.py $(CIRCUITPY)/code.py && echo "Copied at $$(date +%H:%M:%S)"'

## Show what's currently on the board
check-kb2040:
	@test -d $(CIRCUITPY) || { echo "Error: $(CIRCUITPY) not found."; exit 1; }
	@echo "=== $(CIRCUITPY)/code.py ===" && cat $(CIRCUITPY)/code.py
	@echo "" && echo "=== $(CIRCUITPY)/lib/ ===" && ls $(CIRCUITPY)/lib/ 2>/dev/null || echo "(empty)"
