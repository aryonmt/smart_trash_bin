# API Gateway

The single public-facing entry point of the Smart Waste Bin platform's backend. Every dashboard interaction — authentication, fleet visibility, bin provisioning, alert management — flows through this FastAPI service. It is the only backend component exposed outside the internal Docker network.

## Role in the Architecture

```
                        ┌───────────────────────────┐
Dashboard (frontend) ──▶        API Gateway         │
                        │  JWT Auth · RBAC · Routing│
                        └──────────┬────────────────┘
                                   │
                     ┌─────────────┼─────────────┐
                     ▼                           ▼
              TimescaleDB                     Redis
        (bins, readings, alerts,        (login rate-limit
             users tables)                counters, bin state)
```

This service performs no MQTT or stream processing itself — it is a pure read/write API layer over the state that the ingestion → estimation → persistence → alerting pipeline has already produced, plus the administrative actions (auth, provisioning) that only a human operator should trigger.

## Responsibilities

- Issues and validates JWT session tokens (`HS256`).
- Enforces Role-Based Access Control across three roles: `admin`, `operator`, `driver`.
- Enforces per-request zone scoping: `operator`/`driver` accounts with a configured `zone_scope` only see bins and history within their assigned municipal zone.
- Exposes the fleet's live and historical state for the dashboard.
- Is the **only** place a bin can be formally registered into or removed from the system (`Device Management` responsibility).
- Rate-limits login attempts per source IP to blunt brute-force credential guessing.

## Tech Stack

| Component             | Choice                                                           |
| --------------------- | ---------------------------------------------------------------- |
| Language              | Python 3.11                                                      |
| Web framework         | FastAPI + Uvicorn                                                |
| Auth                  | `pyjwt` (HS256) + `bcrypt` password hashing                      |
| Database              | TimescaleDB (PostgreSQL) via `psycopg2-binary`, `RealDictCursor` |
| Connection management | `psycopg2.pool.ThreadedConnectionPool`                           |
| Rate limiting         | Redis counters (sliding 15-minute window)                        |
| Container base        | `python:3.11-slim`                                               |

## Project Structure

```
api-gateway/
├── src/
│   ├── config.py                 # Settings + fail-fast startup guard for JWT_SECRET
│   ├── database.py               # DatabaseManager: pooled connections + admin user seeding
│   ├── redis_client.py           # Redis bootstrapper (state cache + rate-limit counters)
│   ├── auth/
│   │   ├── crypto.py             # Password verification, JWT issuance
│   │   └── dependencies.py       # get_current_user, RoleChecker FastAPI dependencies
│   ├── models/
│   │   ├── auth.py               # LoginRequest, TokenResponse
│   │   ├── bins.py                # BinCreateRequest, BinResponse, ReadingHistoryResponse
│   │   └── alerts.py              # AlertResponse, AcknowledgeRequest
│   ├── routers/
│   │   ├── auth.py                # POST /api/auth/login
│   │   ├── bins.py                # /api/bins* endpoints
│   │   └── alerts.py              # /api/alerts* endpoints
│   └── main.py                     # Composition root: FastAPI app, CORS, router registration
├── requirements.txt
└── Dockerfile
```

## API Reference

All endpoints except `/api/auth/login` require an `Authorization: Bearer <token>` header.

### Authentication

| Method | Path              | Access | Description                                                                                                 |
| ------ | ----------------- | ------ | ----------------------------------------------------------------------------------------------------------- |
| `POST` | `/api/auth/login` | Public | Exchanges username/password for a JWT. Locks out an IP for 15 minutes after 5 failed attempts (HTTP `429`). |

### Bins

