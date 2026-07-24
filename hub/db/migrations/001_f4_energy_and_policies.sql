-- Migration 001 (F4): energy-disaggregation time-series + lifecycle policies.
--
-- Idempotent and safe to re-run. schema.sql already contains these statements
-- for fresh installs; this file is the explicit delta for an existing database.
-- Apply with:  psql "$DATABASE_URL" -f hub/db/migrations/001_f4_energy_and_policies.sql
-- (or just re-run hub/db/init_db.py, which applies the full idempotent schema).

CREATE TABLE IF NOT EXISTS energy_disaggregation (
    ts TIMESTAMPTZ NOT NULL,
    node_id VARCHAR(100) NOT NULL,
    appliances JSONB NOT NULL,
    total_w DOUBLE PRECISION NOT NULL
);
SELECT create_hypertable('energy_disaggregation', 'ts', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_energy_node_ts ON energy_disaggregation (node_id, ts DESC);

-- Compression + retention so local disk does not grow unbounded.
ALTER TABLE sensor_readings SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'node_id, type'
);
SELECT add_compression_policy('sensor_readings', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('sensor_readings', INTERVAL '30 days', if_not_exists => TRUE);

ALTER TABLE energy_disaggregation SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'node_id'
);
SELECT add_compression_policy('energy_disaggregation', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('energy_disaggregation', INTERVAL '90 days', if_not_exists => TRUE);

SELECT add_retention_policy('anomaly_scores', INTERVAL '90 days', if_not_exists => TRUE);
