# mimic-glove

A data glove that drives a robotic hand — flex sensors on each finger stream real-time angle data to a live dashboard, which maps them to servo PWM signals on a 3D-printed hand.

Built software-first: the full pipeline runs on a simulator so everything can be developed and demoed without hardware.

---

## Demo

> *(GIF coming once hardware arrives)*

Live dashboard showing the SVG hand responding to simulated flex sensor data, servo PWM dials updating in real time, and gesture recording/playback.

---

## Features

- **Real-time pipeline** — 50 Hz sensor stream → angle parser → servo controller → live dashboard
- **SVG hand visualization** — animated hand that bends finger-by-finger as data comes in
- **Gesture recording & playback** — capture named poses to JSON, replay at original timing
- **Calibration system** — per-finger flat/fist ADC capture, persisted to disk
- **Hardware-ready** — swap one env var to switch from simulator to real ESP32 glove
- **Binary serial protocol** — 13-byte checksummed packets, defined in both Python and firmware

---

## Architecture

```
┌─────────────────────┐        serial (USB)       ┌──────────────────────┐
│  ESP32 on glove     │  ──────────────────────►  │  Host PC pipeline    │
│  5x flex sensors    │    13-byte binary packets  │                      │
│  50 Hz ADC sample   │                            │  stream_reader       │
└─────────────────────┘                            │       ↓              │
                                                   │  parser + calibration│
         ┌─────────────────────────────────────────│       ↓              │
         │                                         │  servo_controller    │
         ▼                                         └──────────────────────┘
┌─────────────────────┐                                      │
│  3D printed hand    │   ◄──────────────────────────────────┘
│  PCA9685 + 5 servos │        PWM ticks (simulated)
└─────────────────────┘
```

The simulator replaces the ESP32 layer during development — everything downstream is identical.

---

## Quick Start

**Requirements:** Python 3.10+

```bash
git clone https://github.com/cliverafiq/mimic-glove.git
cd mimic-glove
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

---

## Switching to real hardware

```bash
GLOVE_PORT=/dev/tty.usbserial-0001 GLOVE_SOURCE=hardware \
  venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8000
```

That's the only change. Parser, calibration, dashboard, and recording all stay the same.

---

## Hardware Bill of Materials

| Component | Purpose | ~Cost |
|---|---|---|
| ESP32 dev board | Microcontroller — reads sensors, streams serial | $5–10 |
| 5× flex sensors (Spectra Symbol) | Finger bend detection | $10 each |
| 5× 10kΩ resistors | Voltage dividers for flex sensors | <$1 |
| LiPo battery + TP4056 module | Wireless power | $10 |
| InMoov hand (3D printed) | Robotic hand structure | filament cost |
| 5× MG90S micro servos | Finger actuation via tendons | $3–5 each |
| PCA9685 servo driver | I²C PWM controller for all servos | $5 |
| Second ESP32 or Arduino | Drives PCA9685 on the hand side | $5–10 |
| 5V 3A power supply | Powers servos | $10 |

**Total: ~$100–130 USD**

---

## Wiring — Glove (ESP32)

```
3.3V ──── flex sensor ──── GPIO pin ──── 10kΩ ──── GND

GPIO 36 (VP) — thumb
GPIO 39 (VN) — index
GPIO 34      — middle
GPIO 35      — ring
GPIO 32      — pinky
```

All pins are on ADC1, which stays functional alongside WiFi/BLE.

---

## Project Structure

```
mimic-glove/
├── firmware/
│   └── glove_firmware.ino     # ESP32 Arduino sketch
├── hardware/
│   ├── protocol.py            # packet encode/decode (shared with firmware)
│   └── serial_reader.py       # drop-in stream() replacement for real hardware
├── simulator/
│   └── glove_simulator.py     # 50 Hz fake ADC stream
├── pipeline/
│   ├── parser.py              # ADC → finger angles
│   ├── servo_controller.py    # angles → PCA9685 PWM ticks
│   ├── gesture_recorder.py    # record/playback
│   └── calibration.py        # per-finger flat/fist calibration
├── server/
│   ├── app.py                 # FastAPI + WebSocket
│   └── static/index.html      # live dashboard
├── gestures/                  # saved gesture JSON files
└── requirements.txt
```

---

## Serial Packet Format

```
Byte  0    : 0xAA  (magic)
Byte  1    : 0xBB  (magic)
Bytes 2-11 : 5 × uint16 big-endian ADC values (thumb → pinky)
Byte  12   : XOR checksum of bytes 2–11
```

13 bytes per packet × 50 Hz = 650 bytes/s — about 7% of a 115200 baud link.

---

## Roadmap

- [ ] Gesture recognition (real-time pose detection)
- [ ] Demo GIF + wiring photos
- [ ] BLE streaming mode (cut the USB cable)
- [ ] 3-joint finger model (15 servos)
