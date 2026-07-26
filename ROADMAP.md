# AuraSense — Upgrade Roadmap

_From the Phase-1 skeleton to the "Ambient Guardian" product + research thesis._

Status legend: ⬜ not started · 🟨 in progress · ✅ done
Size legend: **S** ≈ hours–1 day · **M** ≈ a few days · **L** ≈ 1–2+ weeks

This roadmap is the source of truth across sessions. When a stage is finished, flip its box and note anything that changed mid-build.

---

## Where we are today (map of the territory)

```
firmware/            ❌ does not exist (vision: ESP32-S3 nodes emitting feature vectors)
mobile/              ❌ does not exist (vision: Flutter control panel + assistant)
hub/                 ✅ FastAPI + asyncio: ingestion, inference, llm_assistant, REST+WS API
  services/ingestion.py    MQTT → Pydantic validate → TimescaleDB
  services/inference.py    15 s poll loop; NILM/fall/anomaly are RULE-BASED SIMULATIONS
  services/llm_assistant.py llama.cpp wrapper; real path never used → keyword sim
  services/api/            nodes / events / assistant / websocket routers
ml/training/         ⚠️  4 scripts, ALL MOCKS (print fake epochs, write placeholder .onnx bytes)
shared/types/        ✅ Pydantic contracts (sensor payloads, API types, ML contracts) — solid
dashboard/           ✅ TanStack-Start template; /console wired to API w/ mock fallback
docker-compose.yml   ✅ TimescaleDB + Mosquitto
                     ❌ no tests, no CI, no device firmware, no real models
```

### Correctness bugs to fix regardless of direction
1. **Auth is a no-op** — `verify_token` (`hub/services/api/main.py`) is never attached to any router and accepts any non-empty token; CORS is `*` + `allow_credentials`.
2. **Live WebSocket never fires** — the PG `LISTEN` listener starts from `@router.on_event("startup")` (`hub/services/api/routers/websocket.py`); router-level startup hooks don't run in FastAPI, so `events_channel` is never broadcast.
3. **paho-mqtt v2 breakage** — `mqtt.Client()` + v1 `on_connect(...rc)` (`hub/services/ingestion.py`) throws under paho ≥2.0, allowed by the `>=1.6.1` pin.
4. **Deprecated APIs** — FastAPI `@app.on_event`, Pydantic v2 `.dict()`.
5. **LLM assistant** opens an unpooled `asyncpg.connect` per query and loads the model synchronously at import → blocks API startup.
6. **Anomaly "3 a.m." logic uses UTC hour** (`inference.py`), not local time.
7. **Dashboard NILM chart is hardcoded mock** — no energy/anomaly endpoint feeds it.

---

## Key design decisions (the "why" behind the plan)

- **Split inference into a reflex path and a batch path.** The current single 15 s poll loop is fine for NILM and behavioral drift (minute-scale) but far too slow for a CRITICAL fall or a glass-break. **Deviation from the existing pattern:** add an in-process async pub/sub so the ingestion stream drives latency-critical models immediately (<1 s), while the periodic loop keeps handling slow-moving analytics. Reason: alert latency on the events that matter.
- **Where each model runs.** Acoustic detection runs **on the node** (INT8 TFLite-Micro on the ESP32-S3, emits only labels) per the privacy promise; NILM, fall, and behavioral anomaly run **on the hub** (ONNX Runtime); the LLM runs **on the hub**. This split is already implied by the vision — the roadmap makes it explicit and load-bearing.
- **One schema, three languages.** Today `shared/types` (Pydantic) is the single contract and that's fine. The moment firmware (C/C++) and mobile (Dart) arrive, these types will drift silently. Plan: keep Pydantic canonical, then generate JSON Schema from it (`model_json_schema()`) and codegen Dart + C structs, with a CI contract test that fails on drift. **This is the top boundary hot-spot — see below.**
- **A device simulator is a keystone deliverable, not a toy.** Building it early (F3) unblocks ML (replay real datasets as MQTT), mobile, and firmware — all without hardware — and becomes the backbone of CI and hardware-in-the-loop tests.
- **No new heavyweight frameworks without a callout.** Additions proposed here — `pytest`, a training stack (PyTorch), ONNX Runtime, Flutter, ESP-IDF — are each introduced at the stage that needs them, not up front.

### Boundary hot-spots (both sides must agree; nothing forces them to)
- **Client ↔ hub**: REST/WS contract shape, versioning, the pairing-token auth scheme, error envelope (`GenericResponseEnvelope`).
- **Hub ↔ ML**: model input tensor shape/units, feature preprocessing, model + registry versioning.
- **Node ↔ hub**: MQTT topic scheme (`aurasense/nodes/{id}/{type}`), payload schema, timing/heartbeat, offline behavior.
- **Shared types across Python/Dart/C++**: the drift risk above.

