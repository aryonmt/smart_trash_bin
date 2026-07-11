# Persistence Service

The durability layer of the Smart Waste Bin platform. This service is the only writer to TimescaleDB's `bins` and `readings` tables — it drains the processed event streams and turns them into queryable, historical, relational data for the API Gateway and dashboard to read.

## Role in the Architecture

```
Redis Stream: bin-fill-updated ──▶ Persistence Service ──▶ TimescaleDB: bins (live state)
Redis Stream: device-status    ──▶        │                TimescaleDB: readings (history hypertable)
                                          │
                                    (both consumed via
                                     dedicated consumer groups)
```

## Responsibilities

- Consumes `bin-fill-updated` (consumer group `persistence-telemetry-group`) and writes:
  - An upsert into `bins` (current fill %, last reading timestamp, last emptied timestamp).
  - An append-only row into the `readings` hypertable, preserving full history for trend charts and future forecasting.
- Consumes `device-status` (consumer group `persistence-status-group`) and updates the `status`/`last_status_at` columns on `bins`.
- Enforces a **provisioning security gate**: telemetry is only persisted for bins that already exist in the database with `provisioned = TRUE`. A bin cannot register itself simply by sending MQTT traffic — it must first be explicitly created through the API Gateway's provisioning endpoint by an administrator. Status updates for unprovisioned or unknown device IDs are silently ignored by design, never implicitly creating a row.

## Tech Stack

| Component             | Choice                                         |
| --------------------- | ---------------------------------------------- |
| Language              | Python 3.11                                    |
| Database              | TimescaleDB (PostgreSQL) via `psycopg2-binary` |
| Connection management | `psycopg2.pool.ThreadedConnectionPool`         |
| Message bus           | Redis Streams (consumer groups)                |
| Container base        | `python:3.11-slim`                             |

## Project Structure

```
persistence-service/
├── src/
│   ├── config.py               # Settings, including per-replica consumer name
│   ├── redis_client.py         # Redis bootstrapper + consumer group creation for both streams
│   ├── database.py             # DatabaseManager: pooled connections with retry-on-startup
│   ├── handlers/
│   │   ├── telemetry.py        # bin-fill-updated → bins upsert + readings insert
│   │   └── status.py           # device-status → bins status update (provisioned-only)
│   └── main.py                  # Dual-stream consumer loop / composition root
├── requirements.txt
└── Dockerfile
```

## Data Flow Detail

### `handle_telemetry_entry`

1. `SELECT provisioned FROM bins WHERE bin_id = %s` — if the bin is missing or not provisioned, the message is acknowledged and dropped (no data written, a security warning is logged).
2. `INSERT ... ON CONFLICT (bin_id) DO UPDATE` on `bins` — keeps `current_fill_pct`, `last_reading_at` current, and only overwrites `last_emptied_at` when this cycle actually represents an empty event.
3. `INSERT INTO readings (...)` — one immutable row per reading, the source of truth for all historical charts.
4. Both statements run inside the same connection/transaction; on any failure the transaction is rolled back and the Redis message is **not** acknowledged, so it will be retried.

### `handle_status_entry`

A strict `UPDATE ... WHERE bin_id = %s AND provisioned = TRUE` — intentionally never an upsert, so an unregistered device can never create a `bins` row through a status heartbeat alone.

## Configuration

| Variable       | Default                                                            | Description                                                                                   |
| -------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `REDIS_HOST`   | `localhost`                                                        | Redis hostname                                                                                |
| `REDIS_PORT`   | `6379`                                                             | Redis port                                                                                    |
| `DATABASE_URL` | `postgresql://wastebin_app:securepassword@localhost:5432/wastebin` | TimescaleDB connection string — **must** be overridden via environment in any real deployment |

`CONSUMER_NAME` is derived automatically from the container's hostname, enabling safe horizontal scaling.

## Running Locally

```bash
docker build -t persistence-service .
docker run --rm \
  -e REDIS_HOST=redis \
  -e DATABASE_URL=postgresql://wastebin_app:${DB_PASSWORD}@timescaledb:5432/wastebin \
  persistence-service
```

## Design Notes

- **Why a connection pool instead of a single global connection?** A single raw connection is a single point of failure: if it drops (network blip, database restart), every subsequent write silently fails until the process is restarted. `ThreadedConnectionPool` with per-operation `get_connection()`/`release_connection()` in a `try/finally` means a transient connection issue self-heals on the next cycle instead of wedging the whole service.
- **Why gate persistence on `provisioned` rather than auto-registering any device that sends data?** Auto-registration means anyone who can reach the MQTT broker with valid (even shared) device credentials can silently inject arbitrary bin IDs into the fleet inventory. Requiring explicit administrative provisioning first makes the bin registry an intentional, auditable list rather than an implicit side effect of network traffic.
- **At-least-once delivery:** messages are only acknowledged (`XACK`) after a successful commit. A crash between processing and acknowledging results in redelivery on restart, which is safe here because the upsert and insert operations are effectively idempotent for the same reading.
