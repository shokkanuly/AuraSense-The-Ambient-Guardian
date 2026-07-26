# AuraSense — Edge-AI Ambient Guardian

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Architecture: Edge-First](https://img.shields.io/badge/Architecture-Edge--First-blue.svg)]()
[![Status: Active Development](https://img.shields.io/badge/Status-Active--Development-brightgreen.svg)]()
[![CI](https://github.com/shokkanuly/AuraSense-The-Ambient-Guardian/actions/workflows/ci.yml/badge.svg)](https://github.com/shokkanuly/AuraSense-The-Ambient-Guardian/actions/workflows/ci.yml)

> **AuraSense** is a privacy-first, multi-sensor ambient intelligence system. By fusing whole-home energy disaggregation (NILM), on-node acoustic classification, mmWave radar spatial tracking, and environmental gas telemetry, it models household "normal" and flags anomalies — a failing fridge, a hidden leak, an intrusion, an elderly parent's fall — **without cloud cameras or raw audio streams**. All AI runs on the edge; only labels and features leave a node, never video or audio.

---

## 📌 Project Status

Development follows a staged plan in **[ROADMAP.md](ROADMAP.md)**.

| Phase | Scope | Status |
| :--- | :--- | :--- |
| **0 · Foundation** | Correctness, pairing auth, device simulator + CI, real data endpoints + DB lifecycle policies | ✅ **Complete (F1–F4)** |
| **1 · Real ML** | Trained NILM / fall / acoustic / anomaly models; ONNX/TFLite edge inference; grounded LLM | 🚧 Next |
| **2 · Device + Mobile** | ESP32-S3 firmware, provisioning/pairing, OTA, Flutter app | ⬜ Planned |
| **3 · Research** | Cross-home NILM generalization, sensor fusion, federated learning | ⬜ Planned |

> **What runs today:** the hub backend (MQTT ingestion → TimescaleDB → inference → REST/WebSocket API with pairing auth), a hardware-free device simulator, a live web console, and a CI-tested Python suite. The ML pipelines described below are the **target designs**; in Phase 0 they run as instrumented simulations and are replaced with trained models in Phase 1.

---

## 🏗 System Architecture

```
                        [ Main Electrical Feed ]
                                   │
                            (CT Clamp Sensor)
                                   │
   ┌───────────────────┬──────────┴──────────┬───────────────────┐
[ ESP32-S3 Node 1 ] [ ESP32-S3 Node 2 ] [ ESP32-S3 Node N ]   (Sub-meter Node)
 (Acoustic / Env)    (mmWave Fall Radar)  (Power / Misc)
   └───────────────────┴──────────┬──────────┴───────────────────┘
                                   │
                 (Local MQTT over Thread / Wi-Fi)
                                   ▼
                    ┌─────────────────────────────┐
                    │      AuraSense Local Hub     │
                    │     (RPi 5 / Jetson Nano)    │
                    ├─────────────────────────────┤
                    │  • MQTT Broker (Mosquitto)   │
                    │  • TimescaleDB               │
                    │  • Inference engine (NILM,   │
                    │    fall, anomaly)            │
                    │  • Local quantized LLM (RAG) │
                    └───────────────┬──────────────┘
                                    │
                    (Local LAN / encrypted sync)
                     ┌──────────────┴──────────────┐
                     ▼                              ▼
            ┌──────────────────┐        ┌────────────────────────┐
            │  Web Console     │        │  Flutter Mobile App     │
            │  (built today)   │        │  (planned — Phase 2)    │
            └──────────────────┘        └────────────────────────┘
```

---

## 🛰 Core Sensor Stack (target hardware)

| Sensor Type | Target Hardware | Functionality | ML Pipeline / Engine |
| :--- | :--- | :--- | :--- |
| **Current/Voltage** | Clamp-on CT sensor | Whole-home power disaggregation | Sequence-to-Point CNN (NILM) |
| **Presence & Motion** | 60 GHz mmWave radar (Infineon BGT60) | Camera-free fall & respiration tracking | Point-cloud LSTM |
| **Acoustics** | MEMS microphone | Glass break, running water, smoke alarms | INT8 YAMNet-distilled CNN |
| **Environment** | BME680 | Temp, humidity, pressure, VOC gas | Autoencoder anomaly scoring |

Nodes publish compact **feature vectors** over MQTT (topic `aurasense/nodes/{node_id}/{type}`) — never raw streams. See [`shared/types/sensor_payload.py`](shared/types/sensor_payload.py) for the payload contracts.

---

## 🧠 Machine Learning Engine

> Status: designs below are the Phase 1 target. Today the hub runs instrumented stand-ins that exercise the full data path (ingest → detect → event → API) so the models can be dropped in without plumbing changes.

### 1. Non-Intrusive Load Monitoring (NILM)
A sequence-to-point model maps a sliding window of whole-home aggregate power to a mid-point per-appliance load:

$$\mathcal{L}_{S2P} = \frac{1}{N} \sum_{i=1}^{N} \left( y_i - f_{\theta}(X_{i-\tau : i+\tau}) \right)^2$$

where $X_{i-\tau : i+\tau}$ is the aggregate-power window and $y_i$ the mid-point appliance load. Disaggregation is persisted to `energy_disaggregation` and served at `GET /api/v1/energy`.

### 2. TinyML Acoustic Classifier
* **Features:** 64-band log-mel spectrograms computed on-device.
* **Runtime:** TFLite Micro running an INT8-quantized CNN on the ESP32-S3.
* **Privacy:** audio buffers are overwritten immediately; only labels (`running_water`, `glass_break`, …) leave the node.

### 3. Behavioral Anomaly Detection
Isolation-forest + autoencoder models learn the household's daily baseline and score divergence (e.g. continuous low-level water flow at 3 a.m.). Scores are served at `GET /api/v1/anomaly-scores`.

### 4. Local Conversational Diagnostics
A local RAG pipeline links a quantized **Phi-3-mini / Llama 3.2 1B** model to the hub's TimescaleDB history, answering questions like *"why was my bill high this month?"* with grounded, on-device answers — no cloud APIs.

See **[docs/TECHNICAL.md](docs/TECHNICAL.md)** for the full technical specification.

---

## 🗂 Repository Layout

```
.
├── hub/                       # Core hub backend (Linux/macOS; target RPi 5 / Jetson)
│   ├── services/
│   │   ├── api/               # FastAPI REST + WebSocket API
│   │   │   ├── main.py        # app, lifespan, CORS, router wiring
│   │   │   ├── security.py    # pairing-code → JWT auth
│   │   │   └── routers/       # nodes, events, energy, assistant, pairing, websocket
│   │   ├── ingestion.py       # MQTT → TimescaleDB
│   │   ├── inference.py       # NILM / fall / anomaly engine
│   │   └── llm_assistant.py   # local RAG assistant
│   ├── db/                    # TimescaleDB schema, init_db.py, migrations/
│   ├── models/registry.json   # ONNX model registry
│   └── config/                # Mosquitto config
├── ml/training/               # Training pipelines: nilm, acoustic, fall_detection, anomaly
├── shared/types/              # Pydantic contracts shared across services
├── dashboard/                 # Web console (TanStack Start + React) — live hub UI
├── tools/sim/                 # Hardware-free device simulator (publishes MQTT feature vectors)
├── tests/                     # pytest suite (hub + simulator + auth + data endpoints)
├── docs/                      # Technical specification & design notes
├── docker-compose.yml         # TimescaleDB + Mosquitto
├── .github/workflows/ci.yml   # CI: schema init → ruff → pytest, + dashboard build
└── ROADMAP.md                 # Staged upgrade plan

# Planned (see ROADMAP.md, Phase 2):
#   firmware/   ESP32-S3 C/IDF sensor-node firmware + TFLite Micro kernels
#   mobile/     Flutter application
```

---

## ⚡ Quickstart

### Prerequisites
* Docker & Docker Compose
* Python 3.12+
* Node.js 20+ (for the web console)

### 1. Bring up infrastructure
```bash
git clone https://github.com/shokkanuly/AuraSense-The-Ambient-Guardian.git
cd AuraSense-The-Ambient-Guardian
docker compose up -d          # TimescaleDB (host port 5434) + Mosquitto (1883)
```
Compose auto-applies the schema on first run. The host DB port is **5434** (not 5432), so services must point at it.

### 2. Python environment
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r hub/requirements.txt -r requirements-dev.txt
export DATABASE_URL=postgresql://postgres:postgres@localhost:5434/aurasense
export MQTT_BROKER=localhost
```
Optional: copy `.env.example` to `.env` and set `AURASENSE_JWT_SECRET` / `AURASENSE_PAIRING_CODE`.

### 3. Run the hub (separate terminals)
```bash
python hub/services/ingestion.py                 # MQTT → TimescaleDB
python hub/services/inference.py                 # NILM / fall / anomaly engine
python -m uvicorn hub.services.api.main:app --port 8000   # REST + WebSocket API
```

### 4. Drive it with the device simulator (no hardware needed)
```bash
python -m tools.sim --scenario fall --duration 20
# scenarios: normal | fall | microwave | water | night
```

### 5. Talk to the API (pairing auth)
```bash
# exchange the pairing code for a token
curl -sX POST localhost:8000/api/v1/pair \
  -H 'content-type: application/json' -d '{"pairing_code":"aurasense-dev"}'

# use the returned access_token
curl localhost:8000/api/v1/events?severity=CRITICAL \
  -H "Authorization: Bearer <token>"
```

### 6. Web console
```bash
cd dashboard
npm install
npm run dev        # http://localhost:8080/console
```

---

## 🧪 Testing

```bash
pytest                 # hub + simulator + auth + data-endpoint suite
ruff check .           # lint
```
The suite spins its integration tests against the docker-compose TimescaleDB (and skips cleanly if it isn't running). CI runs the same on every push — see [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## 🗺 Roadmap

Foundation (Phase 0) is complete. Next is Phase 1 — replacing the simulated ML with trained NILM / fall / acoustic / anomaly models and real ONNX/TFLite edge inference. Full plan, with per-stage goals and verification, in **[ROADMAP.md](ROADMAP.md)**.

---

## 🛡 License

Intended to be distributed under the **MIT License**. A `LICENSE` file has not been added yet — see the roadmap discussion or open a PR to add it.
