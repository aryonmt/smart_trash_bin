# Fill Estimation Service

The algorithmic core of the Smart Waste Bin platform. This stateful service converts raw, noisy ultrasonic distance readings into a trustworthy fill-percentage for every bin in the fleet — specifically designed to resist the two failure modes a single-sensor, single-point setup is most vulnerable to: a transient object briefly fooling the sensor, and a settled object later shifting away and appearing to "empty" a bin that was never collected.

## Role in the Architecture

```
Redis Stream: raw-telemetry
        │  (consumer group: estimation-group)
        ▼
Fill Estimation Service ──reads/writes──▶ Redis key: bin_state:{device_id}
        │
        ▼
Redis Stream: bin-fill-updated
        │
        ├──▶ Persistence Service (writes history to TimescaleDB)
        └──▶ Alerting Service (evaluates threshold rules)
```

This is a pure **Clean Architecture** service: the domain layer (`domain/`) has zero knowledge of Redis, streams, or I/O of any kind, and is fully unit-testable in isolation.

## Responsibilities

- Consumes the `raw-telemetry` stream via a Redis Streams consumer group (`estimation-group`), so multiple replicas of this service can safely share the workload without double-processing a reading.
- Maintains one persistent state object per bin (`BinFillState`) in Redis, tracked across measurement cycles.
- Runs the two-guard estimation algorithm (below) to produce a confirmed, monotonic fill percentage.
- Publishes the result onto `bin-fill-updated` for downstream consumers.

## The Estimation Algorithm

Configuration (`BinConfig`) per bin:

| Parameter | Default | Meaning |
|---|---|---|
| `bin_depth_cm` | `150.0` | Physical distance from sensor to bin floor — read dynamically from each telemetry message rather than hardcoded, so bins with non-standard depths are handled correctly out of the box |
| `sensor_blind_zone_cm` | `20.0` | Minimum reliable sensing distance near the sensor |
| `confirm_cycles` | `3` | Consecutive matching cycles required before a candidate reading is trusted |
| `tolerance_cm` | `5.0` | Agreement window used to decide whether a new reading matches the current candidate |
| `empty_ratio_threshold` | `0.90` | Fraction of `bin_depth_cm` that counts as "near empty" |
| `empty_confirm_cycles` | `2` | Consecutive near-empty cycles required to confirm a genuine pickup event |

### Guard 1 — Persistence Guard

A new distance reading is only trusted once it has repeated consistently, within `tolerance_cm`, for `confirm_cycles` consecutive cycles. This defends against a single transient object (e.g. a plastic bag caught momentarily in the sensor's path) being mistaken for a real change in fill level — a one-off reading can never move the confirmed state on its own.

### Guard 2 — Monotonic (Ratchet) Guard

Outside of a confirmed empty event, the estimated fill level is never allowed to decrease. Trash does not remove itself: if an object that was resting near the sensor later shifts away and the raw distance increases, that is treated as sensor noise, not as the bin having been emptied. The confirmed distance can only decrease (fill percentage only increase) through the persistence guard above, and can only reset to a lower fill level through an explicit, repeated near-empty signal.

### Empty-Event Detection

A genuine pickup is only recognized when the raw reading stays at or above `empty_ratio_threshold` of `bin_depth_cm` for `empty_confirm_cycles` consecutive cycles. On confirmation, the bin's state is fully reset to a fresh baseline.

### Fill Percentage Formula

```
usable_depth_cm = bin_depth_cm - sensor_blind_zone_cm
filled_depth_cm = bin_depth_cm - confirmed_distance_cm
fill_percent     = clamp(filled_depth_cm / usable_depth_cm * 100, 0, 100)
```

## Tech Stack

| Component | Choice |
|---|---|
| Language | Python 3.11 |
| Validation / domain models | `pydantic` v2 |
| Message bus | Redis Streams + Redis key-value (state cache) |
| Container base | `python:3.11-slim` |

## Project Structure

```
fill-estimation-service/
├── src/
│   ├── config.py              # Settings, including a per-replica unique consumer name
│   ├── redis_client.py        # Redis connection bootstrapper + consumer group creation
│   ├── domain/
│   │   ├── models.py          # BinFillState, BinConfig (pure data, no I/O)
│   │   └── estimator.py       # estimate_fill() -- the algorithm above, framework-free
│   └── main.py                 # Stream consumer loop / composition root
├── requirements.txt
└── Dockerfile
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `REDIS_HOST` | `localhost` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |

`CONSUMER_NAME` is derived automatically from the container's hostname (`estimator-consumer-{hostname}`), so this service can be scaled to multiple replicas behind the same consumer group without manual configuration or naming collisions.

## Running Locally

```bash
docker build -t fill-estimation-service .
docker run --rm -e REDIS_HOST=redis fill-estimation-service
```

## Scaling

Because state is keyed per-device in Redis (`bin_state:{device_id}`) and consumption is coordinated through a Redis Streams consumer group, this service can be horizontally scaled by simply running more replicas — Redis Streams will distribute pending messages across active consumers in the group automatically.

## Design Notes

- **Why two guards instead of one?** A persistence-only guard would still let a bin appear to "empty itself" if an object shifts away and the reading stabilizes at the new (larger) distance for several cycles. A ratchet-only guard would let a single noisy reading get baked in immediately if it happened to persist by chance. Together, they require *both* consistency *and* a physically plausible direction of change before the confirmed state moves.
- **Why is `bin_depth_cm` read per-message instead of looked up from a database?** It keeps this service fully decoupled from PostgreSQL — it has no database dependency at all — while still respecting per-bin physical differences, since the ingestion layer already carries this value on every telemetry event.