---

## Phase 0 — Foundation hardening  _(prerequisite for everything)_

### ✅ F1 · Fix the correctness bugs — **S**  _(done 2026-07-24)_
- **Goal**: everything that's currently silently broken actually works; the "Live" badge means live.
- **Steps** (all done):
  - Migrated `hub/services/api/main.py` to the FastAPI **lifespan** context; the WS PG-listener now starts at the app level (`routers/websocket.py` router-startup hook removed).
  - Migrated `ingestion.py` to paho-mqtt **`CallbackAPIVersion.VERSION2`**; pinned `paho-mqtt>=2.0,<3` in `hub/requirements.txt`.
  - Replaced Pydantic `.dict()` → `.model_dump()` (`ingestion.py`).
  - `LLMAssistant` now takes the shared asyncpg pool; model loads off the event loop in the lifespan (`llm_assistant.py`, `routers/assistant.py`). Also added the `asyncio` import it was missing.
  - Local-time hour-of-day via `_local_hour()` + optional `AURASENSE_TZ` (`inference.py`); tidied `get_event_loop()` → `get_running_loop()`.
  - Removed the obsolete `version:` key from `docker-compose.yml` (dropped its boot warning).
- **Depends on**: none.
- **Verified**: `tests/` (seeds F3) — 3 passing against the live TimescaleDB:
  `test_f1_event_bridge` proves an inserted event is broadcast over the WebSocket (the headline bug); `test_f1_ingestion` proves the paho-v2 signature and a real DB write + node upsert. Import smoke test shows the app constructs with the lifespan, all routes wired, and **no deprecation warnings from our code**.
- **Not yet**: the full MQTT→inference→WS chain (needs the F3 simulator + inference running together); covered by proving each half here.

### ✅ F2 · Real pairing-based auth + lock-down — **M**  _(done 2026-07-24)_
- **Goal**: the API is no longer open; clients authenticate with a per-home paired token.
- **Steps** (done):
  - `hub/services/api/security.py`: HS256 JWT signing/verification + constant-time pairing-code check; config from env (`AURASENSE_JWT_SECRET`, `AURASENSE_PAIRING_CODE`, `AURASENSE_TOKEN_TTL_HOURS`) with an insecure-dev-secret warning.
  - `POST /api/v1/pair` (`routers/pairing.py`, open) exchanges the pairing code for a short-lived bearer token.
  - `Depends(verify_token)` applied to the nodes/events/assistant routers; `/pair` and `/health` stay open.
  - CORS restricted to `AURASENSE_ALLOWED_ORIGINS` (default the dashboard origin) instead of `*`.
  - `.env.example` documents all secrets/config (and the host DB port 5434).
  - Added `PairRequest`/`PairResponse` to `shared/types/api_types.py`.
- **Depends on**: F1.
- **Verified**: `tests/test_f2_auth.py` (6 tests) — 401 without a token, pair→200 with a token, wrong code → 401, garbage token → 401, events also protected; full suite 9/9 green.
- **Deferred (by design)**: WebSocket `/ws/v1/events` auth and the dashboard's token-wiring are not in F2 (WS isn't a `/api/v1` router; the typed dashboard client is F4). The dashboard shows mock lists until F4 sends the token; the live WS stream still works.

### ✅ F3 · Test harness, device simulator & CI — **M**  _(done 2026-07-24)_  _(keystone)_
- **Goal**: the system is verifiable and there's a hardware-free way to drive it.
- **Steps** (done):
  - **`tools/sim/` device simulator**: publishes schema-valid power/audio/motion/env feature vectors over MQTT with scenarios (`normal`, `fall`, `microwave`, `water`, `night`). Pure generator (`generator.py`) + CLI (`python -m tools.sim`).
  - Centralized the sensor-`type`→model map as `PAYLOAD_MODELS` in `shared/types/sensor_payload.py` (was duplicated in ingestion) so sim/tests/ingestion can't drift.
  - Expanded `tests/`: simulator schema-validity (every sensor×scenario validates against the contracts), ingestion validation rejection, fall-detection + throttling. Suite = **35 tests**.
  - `pyproject.toml` (pytest `pythonpath`, ruff `E9`/`F`, mypy config) + `requirements-dev.txt`.
  - `hub/db/init_db.py`: idempotent schema initializer (CI applies it to a fresh DB).
  - `.github/workflows/ci.yml`: hub job (Timescale service → schema init → ruff → pytest) + dashboard build job.
- **Depends on**: F1 (F2 recommended).
- **Verified**: `ruff` clean; 35/35 pytest green; schema-init works via asyncpg; and the literal acceptance — `python -m tools.sim --scenario fall` (with ingestion+inference+API running) produced a CRITICAL `fall_detected` event fetched through the authenticated `/api/v1/events` endpoint (full sim→ingest→infer→event→API chain).
- **Note**: the dashboard CI job (`bun install`/`bun run build`) isn't verifiable in this local env (no bun) — watch it on the first CI run; it's isolated from the hub job.

