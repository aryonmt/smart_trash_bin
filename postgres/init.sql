-- postgres/init.sql
-- -------------------------------------------------------------------------
-- TimescaleDB Database Schema Initialization (Version 4.0)
-- -------------------------------------------------------------------------

-- Create table for tracking current live state of bins (Single-row per bin)
CREATE TABLE IF NOT EXISTS bins (
    bin_id           TEXT PRIMARY KEY,
    zone_id          TEXT NOT NULL,
    bin_depth_cm     REAL NOT NULL DEFAULT 150.0,
    current_fill_pct REAL,
    last_reading_at  TIMESTAMPTZ,
    last_emptied_at  TIMESTAMPTZ,
    status           TEXT NOT NULL DEFAULT 'unknown',
    last_status_at   TIMESTAMPTZ,
    label            TEXT,
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION,
    provisioned      BOOLEAN NOT NULL DEFAULT FALSE
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
    alert_type       TEXT NOT NULL,
    triggered_at     TIMESTAMPTZ NOT NULL,
    resolved_at      TIMESTAMPTZ,
    acknowledged_by  TEXT
);

-- Create table for User accounts and Role-Based Access Control (RBAC)
CREATE TABLE IF NOT EXISTS users (
    id           SERIAL PRIMARY KEY,
    username     TEXT UNIQUE NOT NULL,
    email        TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    role         TEXT NOT NULL DEFAULT 'operator',
    zone_scope   TEXT
);

-- --- High-Performance Composite Indexes for Fleet Scalability ---
CREATE INDEX IF NOT EXISTS idx_readings_bin_time ON readings (bin_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_bins_zone ON bins (zone_id);
CREATE INDEX IF NOT EXISTS idx_bins_status ON bins (status);
CREATE INDEX IF NOT EXISTS idx_alerts_open ON alerts (bin_id) WHERE resolved_at IS NULL;
