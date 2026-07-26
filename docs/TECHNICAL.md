# AuraSense — Technical Specification

> This document describes the **target technical design**. For what is built today versus planned,
> see [ROADMAP.md](../ROADMAP.md). Phase 0 (foundation) is complete; ML pipelines and firmware are
> Phase 1–2.

---

## 1. System Summary

AuraSense addresses structural gaps in smart-home safety by shifting from reactive, rule-based cloud
automation to ambient, edge-native multi-sensor fusion. The system processes electrical, acoustic,
spatial, and atmospheric telemetry at the edge to identify unseen home failures (thermal breakdowns,
insulation degradation, water-pipe failures, structural falls, gas anomalies) while maintaining
data privacy — no video, no raw audio, and inference on-device.

---

## 2. Embedded Hardware & Firmware Architecture

- **Sensor nodes:** Espressif ESP32-S3 (Xtensa dual-core 32-bit LX7, vector extensions for TinyML
  acceleration).
- **Transceivers:** Wi-Fi / BLE 5.0 with local Thread/Matter mesh routing.
- **Micro-sensors:**
  - *Acoustic:* I2S MEMS microphones emitting quantized log-mel feature vectors.
  - *Spatial radar:* 60 GHz mmWave radar (Infineon BGT60 series) processing Doppler point-cloud
    clusters for non-optical fall verification.
  - *Environmental:* BME680 measuring IAQ, VOCs, atmospheric pressure, and thermal drift.
- **Central hub:** Raspberry Pi 5 (8 GB) or NVIDIA Jetson Orin Nano running a container-optimized
  Linux image (Ubuntu Server LTS base).

> **Current status:** node firmware is Phase 2. Today, the [`tools/sim`](../tools/sim) device
> simulator publishes the same schema-valid MQTT feature vectors that real nodes will emit, so the
> hub pipeline is exercised end-to-end without hardware.

---

## 3. Edge ML Pipelines & Algorithmic Specification

### A. Non-Intrusive Load Monitoring (NILM)
- **Input:** high-rate AC current/voltage waveform from clamp-on CT sensors.
- **Model:** sequence-to-point temporal convolutional network (TCNN) / transformer.
- **Task:** map whole-house aggregated active/reactive power to individual appliance operational
  states (e.g. a refrigerator compressor degradation cycle).

### B. On-Node Acoustic Classification
- **Pipeline:** distilled YAMNet topology, pruned and quantized to INT8.
- **Processing:** PCM audio → 64-band log-mel spectrograms; emits categorical event tokens over
  local MQTT. No raw audio is logged or streamed.

### C. Behavioral Anomaly Detection
- **Architecture:** combined isolation-forest and convolutional-autoencoder models over short- and
  long-term time-series windows in TimescaleDB.
- **Function:** learn regular household daily-activity baselines and quantify divergence scores
  (e.g. continuous low-level water flow at 3:00 AM).

### D. Local RAG Diagnostic Agent
- **Model:** quantized 4-bit ONNX runtimes of small-parameter LLMs (Phi-3-mini / Llama 3.2 1B).
- **Integration:** natural-language queries against the local SQL / time-series databases return
  grounded diagnostic explanations without cloud APIs.

> **Current status:** the pipelines above run as instrumented stand-ins that exercise the full data
> path (ingest → detect → event → API). Phase 1 replaces them with trained ONNX/TFLite models —
> stages M1–M5 in [ROADMAP.md](../ROADMAP.md).

---

## 4. Data & Privacy Model

- Nodes publish **feature vectors only** (MQTT topic `aurasense/nodes/{node_id}/{type}`), validated
  against the Pydantic contracts in [`shared/types`](../shared/types).
- Time-series and events are stored locally in TimescaleDB, with compression + retention lifecycle
  policies so local disk does not grow unbounded.
- The REST/WebSocket API requires a per-home pairing token (see `hub/services/api/security.py`);
  the cloud is used only for optional push notifications and encrypted backups.

---

## 5. Commercial Viability & Target Markets

- **Insurance telematics:** proactive risk alerts (water damage, electrical fires) integrated with
  home-insurance providers to mitigate high-cost claims.
- **Dignified elder care:** high-accuracy fall and activity tracking without intrusive optical
  cameras in living spaces.
- **Enterprise utilities:** granular demand-response energy telemetry for regional grid management.
