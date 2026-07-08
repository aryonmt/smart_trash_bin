-- postgres/init.sql
-- -------------------------------------------------------------------------
-- TimescaleDB Database Schema Initialization
-- -------------------------------------------------------------------------

-- Create table for tracking current live state of bins (Single-row per bin)
CREATE TABLE IF NOT EXISTS bins (
    bin_id           TEXT PRIMARY KEY,
    zone_id          TEXT NOT NULL,
    bin_depth_cm     REAL NOT NULL DEFAULT 150.0,
    current_fill_pct REAL,
    last_reading_at  TIMESTAMPTZ,
    last_emptied_at  TIMESTAMPTZ,
    status           TEXT NOT NULL DEFAULT 'unknown', -- 'online' | 'offline' | 'unknown'
    last_status_at   TIMESTAMPTZ
);

-- Create table for historical time-series sensor readings
CREATE TABLE IF NOT EXISTS readings (
    time             TIMESTAMPTZ NOT NULL,
    bin_id           TEXT NOT NULL REFERENCES bins(bin_id) ON DELETE CASCADE,
    distance_cm      REAL NOT NULL,
    fill_percent     REAL NOT NULL,
    is_confirmed     BOOLEAN NOT NULL,
    emptied_this_cycle BOOLEAN NOT NULL
);

-- Convert readings to a TimescaleDB hypertable for high-performance time-series queries
SELECT create_hypertable('readings', 'time', if_not_exists => TRUE);

-- Create table for tracking alerts history
CREATE TABLE IF NOT EXISTS alerts (
    id               SERIAL PRIMARY KEY,
    bin_id           TEXT NOT NULL REFERENCES bins(bin_id) ON DELETE CASCADE,
    alert_type       TEXT NOT NULL,   -- 'high_fill' | 'offline' | 'sensor_fault'
    triggered_at     TIMESTAMPTZ NOT NULL,
    resolved_at      TIMESTAMPTZ,
    acknowledged_by  TEXT
);
