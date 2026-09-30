# AuraSense — Arduino Hardware Foundation

This directory contains the production-ready Arduino firmware for **AuraSense Ambient Guardian Nodes**. It enables building and connecting physical sensing nodes to the AuraSense local hub using any **ESP32** or **ESP32-S3** microcontroller.

---

## Architecture & Subsystem Contract

The Arduino node strictly adheres to the AuraSense hardware contract:

1. **Transport**: MQTT over Wi-Fi (QoS 1).
2. **Topic Convention**: `aurasense/nodes/{node_id}/{sensor_type}`
3. **Payload Envelope**: Compact JSON feature vectors conforming to `shared/types/sensor_payload.py`:
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
4. **Time Synchronization**: Automatically synchronizes with NTP servers upon Wi-Fi connection so UTC timestamps (`ts`) match TimescaleDB hypertable requirements.
5. **Auto-Discovery**: The Hub's `hub/services/ingestion.py` automatically registers the node upon first reception of MQTT packets.

---

## Hardware Bill of Materials (BOM)

| Component | Recommended Model | Interface | Purpose |
|---|---|---|---|
| **MCU Board** | ESP32-WROOM-32 or ESP32-S3-DevKitC-1 | Wi-Fi + BLE | Dual-core processing & networking |
| **Environmental** | BME680 (or BME280) | I2C (SDA: 21, SCL: 22) | Temperature, Humidity, Pressure, VOC / Air Quality |
| **Presence / Fall** | Hi-Link HLK-LD2410 (24 GHz mmWave radar) | Digital GPIO (19, 18) | Privacy-safe presence, respiration, fall detection |
| **Power Pulse** | HW-511 phototransistor module / TEMT6000 | Digital GPIO (4) with interrupt | Zero-risk optical pulse reader on utility meter LED |
| **Acoustic Node** | INMP441 MEMS microphone | I2S | Acoustic anomaly classification (features only) |

---

## Pinout Map (ESP32 Standard)

```
       ESP32 DevKit
       ┌───────────┐
3.3V  ─┤ 3V3       ├── 3.3V Rail (Power to BME680, LD2410, Optical Sensor)
GND   ─┤ GND       ├── Ground Rail
GPIO21─┤ SDA       ├── BME680 SDA (I2C Data)
GPIO22─┤ SCL       ├── BME680 SCL (I2C Clock)
GPIO19─┤ IN        ├── HLK-LD2410 Radar (OUT / Presence signal)
GPIO18─┤ IN        ├── HLK-LD2410 Radar (Alert / Rapid Motion signal)
GPIO4 ─┤ IN (ISR)  ├── Optical Pulse Sensor Digital OUT
GPIO2 ─┤ LED       ├── Onboard Status LED (Blinks during connection)
       └───────────┘
```

---

## Setup & Flashing Guide

### Method A: Arduino IDE

1. Open **Arduino IDE** (v2.x recommended).
2. Install ESP32 Board Support:
   - Go to `Settings` -> `Additional Boards Manager URLs`:
     `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Open `Boards Manager`, search for **esp32** by Espressif Systems and install.
3. Install Required Library:
   - Open `Library Manager` (`Ctrl+Shift+I` / `Cmd+Shift+I`).
   - Search for **PubSubClient** (by Nick O'Leary) and install.
4. Open sketch:
   - Open `firmware/arduino/AuraSenseNode/AuraSenseNode.ino`.
5. Configure `config.h`:
   - Set `WIFI_SSID` and `WIFI_PASSWORD`.
   - Set `MQTT_BROKER_HOST` to your Hub machine's local IP (e.g. `192.168.1.100`).
   - Adjust `NODE_ID` (e.g. `node_kitchen`, `node_living_room`).
   - Enable/disable sensor flags (`ENABLE_ENV_SENSOR`, `ENABLE_MOTION_SENSOR`, etc.).
6. Select Board (`ESP32 Dev Module`) and Port, then click **Upload**.

---

### Method B: PlatformIO (`platformio.ini`)

If using VS Code with PlatformIO, create a `platformio.ini` in this directory:

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps =
    knolleary/PubSubClient@^2.8
```

---

## Bench Testing & Serial Commands

The firmware includes interactive workbench testing tools. Open the Serial Monitor at **115200 baud**:

- Press **`s`**: Prints instant node status, connection health, and UTC epoch.
- Press **`f`**: Triggers a simulated **Fall Event** (`fall_detected: true`) to test the Hub's **Cross-Sensor Consensus Matrix**.
- Press **`g`**: Triggers a simulated **Glass Break** acoustic event.
- Press **`v`**: Simulates elevated VOC reading for air hazard testing.

---

## End-to-End Verification

1. Start AuraSense Hub services:
   ```bash
   docker compose up -d          # Starts TimescaleDB & Mosquitto
   python hub/services/ingestion.py
   python hub/services/api/main.py
   ```
2. Power on your ESP32 board.
3. Check the Ingestion terminal:
   ```
   [MQTT TX] aurasense/nodes/node_living_room/env -> {"node_id":"node_living_room","ts":1720000010,"type":"env",...}
   [ingestion-service] Ingested env reading for node node_living_room at ts 1720000010
   ```
4. Check the Dashboard (`http://localhost:3000` or `http://localhost:5173`):
   - The node appears under **Active Nodes** with status `ONLINE`.
   - Live environmental graphs, presence indicators, and energy metrics update automatically.
