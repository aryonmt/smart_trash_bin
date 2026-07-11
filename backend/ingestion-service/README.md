# Ingestion Service

The network-facing edge of the Smart Waste Bin platform's backend. This service is the sole consumer of the MQTT broker: it terminates all inbound device traffic, enforces schema and identity validation, and republishes clean, trustworthy events onto internal Redis Streams for the rest of the pipeline to consume. No other backend service talks to MQTT directly.

## Role in the Architecture

```
ESP32 Devices ──MQTT/TLS──▶ Mosquitto Broker ──MQTT──▶ Ingestion Service
                                                              │
                                          ┌───────────────────┴───────────────────┐
                                          ▼                                       ▼
                              Redis Stream: raw-telemetry           Redis Stream: device-status
                                          │                                       │
                                          ▼                                       ▼
                              Fill Estimation Service                  Persistence Service
```

This service is intentionally "dumb" about business logic (no fill-percentage math lives here) and intentionally strict about data hygiene. Its only responsibilities are: **subscribe, validate, authenticate the source, and forward.**

## Responsibilities

- Subscribes to two MQTT topic patterns:
  - `wastebin/+/+/telemetry` — periodic sensor readings
  - `wastebin/+/+/status` — Last-Will-and-Testament driven online/offline presence
- Validates every telemetry payload against a strict Pydantic schema before it is allowed anywhere near the rest of the system.
- Enforces an **anti-spoofing guard**: the `device_id`/`zone_id` embedded in the MQTT topic path must match the `device_id`/`zone_id` inside the JSON payload. Any mismatch is logged as a blocked spoofing attempt and the message is dropped, not forwarded.
- Publishes validated events onto Redis Streams (`raw-telemetry`, `device-status`) so that downstream services never need to know MQTT exists.

## Tech Stack

| Component | Choice |
|---|---|
| Language | Python 3.11 |
| MQTT client | `paho-mqtt` 1.6.x |
| Validation | `pydantic` v2 |
| Message bus | Redis Streams (`redis-py`) |
| Container base | `python:3.11-slim` |

## Project Structure

```
ingestion-service/
├── src/
│   ├── config.py             # Environment-driven settings (Settings class)
│   ├── redis_client.py       # Redis connection bootstrapper with retry loop
│   ├── main.py                # Composition root: MQTT client lifecycle & message router
│   ├── models/
│   │   └── telemetry.py       # TelemetryPayload Pydantic schema
│   └── handlers/
│       ├── telemetry.py       # Validation + anti-spoofing + stream publish
│       └── status.py          # Online/offline status normalization + stream publish
├── requirements.txt
└── Dockerfile
```

## Data Contract

### Inbound: MQTT telemetry payload (`wastebin/{zone_id}/{bin_id}/telemetry`)

```json
{
  "device_id": "bin-0142",
  "zone_id": "district-7",
  "distance_cm": 63.4,
  "bin_depth_cm": 150.0,
  "sample_count": 11,
  "uptime_s": 184203
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `device_id` | string | yes | min length 3 |
| `zone_id` | string | no | falls back to the zone segment of the MQTT topic if omitted |
| `distance_cm` | float | yes | `0.0 ≤ x ≤ 1000.0` |
| `bin_depth_cm` | float | no | `100.0 ≤ x ≤ 1000.0`, default `150.0` — carries the physical bin depth so downstream services don't need a database lookup |
| `sample_count` | int | no | `1 ≤ x ≤ 50`, default `11` |
| `uptime_s` | int | yes | `≥ 0` |

### Inbound: MQTT status payload (`wastebin/{zone_id}/{bin_id}/status`)

Plain text body: `"online"` or `"offline"` (retained, delivered via LWT on unexpected disconnect).

### Outbound: `raw-telemetry` Redis Stream entry

Flat field map matching the validated `TelemetryPayload`, ready for `XADD`.

### Outbound: `device-status` Redis Stream entry

```json
{ "device_id": "bin-0142", "zone_id": "district-7", "status": "offline", "timestamp": "1752150900" }
```

## Configuration

All configuration is environment-variable driven (see `src/config.py`):

| Variable | Default | Description |
|---|---|---|
| `MQTT_BROKER` | `localhost` | Hostname of the Mosquitto broker |
| `MQTT_PORT` | `1883` | Broker port. Internal Docker-network traffic uses the unencrypted internal listener; only physical devices connect over the external TLS listener (8883) |
| `MQTT_USER` | *(empty)* | Broker username for this service's own connection |
| `MQTT_PASSWORD` | *(empty)* | Broker password for this service's own connection |
| `REDIS_HOST` | `localhost` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |

## Running Locally

```bash
docker build -t ingestion-service .
docker run --rm \
  -e MQTT_BROKER=mqtt-broker \
  -e MQTT_USER=ingestion_service \
  -e MQTT_PASSWORD=*** \
  -e REDIS_HOST=redis \
  ingestion-service
```

The service loops forever (`client.loop_forever()`), reconnecting to both MQTT and Redis with bounded retry/backoff on startup failures.

## Design Notes

- **Why validate here and not downstream?** Every other service in the pipeline trusts that anything sitting on `raw-telemetry`/`device-status` is well-formed and legitimately sourced. Centralizing validation at the network boundary means the rest of the system can stay simple and assume clean input — a single, auditable trust boundary rather than defensive checks scattered across five services.
- **Why is the anti-spoofing check topic-vs-payload rather than a broker ACL?** It is a defense-in-depth layer on top of (not a replacement for) MQTT broker authentication and per-device ACLs. It specifically protects against a payload that lies about its own identity even when the underlying MQTT session is legitimately authenticated.
- **Fail-open vs fail-closed:** Malformed JSON, schema validation failures, and spoofing attempts are all logged and the message is dropped — the service never crashes on bad input from a single device; a misbehaving bin cannot take down ingestion for the rest of the fleet.
