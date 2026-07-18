# ML / AI Subsystem Conventions — AuraSense

## Model inventory
| Model | Location | Input | Output | Runtime |
|---|---|---|---|---|
| NILM (energy disaggregation) | Hub | power feature window (seq) | per-appliance usage dict | ONNX Runtime |
| Acoustic event classifier | ESP32-S3 node | log-mel spectrogram | label + confidence | TFLite Micro INT8 |
| Behavioral anomaly detector | Hub | activity time-series | anomaly_score float | ONNX Runtime |
| Fall detector (LSTM) | Hub | radar point-cloud time series | fall_prob float | ONNX Runtime |
| On-device LLM assistant | Hub | text prompt + RAG context | text response | llama.cpp / ONNX |

## Model versioning
- Model files live in `hub/models/` as `{model_name}_v{major}_{minor}.onnx`
- Version metadata in `hub/models/registry.json`:
  ```json
  { "nilm": { "version": "1.0", "file": "nilm_v1_0.onnx", "input_schema": "...", "output_schema": "..." } }
  ```
- Inference service loads models by reading `registry.json` — never hardcode filenames

## Input/output contracts
- All model inputs and outputs documented in `shared/types/ml_contracts.py`
- Input: numpy arrays with dtype and shape specified; preprocessing must match training pipeline exactly
- Output: typed dataclasses; never return raw numpy arrays to the API layer

## Training pipeline
- `ml/training/` directory; one subfolder per model
- Datasets stored in `ml/data/` (gitignored; documented in `ml/data/README.md`)
- Training scripts produce `.onnx` export + a `metrics.json` with eval results
- Never deploy a model without updating `registry.json` and running `scripts/validate_model.py`

## Inference service pattern
- Inference runs in `hub/services/inference.py` as a background loop
- Pulls a sliding window of readings from TimescaleDB
- Writes results to `events` and `anomaly_scores` tables — never writes back to `sensor_readings`
- ML results are read by the API layer from DB — inference service does NOT call the API

## On-device (ESP32) model constraints
- Max model size: 256 KB (INT8 quantized)
- Max inference latency: 50 ms per frame
- Distilled from a YAMNet-style teacher; training in `ml/training/acoustic/`

## Boundary to Backend
- Inference service is a consumer of `sensor_readings` and a producer of `events` / `anomaly_scores`
- It does NOT expose HTTP endpoints itself — all access is via the `api` service reading from DB
