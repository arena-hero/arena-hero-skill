<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `21f149e36d8c5c445bca86181af33ed64b738442`: `docs/reference/numbers.md`.

# Rules at a glance

## Timing

| Rule | Value |
|---|---:|
| Global command window | 15 seconds |
| Resource replenishment | every 4 resolved Ticks (about 1 minute) |
| Core migration | 4 logical Ticks per cell |
| Core respawn delay | 20 logical Ticks |
| WebSocket Ping interval | 20 seconds |
| WebSocket Pong timeout | 60 seconds |
| Credential revalidation | approximately 5 seconds |
| Recommended reconnect backoff | 250 ms → 5 seconds, with jitter |

## Core

| Attribute | Value |
|---|---:|
| HP | 5 |
| Shield | 5 |
| Shield cap with Beacon | 10 |
| Vision | 5 |
| Starting resources | 5 |
| Starting Workers | 1 |
| Resource capacity | `max(10, population × 5)` |
| Shield repair | 1 resource → 1 shield |

## Units

| Unit | HP | Vision | Cost | Damage / range |
|---|---:|---:|---:|---|
| Worker | 2 | 3 | 5 | none |
| Vanguard | 4 | 4 | 10 | 1 to adjacent target cell |
| Ranger | 2 | 5 | 12 | 1 at cardinal range 1-3 |

## World

| Rule | Value |
|---|---:|
| Cell capacity | 2 occupying entities |
| Terrain kinds | `EMPTY`, `RESOURCE`, `OBSTACLE` |
| Chunk size | 32×32 |
| Central chunk ring | the 2×2 chunks with `cx, cy ∈ {-1, 0}` |
| Resource quota | `max(2, floor(16 × 8 / (8 + ring)))` per chunk |
| Spawn distance from nearest active Core | 20-30 |
| Coordinate type | signed int64 `[x, y]` |
| Beacon start | `[0, 0]` |

## Economy

```text
axis(c) = c if c >= 0 else -c - 1
ring = axis(cx) + axis(cy)
resource_quota = max(2, floor(16 * 8 / (8 + ring)))
```

One point yields 1 resource to a normal Worker or 2 to a Beacon player's Worker.
Either harvest consumes exactly one point. A same-point tie goes to the lowest
eligible Worker UUID.

A dead Worker drops its complete cargo amount on its final cell. Recovery takes
1 resource normally or up to 2 with the Beacon, never more than the pile holds.
Cargo piles do not count toward the chunk's natural-resource quota.

```text
population = Worker + Vanguard + Ranger
resource_capacity = max(10, population × 5)
tier = floor(population / 20)
upkeep = tier × (tier + 1) / 2
```

Deposits move only what fits. If population falls, stored resources above the
new capacity are destroyed immediately.

| Population | Upkeep |
|---:|---:|
| 0-19 | 0 |
| 20-39 | 1 |
| 40-59 | 3 |
| 60-79 | 6 |
| 80-99 | 10 |
| 100-119 | 15 |

## Commands

| Limit | Value |
|---|---:|
| Idempotency key | 8-128 visible ASCII bytes |
| New submissions per `(player, tick, source)` | 64 |
| Concurrent command bodies per credential kind | 4 |
| WebSocket inbound frame limit | 1024 bytes |
| WebSocket messages | `tick`, `state`, `received` |
| Command sources | `AGENT`, `MANUAL` |
