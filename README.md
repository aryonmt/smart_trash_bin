# Smart Waste Bin IoT System

An end-to-end IoT platform for municipalities and large organizations to monitor waste bin fill levels in real time and schedule collection based on actual need instead of a fixed route.

A battery-free ESP32 sensor node (ESP32 DevKit V1 + AJ‑SR04M ultrasonic sensor) measures the distance to the trash surface, a microservice backend turns that noisy raw signal into a trustworthy fill percentage, and a web dashboard lets operators see and manage every bin in the fleet.

## Table of Contents

- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Default Login](#default-login)
- [Services & Ports](#services--ports)
- [Environment Variables](#environment-variables)
- [Security Notes](#security-notes)
- [Testing the Pipeline](#testing-the-pipeline)
- [Further Documentation](#further-documentation)

## Architecture

```
ESP32 + AJ-SR04M  --MQTTS-->  Mosquitto  ------>  ingestion-service  ------>  Redis Streams
                                                                                    |
                                                                     raw-telemetry / device-status
                                                                                    v
                                                                     fill-estimation-service
                                                                     (median/MAD + persistence +
                                                                      ratchet fill-level algorithm)
                                                                                    |
                                                                       bin-fill-updated stream
                                                                        /                    \
                                                          persistence-service          alerting-service
                                                          (writes TimescaleDB)         (writes alert rows)
                                                                        \                    /
                                                                          TimescaleDB (Postgres)
                                                                                    |
                                                                           api-gateway (FastAPI, JWT auth)
                                                                                    |
                                                                       frontend (React dashboard)
```

Each backend component is an independent microservice with a single responsibility, communicating asynchronously through Redis Streams so that no single slow/down consumer can block ingestion. Historical readings and alerts are persisted in TimescaleDB; Redis also holds the fast-access current state used by the fill-estimation algorithm between cycles.

## Repository Layout

```
.
├── firmware/                  ESP32 sensor node (PlatformIO/Arduino) — see firmware/README.md
├── backend/
│   ├── ingestion-service/     MQTT -> Redis Streams bridge, payload validation
│   ├── fill-estimation-service/  Core fill-level algorithm (stateful, per bin)
│   ├── persistence-service/   Writes readings/status/alerts to TimescaleDB
│   ├── alerting-service/      Threshold-based alert rules (open/resolve)
│   ├── api-gateway/           FastAPI REST API, JWT auth, RBAC
│   └── test_pipeline.py       Manual end-to-end simulation script
├── frontend/                  React + Vite dashboard — see frontend/README.md
├── mosquitto/config/          Mosquitto broker configuration
├── postgres/init.sql          TimescaleDB schema (bins, readings, alerts, users)
├── setup_security.py          Generates TLS certs + MQTT password file
├── docker-compose.yml         Orchestrates the full backend + frontend stack
├── .env.example                Template for backend/broker secrets
└── firmware/src/secrets.cpp.example   Template for device Wi-Fi/MQTT credentials
```

See [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md) for details on each layer; see [`firmware/README.md`](firmware/README.md) for wiring and flashing the sensor node.

## Prerequisites

- Docker and Docker Compose
- Python 3.10+ (only needed locally to run `setup_security.py` and the manual test script)
- [PlatformIO](https://platformio.org/) (CLI or the VS Code extension) to build and flash the ESP32 firmware
- An ESP32 DevKit V1 wired to an AJ‑SR04M sensor — see [`firmware/README.md`](firmware/README.md)

## Getting Started

### 1. Clone and configure secrets

```bash
git clone <this-repo-url>
cd smart_trash_bin
cp .env.example .env
```

Open `.env` and replace every placeholder value with a real secret:

| Variable | Purpose |
|---|---|
| `DB_PASSWORD` | Password for the TimescaleDB `wastebin_app` user |
| `MQTT_BIN_PASSWORD` | Password the physical bin devices will authenticate with |
| `MQTT_INGESTION_PASSWORD` | Password the `ingestion-service` uses to authenticate to the broker |
| `JWT_SECRET` | Signing key for dashboard session tokens — use a long random value, e.g. `openssl rand -hex 32` |
| `INITIAL_ADMIN_PASSWORD` | Password for the `admin` account that is seeded into the database on first boot |

**Never commit `.env`.** It is already listed in `.gitignore`; only `.env.example` (with placeholder values) belongs in the repository.

### 2. Generate TLS certificates and the MQTT password file

The broker is configured to require both TLS (for the device-facing listener on port 8883) and authentication. Run the provisioning script **after** `.env` is filled in and **before** starting the stack:

```bash
python setup_security.py
```

This uses temporary Docker containers to:
- Generate a self-signed CA and a server certificate/key under `mosquitto/certs/` (used by the broker's TLS listener).
- Create `mosquitto/config/passwd`, a hashed password database containing the `bin_device` and `ingestion_service` accounts, using the passwords from `.env`.

Both `mosquitto/certs/` and `mosquitto/config/passwd` are git-ignored — every environment (dev, staging, production) generates its own.

### 3. Start the backend and dashboard

```bash
docker compose up -d --build
```

This builds and starts the broker, Redis, TimescaleDB, all five backend services, and the frontend. The database schema in `postgres/init.sql` is applied automatically on first boot, and a default `admin` account is seeded using `INITIAL_ADMIN_PASSWORD`.

Check that everything is healthy:

```bash
docker compose ps
docker compose logs -f api-gateway
```

### 4. Register (provision) a bin

For security, the platform only accepts telemetry from bins that have been explicitly registered — an unregistered `device_id` is silently dropped by `persistence-service`. Log in to the dashboard (or call the API directly) as `admin` and create the bin **before** it comes online:

```bash
curl -X POST http://localhost:8000/api/bins \
  -H "Authorization: Bearer <admin JWT from /api/auth/login>" \
  -H "Content-Type: application/json" \
  -d '{
        "bin_id": "bin-0142",
        "zone_id": "district-7",
        "bin_depth_cm": 150,
        "label": "Main Street",
        "latitude": 36.5659,
        "longitude": 53.0586
      }'
```

The `bin_id` and `zone_id` here must exactly match `DEVICE_ID` and `ZONE_ID` that you flash onto the physical device in the next step.

### 5. Flash the firmware

Follow [`firmware/README.md`](firmware/README.md) to wire the sensor, fill in `firmware/src/secrets.cpp` (copied from `secrets.cpp.example`), and flash it with PlatformIO. Once powered, the device connects over MQTTS and starts publishing telemetry.

### 6. Open the dashboard

Visit `http://localhost` and log in with the admin account created in step 3.

## Default Login

On first boot, `api-gateway` seeds one account:

- **Username:** `admin`
- **Password:** whatever you set as `INITIAL_ADMIN_PASSWORD` in `.env`

Use this account to create additional `operator`/`driver` accounts (scoped to a `zone_id`) as needed — see [`backend/README.md`](backend/README.md) for the role model.

## Services & Ports

| Service | Container | Host Port | Notes |
|---|---|---|---|
| Mosquitto (MQTT) | `mqtt-broker` | `1883`, `8883` | 1883 is internal/plaintext (Docker network only); 8883 is the TLS listener devices connect to |
| Redis | `redis-cache` | `6379` | Streams + fill-state cache |
| TimescaleDB | `timescaledb` | `5432` | `wastebin` database |
| API Gateway | `api-gateway` | `8000` | REST API consumed by the frontend |
| Frontend | `frontend-dashboard` | `80` | React dashboard served by Nginx |
| ingestion / fill-estimation / persistence / alerting services | — | *(internal only)* | No published ports; communicate via Redis Streams |

## Environment Variables

See [`.env.example`](.env.example) for the full list consumed by `docker-compose.yml`. Do not reuse any of the placeholder values in a real deployment.

## Security Notes

- **Rotate anything that was ever a placeholder or a real value pasted into chat, a screenshot, or a shared doc.** Treat `.env`, `firmware/src/secrets.cpp`, and everything under `mosquitto/certs/`/`mosquitto/config/passwd` as sensitive — they are git-ignored on purpose.
- **Always rename, never edit in place, the `*.example` files:**
  - `cp .env.example .env`
  - `cp firmware/src/secrets.cpp.example firmware/src/secrets.cpp`

  This keeps the tracked `*.example` files as safe templates and your real credentials only in the untracked copies.
- Re-run `setup_security.py` whenever you rotate `MQTT_BIN_PASSWORD` or `MQTT_INGESTION_PASSWORD` in `.env`, then restart the broker (`docker compose restart mqtt-broker`).
- The device-facing MQTT listener (8883) is TLS-encrypted, but the firmware currently calls `setInsecure()` on the TLS client, meaning it encrypts the connection without validating the broker's certificate chain. This is acceptable for a local/private network but should be replaced with proper CA pinning (using the embedded `MQTT_CA_CERT`) before exposing the broker beyond a trusted network.
- Telemetry and status updates are only accepted for bins with `provisioned = TRUE` in the database — always register a bin via the API/dashboard before or immediately after flashing it.

## Testing the Pipeline

`backend/test_pipeline.py` publishes a scripted sequence of MQTT messages that exercises the fill-estimation algorithm's guard rails (transient noise, genuine fill-up, an object shifting away from the sensor, and a genuine empty event):

```bash
pip install paho-mqtt
python backend/test_pipeline.py
```

Watch `docker compose logs -f fill-estimation-service persistence-service alerting-service` while it runs to see each stage of the pipeline react.

## Further Documentation

- [`backend/README.md`](backend/README.md) — microservice-by-microservice breakdown, Redis Stream topology, API reference
- [`frontend/README.md`](frontend/README.md) — dashboard setup, local dev server, environment configuration
- [`firmware/README.md`](firmware/README.md) — wiring diagram, PlatformIO build/flash instructions, device provisioning