### ✅ F4 · Real data endpoints + TimescaleDB policies — **M**  _(done 2026-07-24)_
- **Goal**: the dashboard shows real data; the DB won't grow unbounded.
- **Steps** (done):
  - Hub: new `energy_disaggregation` hypertable; inference persists the NILM breakdown each cycle; `GET /api/v1/energy` + `GET /api/v1/anomaly-scores` (token-protected); compression (7d) + retention (30/90d) policies in `schema.sql` + `hub/db/migrations/001_f4_energy_and_policies.sql`.
  - Dashboard: typed hub client `dashboard/src/lib/api.ts` that pairs for a token (F2) and exposes typed calls; `console.tsx` now drives the NILM chart and a new Behavioral-Anomaly panel from the live endpoints and drops the `mock*` arrays; `VITE_HUB_URL`/`VITE_PAIRING_CODE` env (+ `dashboard/.env.example`, `vite-env.d.ts`). The CORS default now includes the dashboard's :8080 origin.
- **Depends on**: F1 (F2 for the token).
- **Verified**: hub — 38/38 pytest green; schema + policies apply. Dashboard — `tsc` clean, `npm run build` succeeds, and **browser-verified**: with the stack + simulator running, the console rendered live nodes/events, a live NILM area chart (real time-buckets + appliance legend) and the anomaly panel (live score, 0–1 axis, threshold line) — no mock data.
- **Deferred (noted)**: continuous-aggregate rollups (CAGG-in-transaction constraint) and WebSocket auth (client work) — both fast follows.

> **Phase 0 (Foundation) complete — F1–F4 done.** Next: Phase 1 (real ML), starting with M1 (training pipeline scaffolding).

---

## Phase 1 — Make the ML real

### ⬜ M1 · Training pipeline scaffolding — **M**
- **Goal**: reproducible training that emits real ONNX + an eval gate — no more placeholder bytes.
- **Steps**: introduce PyTorch (callout) + a shared `ml/common` (datasets, feature transforms mirroring `shared/types`, ONNX export, metric reporting); real `metrics.json` + model card per run; extend `hub/models/registry.json` with checksums, input signatures, and eval thresholds; a `make train-<model>` entry.
- **Depends on**: F3 (simulator/replay + CI).
- **Done when**: `python ml/training/nilm/train.py` produces a **loadable** ONNX file whose input signature matches `NILMInput`, and `onnxruntime` loads it in a test.

### ⬜ M2 · Real NILM (seq-to-point CNN) — **L**
- **Goal**: genuine appliance disaggregation replacing the `if avg_power > X` rules in `inference.py`.
- **Steps**: train seq-to-point CNN on UK-DALE/REDD; export ONNX; replace `run_nilm` simulation with real ORT inference over the power window; publish per-appliance series to the `energy` endpoint/table.
- **Depends on**: M1, F4.
- **Done when**: on a held-out house, per-appliance MAE beats a mean baseline (target parity with the numbers `metrics.json` currently fakes), checked by an eval test; the dashboard shows model-driven disaggregation.

### ⬜ M3 · Real fall detection + behavioral anomaly (reflex path) — **L**
- **Goal**: a trained fall LSTM and an anomaly model (autoencoder/isolation forest), with falls on the low-latency reflex path.
- **Steps**: train fall LSTM over radar point-cloud sequences and the behavioral autoencoder; implement the in-process pub/sub reflex path (design decision above) so `motion`/`audio` frames evaluate immediately; keep the periodic loop for behavioral drift; tune the false-alarm rate (the hardest metric — the vision calls this out).
- **Depends on**: M1, F1.
- **Done when**: simulator "fall" scenario fires a CRITICAL event in <1 s; a benign-motion suite holds false alarms under the target threshold (test-enforced).

### ⬜ M4 · Acoustic event detection (on-device INT8) — **L**
- **Goal**: a real compact CNN on log-mel spectrograms, distilled and INT8-quantized, targeting the ESP32-S3.
- **Steps**: train/distill from a YAMNet-style teacher; export TFLite-Micro INT8; hub-side reference decoder now, on-node deployment in D1. Labels only ever leave the node (privacy invariant).
- **Depends on**: M1.
- **Done when**: quantized model classifies glass-break/smoke/water on a test clip set above target accuracy and fits the ESP32-S3 memory budget (documented in the model card).

