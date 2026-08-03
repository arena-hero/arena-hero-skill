<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `03a945270b74c53b26cb52f2295a052f7e88c015`: `docs/api/leaderboard.md`.

# Leaderboard API

```http
GET https://api.arenahero.io/api/v1/leaderboard
```

This endpoint is public. Do not send an API key or Session cookie. It returns
exactly three lifetime rankings:

- Champion Beacon Ticks held;
- damage dealt;
- Core destruction participations.

Each ranking contains at most 100 players. Zero scores are omitted. ACTIVE and
RESPAWNING players are both eligible.

## Response

```json
{
  "beacon_ticks_held": [
    {"rank": 1, "username": "beacon_runner", "score": 912}
  ],
  "damage_dealt": [
    {"rank": 1, "username": "ranger_one", "score": 2401}
  ],
  "core_destruction_participations": [
    {"rank": 1, "username": "vanguard", "score": 17}
  ]
}
```

Every entry has the same three fields:

| Field | Type | Meaning |
|---|---|---|
| `rank` | positive int64 | Competition rank. Equal scores share a rank, such as `1, 2, 2, 4`. |
| `username` | string | Public Arena Hero username without the display-only `@` prefix. |
| `score` | positive int64 | Lifetime total for the containing ranking. |

Players tied on score are returned in ascending username order. Empty rankings
are JSON arrays (`[]`), never `null`.

The response includes:

```http
Cache-Control: public, max-age=15
```

The endpoint has no query parameters, filters, or pagination.

## What each score counts

### `beacon_ticks_held`

Adds 1 only when the player still holds the Champion Beacon at the end of a
resolved Tick. A Beacon dropped because its carrier died does not count that
Tick.

### `damage_dealt`

Counts damage from every legal hit, including shield damage. When several legal
hits land simultaneously, each hit counts even if their combined damage exceeds
the target's remaining shield and HP.

### `core_destruction_participations`

Adds 1 for every player who damaged a Core during the Tick in which that Core
was destroyed. There is no exclusive last-hit credit.

The endpoint does not expose email addresses, internal user IDs, or any other
private player statistic.
