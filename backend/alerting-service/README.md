# Alerting Service

The rules engine of the Smart Waste Bin platform. This service watches the live stream of confirmed fill-percentage updates and turns threshold breaches into actionable, persisted alerts that operators see on the dashboard — without ever touching the estimation algorithm or the persistence pipeline itself.

## Role in the Architecture

```
Redis Stream: bin-fill-updated
        │  (consumer group: alerting-telemetry-group)
        ▼
Alerting Service ──▶ TimescaleDB: alerts table
```

This service reads from the same `bin-fill-updated` stream as the Persistence Service, but through its **own independent consumer group** — Redis Streams consumer groups are isolated from one another, so both services receive every message without interfering with each other's delivery or acknowledgment state.

## Responsibilities

- Consumes `bin-fill-updated` and evaluates alerting rules against every confirmed fill-percentage update.
- Maintains alert lifecycle state: opens a new `high_fill` alert the first time a bin crosses the threshold, and automatically resolves it once the fill level drops back below threshold — without ever creating duplicate open alerts for the same bin.
- Keeps the domain rule (`evaluate_telemetry_alerts`) fully decoupled from stream/consumer plumbing, so the threshold logic can be unit-tested against a plain database cursor.

## Current Rule Set

| Alert Type | Trigger Condition | Resolution Condition |
|---|---|---|
| `high_fill` | `fill_percent >= 80.0%` and no existing open `high_fill` alert for the bin | `fill_percent < 80.0%` while an open alert exists |

> The `alerts` table schema anticipates additional alert types (`offline`, `sensor_fault`) for future iterations of this service; only `high_fill` is implemented today.

## Tech Stack

| Component | Choice |
|---|---|
| Language | Python 3.11 |
| Database | TimescaleDB (PostgreSQL) via `psycopg2-binary` |
| Connection management | `psycopg2.pool.ThreadedConnectionPool` |
| Message bus | Redis Streams (consumer group) |
| Container base | `python:3.11-slim` |

## Project Structure

```
alerting-service/
├── src/
│   ├── config.py               # Settings, including per-replica consumer name
│   ├── redis_client.py         # Redis bootstrapper + consumer group creation
│   ├── database.py             # DatabaseManager: pooled connections with retry-on-startup
│   ├── domain/
│   │   └── rules.py            # evaluate_telemetry_alerts() -- pure rule logic, takes a cursor
│   └── main.py                  # Stream consumer loop / composition root
├── requirements.txt
└── Dockerfile
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `REDIS_HOST` | `localhost` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `DATABASE_URL` | `postgresql://wastebin_app:securepassword@localhost:5432/wastebin` | TimescaleDB connection string — **must** be overridden via environment in any real deployment |

`CONSUMER_NAME` is derived automatically from the container's hostname, enabling safe horizontal scaling.

## Running Locally

```bash
docker build -t alerting-service .
docker run --rm \
  -e REDIS_HOST=redis \
  -e DATABASE_URL=postgresql://wastebin_app:${DB_PASSWORD}@timescaledb:5432/wastebin \
  alerting-service
```

## Design Notes

- **Why a separate service instead of folding this logic into the Fill Estimation Service?** Alerting rules (thresholds, escalation policies, notification channels) are expected to change far more often, and by different stakeholders (municipal operations), than the sensor-fusion algorithm. Keeping them in an independently deployable service means threshold tuning never risks destabilizing the core estimation logic, and vice versa.
- **Idempotent by construction:** because the service checks for an existing open alert before inserting a new one, redelivery of the same stream message (e.g. after a crash before acknowledgment) cannot create duplicate alerts.
- **Transactional safety:** the rule evaluation and its resulting `INSERT`/`UPDATE` run inside a single transaction per message; the Redis message is only acknowledged after a successful commit.