### ⬜ M5 · Grounded on-device LLM — **M**
- **Goal**: replace the keyword simulation in `llm_assistant.py` with a real quantized LLM + retrieval over the home's time-series.
- **Steps**: wire Phi-3-mini / Llama-3.2-1B (GGUF) via llama.cpp; build retrieval over events + continuous aggregates; keep the simulated responses strictly as an offline test fallback; stream tokens to the dashboard/app.
- **Depends on**: F4 (aggregates to retrieve over).
- **Done when**: "why was my bill high this month?" returns an answer grounded in real NILM aggregates, with the retrieved context shown; an eval checks it cites actual figures.

---

## Phase 2 — Device + mobile surfaces

### ⬜ D1 · ESP32-S3 sensor-node firmware — **L**
- **Goal**: a real node computes features on-device and publishes them (never raw streams), starting with one sensor type end-to-end.
- **Steps**: `firmware/` (ESP-IDF); power node first (CT sensor → RMS/apparent-power/THD → MQTT on the existing topic scheme); then acoustic node running the M4 INT8 model; C structs generated from the shared schema (see boundary hot-spot). Must reach simulator parity — same payloads the sim emits.
- **Depends on**: F3 (schema + sim parity), M4 (for the acoustic node).
- **Done when**: a physical (or QEMU-emulated) ESP32-S3 appears in `GET /api/v1/nodes` as ONLINE and its readings validate against `shared/types` and land in TimescaleDB.

### ⬜ D2 · Provisioning & pairing flow — **M**
- **Goal**: a new node/home onboards securely and gets the F2 pairing secret.
- **Steps**: BLE/SoftAP Wi-Fi onboarding on the node; a hub pairing service that mints the credential F2 consumes; node identity in the `nodes` table.
- **Depends on**: D1, F2.
- **Done when**: a factory-reset node joins Wi-Fi and appears paired in the API without hand-editing config.

### ⬜ D3 · OTA firmware pipeline — **M**
- **Goal**: make the mocked OTA endpoint (`routers/nodes.py`) real and safe for a fleet.
- **Steps**: signed image build + hosting; real MQTT `aurasense/nodes/{id}/ota/cmd`; A/B partition + rollback on the node; staged rollout + version tracking in the fleet view.
- **Depends on**: D1.
- **Done when**: `POST /nodes/{id}/ota` moves a node to a new firmware version with automatic rollback on a bad image, shown in the dashboard.

### ⬜ D4 · Flutter mobile app — **L**
- **Goal**: the vision's primary interface — control panel + conversational assistant + push alerts, offline-first.
- **Steps**: `mobile/` (Flutter); Dart models generated from the shared schema; LAN-first client to the hub with the F2 token; the M5 assistant chat; a thin cloud relay for push notifications + encrypted backups (LAN stays the default path).
- **Depends on**: F2, F4, M5.
- **Done when**: on a phone on the same LAN, the app pairs, lists nodes/events, chats with the assistant, and receives a push for a CRITICAL fall while backgrounded.

---

## Phase 3 — Research thesis  _(the publishable core)_

### ⬜ R1 · Cross-home NILM generalization — **L**
- **Goal**: quantify and improve NILM on homes never seen in training.
- **Steps**: leave-one-house-out eval harness; domain-adaptation / normalization experiments; a benchmark report checked into `ml/`.
- **Depends on**: M2.
- **Done when**: a reproducible benchmark reports transfer MAE across held-out homes with a documented improvement over the naive-transfer baseline.

### ⬜ R2 · Multi-sensor fusion → one trustworthy signal — **L**
- **Goal**: fuse radar + audio + power into a single anomaly signal that beats any single modality.
- **Steps**: a fusion model over the three streams; ablations vs. each modality alone; calibrated confidence.
- **Depends on**: M2, M3, M4.
- **Done when**: fused precision/recall beats each single-sensor baseline on a labeled scenario set (ablation table in the report).

### ⬜ R3 · Federated learning across homes — **L**
- **Goal**: the thesis capstone — models improve across homes **without sharing raw data**.
- **Steps**: federated averaging over hub-side models; on-device personalization; a privacy-budget writeup; fleet-level orchestration.
- **Depends on**: R1/R2, D3 (fleet delivery), a multi-home deployment.
- **Done when**: a simulated federation of ≥3 homes shows a global model improving over rounds with only weight updates (never raw signals) crossing the boundary — demonstrated in an experiment notebook.

---

## Suggested sequencing

1. **F1 → F2 → F3 → F4** in order (foundation; F3 unblocks nearly everything).
2. Then parallelize: **M1→M2/M3/M4/M5** (ML) alongside **D1** (firmware) once F3 lands.
3. **D2/D3/D4** after D1 + the relevant M/F stages.
4. **R1–R3** last — they need real models (Phase 1) and, for R3, fleet delivery (D3) + multiple homes.

Recommended first slice to build once approved: **F1** (turns the currently-broken pieces on) then **F3** (the simulator + CI you'll lean on for every stage after).
