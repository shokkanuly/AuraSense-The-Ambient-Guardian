# Hardware Subsystem Conventions — AuraSense

## Sensor Nodes
- **MCU**: ESP32-S3 (BLE + Wi-Fi)
- **Communication protocol to hub**: MQTT over Wi-Fi (primary), BLE advertisement (low-power fallback)
- **Data format**: compact JSON feature vectors — NEVER raw streams
- **Topic schema**: `aurasense/nodes/{node_id}/{sensor_type}` (e.g. `aurasense/nodes/node_01/power`)
- **Payload schema** (all sensor types share this envelope):
  ```json
  { "node_id": "node_01", "ts": 1720000000, "type": "power|audio|motion|env", "features": {...} }
  ```
- **QoS**: MQTT QoS 1 for all feature vectors
- **OTA**: ESP-IDF OTA partition; firmware update triggered by hub via `aurasense/nodes/{node_id}/ota/cmd`

## Power / CT Sensor
- **Sensor**: Clamp-on CT on mains feed
- **Output**: high-rate current/voltage sampled locally, then features extracted on-device before publishing
- **Feature vector keys**: `{ "rms_current": float, "rms_voltage": float, "apparent_power": float, "thd": float }`

## Acoustic Node
- **Sensor**: MEMS microphone
- **Model**: tiny CNN on-device (INT8, TFLite Micro)
- **Output**: label only — `{ "label": "glass_break|smoke_alarm|running_water|none", "confidence": float }`
- **NEVER publish raw audio**

## Presence / Fall (mmWave)
- **Sensor**: Infineon BGT60 60 GHz mmWave radar
- **Output**: `{ "presence": bool, "breathing_rate": float, "fall_detected": bool, "point_cloud_summary": [...] }`

## Environment
- **Sensor**: BME680
- **Output**: `{ "temp_c": float, "humidity_pct": float, "pressure_hpa": float, "voc_iaq": float }`

## Failure modes
- If a node drops off MQTT for >60s, hub marks it `STALE` and raises a connectivity alert to mobile.
- Hub never assumes node is alive; always checks last-seen timestamp before acting on data.

## Boundary to Hub (Software ↔ Hardware)
- Hub subscribes to `aurasense/nodes/#` on Mosquitto broker (running on hub itself).
- Shared type definitions live in `shared/types/sensor_payload.py` — hardware team must not change payload schema without updating this file.
