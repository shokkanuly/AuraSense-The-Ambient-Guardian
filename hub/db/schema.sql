-- Enable TimescaleDB extension if not exists
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Nodes Table
CREATE TABLE IF NOT EXISTS nodes (
    node_id VARCHAR(100) PRIMARY KEY,
    type VARCHAR(50) NOT NULL, -- 'power', 'audio', 'motion', 'env'
    last_seen BIGINT NOT NULL, -- UTC Unix timestamp in seconds
    firmware_version VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ONLINE' -- 'ONLINE', 'STALE', 'OFFLINE'
);

-- Sensor Readings Table
CREATE TABLE IF NOT EXISTS sensor_readings (
    ts TIMESTAMPTZ NOT NULL,
    node_id VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    features JSONB NOT NULL
);

-- Create hypertable for sensor readings
SELECT create_hypertable('sensor_readings', 'ts', if_not_exists => TRUE);

-- Index for sensor readings
CREATE INDEX IF NOT EXISTS idx_sensor_readings_node_type_ts ON sensor_readings (node_id, type, ts DESC);

-- Events Table
CREATE TABLE IF NOT EXISTS events (
    event_id VARCHAR(100) PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    type VARCHAR(100) NOT NULL, -- e.g., 'power_anomaly', 'glass_break', 'fall'
    severity VARCHAR(20) NOT NULL, -- 'INFO', 'WARNING', 'CRITICAL'
    node_id VARCHAR(100) NOT NULL REFERENCES nodes(node_id),
    payload JSONB NOT NULL,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_unack ON events (acknowledged) WHERE acknowledged = FALSE;

-- Anomaly Scores Table
CREATE TABLE IF NOT EXISTS anomaly_scores (
    ts TIMESTAMPTZ NOT NULL,
    model VARCHAR(100) NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    context JSONB NOT NULL
);

-- Create hypertable for anomaly scores
SELECT create_hypertable('anomaly_scores', 'ts', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_anomaly_scores_model_ts ON anomaly_scores (model, ts DESC);

-- Listen/Notify Trigger configuration for events table
CREATE OR REPLACE FUNCTION notify_event_insert()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify(
        'events_channel',
        json_build_object(
            'event_id', NEW.event_id,
            'ts', EXTRACT(EPOCH FROM NEW.ts)::integer,
            'type', NEW.type,
            'severity', NEW.severity,
            'node_id', NEW.node_id,
            'payload', NEW.payload,
            'acknowledged', NEW.acknowledged
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_notify_event_insert
AFTER INSERT ON events
FOR EACH ROW
EXECUTE FUNCTION notify_event_insert();