| Method   | Path                                  | Access                  | Description                                                                                                                                                                                                     |
| -------- | ------------------------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`    | `/api/bins`                           | admin, operator, driver | Lists bins. `operator`/`driver` accounts with a `zone_scope` only see bins in that zone.                                                                                                                        |
| `POST`   | `/api/bins`                           | admin                   | Provisions a new bin (`bin_id`, `zone_id`, `bin_depth_cm`, optional `label`/`latitude`/`longitude`). This is the **only** way a bin becomes eligible to have its telemetry accepted by the Persistence Service. |
| `GET`    | `/api/bins/{bin_id}/history?limit=30` | admin, operator, driver | Time-series reading history for one bin. `driver` accounts are additionally checked against their `zone_scope` before access is granted.                                                                        |
| `POST`   | `/api/bins/{bin_id}/empty`            | admin, operator         | Manually marks a bin as emptied: resets `current_fill_pct` to 0, resolves any open alerts for that bin, inserts a synthetic "emptied" reading, and clears the bin's cached estimator state in Redis.            |
| `DELETE` | `/api/bins/{bin_id}`                  | admin                   | Permanently deletes a bin and all related history/alerts (`ON DELETE CASCADE`), and clears its Redis state.                                                                                                     |

### Alerts

| Method | Path                                 | Access          | Description                                                                                                 |
| ------ | ------------------------------------ | --------------- | ----------------------------------------------------------------------------------------------------------- |
| `GET`  | `/api/alerts?status=open`            | admin, operator | Lists alerts. `status=open` (default) returns only unresolved alerts; any other value returns full history. |
| `POST` | `/api/alerts/{alert_id}/acknowledge` | admin, operator | Records which operator acknowledged an alert.                                                               |

## Configuration

| Variable                 | Default                                                            | Description                                                                                                                                                              |
| ------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `JWT_SECRET`             | _(none — required)_                                                | Signing secret for issued JWTs. The service refuses to start if this is unset or equal to a known insecure placeholder value. Generate with e.g. `openssl rand -hex 32`. |
| `INITIAL_ADMIN_PASSWORD` | _(none — required)_                                                | Plaintext password used once, at first startup, to seed the initial `admin` account (hashed with `bcrypt` before storage). The service refuses to start without it.      |
| `DATABASE_URL`           | `postgresql://wastebin_app:securepassword@localhost:5432/wastebin` | TimescaleDB connection string — **must** be overridden via environment in any real deployment                                                                            |
| `REDIS_HOST`             | `localhost`                                                        | Redis hostname                                                                                                                                                           |
| `REDIS_PORT`             | `6379`                                                             | Redis port                                                                                                                                                               |

## Running Locally

```bash
docker build -t api-gateway .
docker run --rm -p 8000:8000 \
  -e JWT_SECRET=$(openssl rand -hex 32) \
  -e INITIAL_ADMIN_PASSWORD=change-me-immediately \
  -e DATABASE_URL=postgresql://wastebin_app:${DB_PASSWORD}@timescaledb:5432/wastebin \
  -e REDIS_HOST=redis \
  api-gateway
```

Interactive OpenAPI documentation is available at `/docs` once the service is running.

## Security Notes

- **Fail-fast configuration:** both `JWT_SECRET` and `INITIAL_ADMIN_PASSWORD` are required at startup with no insecure fallback — a misconfigured deployment fails loudly instead of silently running with a guessable default.
- **Password storage:** all credentials are hashed with `bcrypt` before being persisted; plaintext passwords are never stored.
- **Zone scoping** is enforced server-side on every relevant query, not just filtered client-side, so a scoped operator or driver account cannot see data outside their assignment even by calling the API directly.
- **CORS** is currently configured with `allow_origins=["*"]` and `allow_credentials=False` (the token is sent via the `Authorization` header, not cookies, so this combination does not expose credentials to third-party origins). For production deployments, restricting `allow_origins` to the dashboard's actual domain is recommended as defense in depth.
- The `GET /api/bins` and `GET /api/alerts` endpoints do not yet implement pagination; this is acceptable at pilot scale and is a known area for follow-up work as the fleet grows into the hundreds/thousands of bins.
