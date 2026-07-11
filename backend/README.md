# Backend

The Smart Waste Bin backend is a set of five small, independently deployable Python microservices that turn raw MQTT sensor traffic into a trustworthy, queryable fleet state for the dashboard. Each service does one job, owns its own data path, and talks to its neighbors only through Redis Streams or TimescaleDB — never through direct service-to-service calls.

This document is the map of how they fit together. For the detailed responsibilities, algorithms, API references, and configuration of a specific service, see its own README linked below.

## The Services

| Service | One-line role | README |
|---|---|---|
| **ingestion-service** | Only consumer of MQTT; validates payloads and anti-spoofs device identity, republishes onto Redis Streams | [`ingestion-service/README.md`](ingestion-service/README.md) |
| **fill-estimation-service** | Stateful algorithm turning noisy raw distance readings into a trustworthy, monotonic fill percentage | [`fill-estimation-service/README.md`](fill-estimation-service/README.md) |
| **persistence-service** | Only writer of `bins`/`readings` in TimescaleDB; enforces that only provisioned bins get persisted | [`persistence-service/README.md`](persistence-service/README.md) |
| **alerting-service** | Rules engine; opens/resolves threshold-based alerts independently of the estimation and persistence paths | [`alerting-service/README.md`](alerting-service/README.md) |
| **api-gateway** | The only service exposed outside the Docker network; JWT auth, RBAC, and all dashboard-facing REST endpoints | [`api-gateway/README.md`](api-gateway/README.md) |

None of these communicate directly with one another. A message produced by one is picked up by the next purely by virtue of which Redis Stream or database table it lands in — so any service can be scaled, restarted, or temporarily down without the others needing to know or care.

## End-to-End Data Flow

```
                 MQTT/TLS
ESP32 Devices ─────────────▶ Mosquitto Broker
                                     │ MQTT
                                     ▼
                         ┌─────────────────────┐
                         │  ingestion-service   │
                         └──────────┬───────────┘
                        ┌───────────┴────────────┐
                        ▼                         ▼
             Stream: raw-telemetry       Stream: device-status
                        │                         │
                        ▼                         │
           ┌─────────────────────────┐            │
           │ fill-estimation-service │            │
           └────────────┬────────────┘            │
                         ▼                         │
             Stream: bin-fill-updated              │
              ┌──────────┴──────────┐              │
              ▼                     ▼              │
  ┌────────────────────┐  ┌────────────────────┐   │
  │ persistence-service │  │  alerting-service  │   │
  └──────────┬──────────┘  └──────────┬─────────┘   │
             │                        │              │
             └────────────┬───────────┴──────────────┘
                           ▼
                     TimescaleDB
              (bins · readings · alerts · users)
                           ▲
                           │  reads + admin writes
                           │
                    ┌─────────────┐
                    │ api-gateway │◀── JWT ── Dashboard (frontend)
                    └─────────────┘
```

## Redis Streams Topology

All inter-service communication (besides the MQTT hop into `ingestion-service`) goes through three Redis Streams, each consumed via one or more independent **consumer groups** — Streams keep per-group delivery/acknowledgment state, so multiple services (or multiple replicas of the same service) can read the same stream without stepping on each other, and a crashed-before-ack message is safely redelivered.

| Stream | Producer | Consumer(s) / consumer group |
|---|---|---|
| `raw-telemetry` | ingestion-service | fill-estimation-service (`estimation-group`) |
| `device-status` | ingestion-service | persistence-service (`persistence-status-group`) |
| `bin-fill-updated` | fill-estimation-service | persistence-service (`persistence-telemetry-group`), alerting-service (`alerting-telemetry-group`) |

`fill-estimation-service` additionally keeps a small piece of *non-stream* state in Redis — one key per bin, `bin_state:{device_id}` — holding the in-progress `BinFillState` between measurement cycles. That key is cleared by `api-gateway` whenever a bin is manually emptied or deleted, so the algorithm always starts from a clean baseline after either event.

## TimescaleDB Ownership

Every table in `postgres/init.sql` has exactly one writer, even though several services may read from it:

| Table | Written by | Read by |
|---|---|---|
| `bins` | persistence-service (telemetry/status updates), api-gateway (provisioning, manual empty, delete) | api-gateway |
| `readings` (hypertable) | persistence-service | api-gateway |
| `alerts` | alerting-service (open/resolve), api-gateway (acknowledge) | api-gateway |
| `users` | api-gateway (seeds the initial `admin` on first boot) | api-gateway |

This single-writer-per-table discipline is what lets each service's README describe its database behavior in isolation without needing to account for write conflicts from the others.

## Shared Conventions

Every service in this backend follows the same set of house rules, so once you've read one service's code the rest are familiar:

- **Clean Architecture where it matters:** the fill-estimation and alerting services isolate their core logic (`domain/estimator.py`, `domain/rules.py`) from all I/O, so the actual business rules are plain functions that take/return data and are unit-testable without Redis or Postgres running.
- **Config via environment variables only**, with sane `localhost`-based defaults for running a single service standalone, and no insecure fallback for secrets (`api-gateway` refuses to boot without a real `JWT_SECRET`/`INITIAL_ADMIN_PASSWORD`).
- **Retry-on-startup, not crash-on-startup:** every service that depends on Redis, Postgres, or the MQTT broker retries with backoff instead of failing immediately, so `docker compose up` doesn't require a specific container start order.
- **At-least-once stream processing:** a stream message is only acknowledged (`XACK`) after its corresponding database write has committed successfully, so a crash mid-processing results in safe redelivery rather than silent data loss.
- **English-only docstrings and comments**, full type hints/Pydantic models at every service boundary.

## Running the Backend

The backend is designed to run as a whole via the root `docker-compose.yml` — see the [project root README](../README.md) for the full setup sequence (`.env`, `setup_security.py`, then `docker compose up -d --build`).

To run and iterate on a single service in isolation, see the **Running Locally** section of that service's own README — each one documents its `docker build`/`docker run` invocation and required environment variables.

## End-to-End Testing

`backend/test_pipeline.py` drives the whole chain by publishing a scripted sequence of MQTT messages directly (bypassing the firmware) and is the fastest way to see all five services react in sequence:

```bash
pip install paho-mqtt
python backend/test_pipeline.py
```

Run it alongside `docker compose logs -f ingestion-service fill-estimation-service persistence-service alerting-service` to watch a reading travel through the whole pipeline: MQTT → validation → estimation → persistence + alerting.
