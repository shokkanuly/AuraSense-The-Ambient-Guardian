# AuraSense — System Architecture Evaluation & Arduino Hardware Foundation

## 1. Executive Summary & Core Value Proposition

**AuraSense** is a privacy-first ambient guardian mesh designed to monitor environments (eldercare homes, assisted living, critical facilities, and residences) without visual surveillance.

### The Problem Solved
1. **Surveillance Friction**: Cameras are intrusive and legally or ethically unacceptable in bedrooms, care home suites, bathrooms, and private living quarters.
2. **Alert Fatigue**: Single-sensor alarms (simple noise sensors or threshold detectors) cry wolf and are quickly disabled or muted.

### Architectural Solution
- **Privacy at the Edge**: Sensor nodes process raw data on-device (DSP log-mel features, radar reflection characteristics, optical meter flash intervals) and transmit only compact JSON feature vectors. **No raw audio or video streams ever leave the node.**
- **Cross-Sensor Consensus Matrix**: High-severity alerts require secondary verification across different sensor domains within timed action windows before escalating.
- **Local Sovereignty**: All processing, storage (TimescaleDB), inference, and API serving reside on a local hub (Raspberry Pi 5 or local server) with zero compulsory cloud dependencies.

---

## 2. Comprehensive System Architecture Audit

```
┌─────────────────────────────────┐
│ ESP32 / ESP32-S3 Edge Nodes     │
│ (BME680, mmWave, Optical, Audio)│
└───────────────┬─────────────────┘
                │ MQTT (QoS 1) - JSON Feature Vectors
                ▼
┌─────────────────────────────────────────────────────┐
│ AuraSense Local Hub (RPi 5 / Local Workstation)     │
│  ├── Mosquitto MQTT Broker (port 1883)              │
│  ├── Ingestion Worker (Pydantic schema validation)  │
│  ├── TimescaleDB (Hypertables & Continuous Aggs)    │
│  ├── Cross-Sensor Consensus Matrix Engine           │
│  ├── Edge ML Inference (ONNX Runtime / Fallbacks)   │
│  └── FastAPI (REST + WebSockets on /api/v1)         │
└───────────────┬─────────────────────────────────────┘
                │ WebSocket / REST
                ▼
┌─────────────────────────────────┐
│ Real-Time React / Vite Console  │
│ (Live metrics, alerts & triage) │
└─────────────────────────────────┘
```

### Component Analysis

| Subsystem | File Location | Purpose & Implementation | Architectural Assessment |
|---|---|---|---|
| **Edge Hardware / Firmware** | `firmware/esp32s3/`, `firmware/arduino/` | Microcontroller firmware for ESP32 and ESP32-S3 boards. | Dual-core task separation (ESP-IDF) and standard Arduino framework for rapid deployment. Transmits compact JSON feature vectors over MQTT (QoS 1). |
| **Ingestion Pipeline** | `hub/services/ingestion.py` | Asynchronously ingests MQTT messages into TimescaleDB. | Validates strictly against Pydantic models (`shared/types/sensor_payload.py`). Upserts node health and inserts hypertable records cleanly. |
| **Consensus Matrix** | `hub/services/consensus.py` | Correlates multi-sensor telemetry to prevent false positives. | **Core Innovation**: Eliminates single-sensor false alarms by cross-verifying signals (e.g. radar fall + acoustic silence + adjacent node immobility; VOC gas spike + stove power draw). |
| **Edge ML Inference** | `hub/services/inference.py`, `ml/training/` | ONNX runtime inference for NILM, acoustic events, and anomaly scoring. | Shipped with trained `nilm_v1_0.onnx` model. Includes graceful simulation fallback when ONNX runtime is absent. |
| **Data Layer** | `hub/db/schema.sql` | TimescaleDB hypertable schema, continuous aggregates, and retention policies. | Optimized for high-throughput time-series writes and continuous rollups for 1-minute and 1-hour windows. |
| **API & Security** | `hub/services/api/` | FastAPI REST and WebSocket event streaming. | Clean modular routers for `/nodes`, `/events`, `/assistant`, and real-time WebSockets. |
| **Console Dashboard** | `dashboard/` | Modern TanStack Router / React console with dark aesthetic. | Real-time WebSocket event delivery, live telemetry charts, node status badges, and incident triage modal. |

