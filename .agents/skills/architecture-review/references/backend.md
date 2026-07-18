# Backend / Hub Subsystem Conventions — AuraSense

## Runtime
- **Platform**: Raspberry Pi 5 (or Jetson Orin Nano for vision)
- **Language**: Python 3.11+
- **Framework**: FastAPI (REST + WebSocket endpoints)
- **Process manager**: systemd services

## Services (each a separate systemd unit)
| Service | Responsibility |
|---|---|
| `mqtt-broker` | Mosquitto; local MQTT bus for sensor nodes |
| `ingestion` | Subscribes to `aurasense/nodes/#`, validates, writes to TimescaleDB |
| `inference` | Pulls recent windows from DB, runs ML models, writes events to `events` table |
| `api` | FastAPI — serves mobile app and dashboard (REST + WebSocket) |
| `ota-manager` | Manages firmware update commands to nodes |
| `llm-assistant` | Quantized on-device LLM (Phi-3-mini / Llama 3.2 1B) for conversational queries |

## Database
- **Engine**: TimescaleDB (PostgreSQL extension)
- **Hypertables**: `sensor_readings`, `events`, `anomaly_scores`
- **Schema migrations**: Alembic; always add migrations, never alter tables manually.

## API conventions
- **Base path**: `/api/v1/`
- **Auth**: JWT bearer token (issued at pairing time; no cloud auth required for LAN use)
- **Error format**:
  ```json
  { "error": { "code": "ERR_CODE", "message": "Human readable", "detail": {} } }
  ```
- **Success format**:
  ```json
  { "data": {...}, "meta": { "ts": 1720000000 } }
  ```
- **WebSocket**: `/ws/v1/events` — pushes `EventPayload` JSON on new events

## Shared types
- All sensor payload types defined in `shared/types/sensor_payload.py`
- All API response types defined in `shared/types/api_types.py`
- Mobile and backend MUST use the same type definitions (mobile reads from `shared/` via git submodule or codegen)

## Logging
- Structured JSON logs via `structlog`
- Log level controlled by `LOG_LEVEL` env var
- Never log raw sensor data; log event IDs and metadata only