---

## 3. Hardware Foundation & Arduino Implementation

To make building and deploying physical nodes straightforward, a complete Arduino firmware framework is implemented under `firmware/arduino/AuraSenseNode/`.

### Subsystem Contract Compliance
- **Transport**: MQTT over Wi-Fi with QoS 1.
- **Topic Convention**: `aurasense/nodes/{node_id}/{sensor_type}`
- **Payload Envelope**:
  ```json
  {
    "node_id": "node_living_room",
    "ts": 1720000000,
    "type": "env",
    "features": {
      "temp_c": 22.50,
      "humidity_pct": 46.00,
      "pressure_hpa": 1013.25,
      "voc_iaq": 45.00
    }
  }
  ```
- **NTP Time Synchronization**: Connects to SNTP upon Wi-Fi handshake to guarantee accurate UTC epoch seconds (`ts`), ensuring proper partitioning in TimescaleDB hypertables.
- **Graceful Hardware Fallback**: Includes simulated drift fallbacks for sensors not yet physically attached, allowing full end-to-end network and dashboard verification on day one.

---

## 4. Hardware Bill of Materials (BOM) & Pinout

| Sensor Domain | Suggested Hardware Module | Interface | ESP32 Pin Mapping |
|---|---|---|---|
| **Microcontroller** | ESP32-WROOM-32 or ESP32-S3 DevKit | Wi-Fi / BLE | Standard 3.3V & GND rails |
| **Environmental** | Bosch BME680 (or BME280) | I2C | SDA: `GPIO 21`, SCL: `GPIO 22` |
| **Radar / Presence** | Hi-Link HLK-LD2410 (24 GHz mmWave) | Digital Input | Out: `GPIO 19`, Alert: `GPIO 18` |
| **Power Pulse** | HW-511 Phototransistor / TEMT6000 | Digital Interrupt | Signal: `GPIO 4` |
| **Acoustic Node** | INMP441 MEMS Microphone | I2S | SCK: `GPIO 14`, WS: `GPIO 15`, SD: `GPIO 32` |

---

## 5. Firmware Modules in `firmware/arduino/AuraSenseNode/`

1. **`config.h`**: Central definitions for Wi-Fi SSID/password, Hub broker IP, node ID, sensor enable toggles, and GPIO pins.
2. **`PayloadFormatter.h` / `.cpp`**: High-performance JSON serializer matching `shared/types/sensor_payload.py`.
3. **`NetworkManager.h` / `.cpp`**: Non-blocking Wi-Fi auto-reconnect, NTP synchronization, and MQTT connection with Last Will & Testament (LWT).
4. **`SensorEnv.h` / `.cpp`**: BME680/BME280 I2C scanning, environmental feature sampling, and simulated drift fallback.
5. **`SensorMotion.h` / `.cpp`**: mmWave radar digital pulse reader, presence duration tracking, and test fall event trigger.
6. **`SensorOpticalPulse.h` / `.cpp`**: Zero-risk optical pulse interrupt counter with hardware debouncing and instantaneous active Wattage computation.
7. **`SensorAudio.h` / `.cpp`**: Acoustic feature classifier interface emitting structured event labels and confidence scores.
8. **`AuraSenseNode.ino`**: Main coordinating sketch with non-blocking timers and interactive workbench serial console commands (`f`, `g`, `s`).

---

## 6. Workbench Testing & Verification

1. Start the AuraSense Hub services:
   ```bash
   docker compose up -d
   python hub/services/ingestion.py
   python -m uvicorn hub.services.api.main:app --port 8000
   ```
2. Open `firmware/arduino/AuraSenseNode/AuraSenseNode.ino` in Arduino IDE or PlatformIO.
3. Edit `config.h` with your Wi-Fi credentials and Hub IP.
4. Flash the ESP32 board and open the Serial Monitor (`115200 baud`):
   - **`s`**: Display current connection status and UTC epoch time.
   - **`f`**: Inject a simulated fall trigger to test the Hub's consensus engine.
   - **`g`**: Inject a simulated glass-break acoustic event.
