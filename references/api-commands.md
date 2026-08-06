<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `166ef865a0ceec280b5fd8b9ffff80eb613674c7`: `docs/api/commands.md`.

# Command API

Send one plan after each `state` message:

```http
POST /api/v1/game/commands HTTP/1.1
Host: api.arenahero.io
Authorization: Bearer <token>
Idempotency-Key: agent-10583-plan-01
Content-Type: application/json
```

```json
{
  "tick": 10583,
  "unit_actions": {
    "9d3e4941-2816-4a39-a220-df8cd95e877d": {
      "type": "SHOOT",
      "expected_cell": [120, 85]
    }
  },
  "core_action": {
    "type": "SPAWN",
    "unit_type": "VANGUARD"
  }
}
```

An Agent request replaces that player's current `AGENT` plan. Wait for the `state`
for that Tick before sending it.

## Headers

| Header | Required | Format | What it does |
|---|---:|---|---|
| `Authorization` | Yes | `Bearer <token>` | Identifies the Agent. |
| `Content-Type` | Yes | `application/json` | `charset=utf-8` and other parameters are allowed. |
| `Idempotency-Key` | Yes | 8-128 bytes in ASCII `0x21`-`0x7e` | Identifies this request and its exact body. |

The maximum body size depends on the deployment. Go over it and you get
`413 REQUEST_BODY_TOO_LARGE`.

## Plan body {#commandplan-model}

| Field | JSON type | Required | What to send |
|---|---|---:|---|
| `tick` | integer | Yes | The positive int64 from the latest `tick` message. |
| `unit_actions` | object | No | Unit UUIDs mapped to actions. Use `{}` when no Unit acts. |
| `core_action` | object | No | One Core action. Omit it when the Agent has no Core action. |

Note that `unit_actions` is an object, not an array. Every key has to be the
lowercase, hyphenated UUID of a living Unit you own, and you must never emit
duplicate JSON keys.

### A POST replaces the earlier plan

Say the stored Agent plan currently reads:

```text
Unit A: MOVE
Unit B: HARVEST
```

and the next body contains only:

```text
Unit A: WAIT
```

The stored plan is now `WAIT` for Unit A and nothing at all for Unit B. Unit B
resolves to `WAIT` too, unless Manual supplies an action, because the server does
not carry missing actions over from the previous Agent plan.

## Unit actions

Read `type` first, then send only the fields shown in that row.

| `type` | Unit | JSON | What happens during resolution |
|---|---|---|---|
| `WAIT` | Any | `{"type":"WAIT"}` | The Unit does nothing. |
| `MOVE` | Any | `{"type":"MOVE","direction":"RIGHT"}` | The Unit tries to move one cardinal cell. |
| `HARVEST` | Worker | `{"type":"HARVEST"}` | Consumes the point and loads 1 resource, or 2 while the player holds the Beacon. |
| `DEPOSIT` | Worker | `{"type":"DEPOSIT"}` | Moves as much cargo as fits into the player's Core on the same cell. |
| `SWEEP` | Vanguard | `{"type":"SWEEP","direction":"UP"}` | Deals 1 damage to each enemy entity in the adjacent cell. |
| `SHOOT` | Ranger | `{"type":"SHOOT","expected_cell":[120,85]}` | Fires at that cell from horizontal, vertical, or diagonal range 1-3. An optional `target_id` keeps precision-target behavior. |
| `PICKUP_BEACON` | Any | `{"type":"PICKUP_BEACON"}` | Tries to pick up the ground Beacon on the actor's cell. |
| `DROP_BEACON` | Any | `{"type":"DROP_BEACON"}` | The current carrier tries to drop the Beacon. |
| `HEAL` | Any | `{"type":"HEAL"}` | After combat, restores HP at 1 Core resource per HP while at the owned stationary Core. |
| `SELF_DESTRUCT` | Any | `{"type":"SELF_DESTRUCT"}` | Removes this Unit before movement and before spawn pricing. |

### Moving

`direction` has to be `UP`, `DOWN`, `LEFT`, or `RIGHT`.

Terrain, other movement, occupancy, swaps, dependencies, and cell capacity are all
checked at resolution rather than on submission. When a move fails, the next state
carries `UNIT_MOVE_FAILED`.

### Harvesting and depositing

Only a Worker can do either of these.

- `HARVEST` needs an empty Worker on a `RESOURCE` cell.
- One successful harvest consumes that point.
- If multiple eligible empty Workers harvest the same point in one Tick, only
  the lowest Worker UUID in raw-byte order succeeds. Every other contender gets
  `HARVEST_FAILED` with `RESOURCE_DEPLETED`.
- Beacon ownership changes the winner's cargo from 1 to 2; it does not consume a
  second point or change the UUID tie-break.
- Consumed points disappear from current state. Every four resolved Ticks, each
  chunk deterministically fills only its missing slots back to its fixed quota.
- `DEPOSIT` needs a Worker with cargo and its own Core on the same cell.
- A Core cannot receive a deposit during a migration-restricted Tick.
- Core capacity is `max(10, population × 5)`. A partial deposit leaves the remainder on
  the Worker.
- A full Core returns `DEPOSIT_FAILED` with
  `CORE_RESOURCE_FULL`.
- A failed deposit leaves all cargo where it was, on the Worker.

### Sweeping

`SWEEP` hits the adjacent cell in `direction`, dealing 1 damage to every enemy Unit
and Core standing there. Sweeping an empty cell still counts as a success, and
reports `targets_hit: 0`.

### Shooting

A shot always needs `expected_cell`; `target_id` is optional:

| Field | Format | Meaning |
|---|---|---|
| `expected_cell` | `[x, y]` | The cell where the Ranger fires. |
| `target_id` | UUID, optional | Keep tracking only this Unit or Core instead of selecting by cell. |

Movement resolves first. For a cell shot, the server chooses the lowest-HP
hostile then standing at `expected_cell`, breaking ties by raw UUID order. An
empty cell misses. When `target_id` is present, only that object can be hit, and
it must still be hostile and at `expected_cell`. In both modes the cell must be
on the same row, column, or exact 45-degree diagonal, at range 1-3, with no
obstacle on an intermediate shot cell. Relative offset `(3, 3)` is range 3;
`(2, 1)` is not aligned. Units, Cores, and obstacles beside a diagonal do not
block the shot.

Every dynamic failure comes back as the same event:
`{"event_type":"SHOT_MISSED","reason_code":"SHOT_MISSED"}`. A cell-shot miss
omits `target_id`; a hit reports the actual target chosen by the server.

### Picking up and dropping the Beacon

Any Unit can use both Beacon actions.

- For a pickup, the ground Beacon has to be on the actor's own cell.
- Only the current carrier can drop it.
- A living carrier cannot be robbed.
- When several actors reach for it, the lowest UUID in raw byte order wins.
- A Beacon that was already carried at the start of a Tick cannot be dropped and picked up again within that same Tick.

### Self-destructing a Unit

`SELF_DESTRUCT` has no other fields. It resolves before movement, removes the Unit,
and consumes its action for the Tick. There is no resource refund and no damage
to nearby objects. Worker cargo drops on that cell. If the Unit carries the Beacon, it
drops on that cell and remains unavailable for pickup until the next Tick.
The Worker owner also receives `WORKER_CARGO_DROPPED` with the dropped amount.

### Healing a Unit

`HEAL` has no other fields and consumes the Unit's complete action. At
resolution the Unit must still be alive on the same cell as its own stationary
Core. After combat it spends one Core resource per missing HP, up to full HP or
the available balance. Unit heals resolve in Unit UUID order before the Core
action. Full HP, no resources, a different cell, or a moving Core are dynamic
failures: the stored plan remains valid and no resource is spent.

## Core actions

| `type` | JSON | What happens during resolution |
|---|---|---|
| `WAIT` | `{"type":"WAIT"}` | No new Core action. An existing migration continues. |
| `SPAWN` | `{"type":"SPAWN","unit_type":"WORKER"}` | Pays the cost and creates one Unit on the Core cell. |
| `HEAL` | `{"type":"HEAL"}` | After combat, spends 1 resource per missing Core HP, up to full HP. |
| `REPAIR_SHIELD` | `{"type":"REPAIR_SHIELD"}` | Pays 1 resource to restore 1 shield, up to the current cap. |
| `START_MOVE` | `{"type":"START_MOVE","direction":"LEFT"}` | Starts a four-Tick migration to an adjacent empty cell. |
| `CANCEL_MOVE` | `{"type":"CANCEL_MOVE"}` | Stops the current migration and clears its progress. |
| `PICKUP_BEACON` | `{"type":"PICKUP_BEACON"}` | A normal Core tries to pick up the Beacon on its cell. |
| `DROP_BEACON` | `{"type":"DROP_BEACON"}` | A carrier Core tries to drop the Beacon. |
| `SELF_DESTRUCT` | `{"type":"SELF_DESTRUCT"}` | After combat, destroys the surviving Core, its inventory, and all owned Units, then enters the normal respawn flow. |

`unit_type` has to be `WORKER`, `VANGUARD`, or `RANGER`. Their base prices are
5, 10, and 12 resources. At population `N`, the server charges
`round_half_up(base_price × (13/10)^k)`, where
`k = max(0, floor((N - 20) / 5) + 1)`. The 20th Unit is base-priced; the 21st
uses the first 30% increase. Population is measured after same-Tick
self-destruction and combat deaths. Read `CORE_SPAWN_SUCCEEDED.values.cost` or
`CORE_SPAWN_FAILED.values.required` for the actual settled price.

A migrating Core can carry on with `WAIT`, stop with `CANCEL_MOVE`, or queue
`SELF_DESTRUCT`; anything else fails with `CORE_ALREADY_MOVING`. A self-destruct
has no resource, Unit, movement-state, or cooldown restriction. Movement and
combat resolve first. A lethal enemy attack keeps normal credit and resource
capture; otherwise the surviving Core destroys its inventory and fleet, drops
Worker cargo and the Beacon at their actual positions, and immediately enters
the normal respawn flow without awarding loot. In the other direction,
`CANCEL_MOVE` on a Core that is not moving fails with `CORE_NOT_MOVING`.

Unit healing resolves before the Core action. The Core action then uses whatever
resources remain, including inventory captured from an enemy Core during that
combat Tick. Core healing, shield repair, and spawning all happen after combat;
they cannot change combat that has already resolved.

## Extra fields make an action invalid

An action may contain only the fields listed for its own `type`. Every one of these
rejects the whole plan:

```json
{"type":"WAIT","direction":"UP"}
{"type":"HARVEST","target_id":null}
{"type":"MOVE","direction":"UP","expected_cell":[1,2]}
{"type":"SPAWN","unit_type":"WORKER","direction":""}
```

You will usually see the validation reason `UNEXPECTED_ACTION_FIELDS`.

## Accepted response

```http
HTTP/1.1 202 Accepted
Content-Type: application/json; charset=utf-8
```

```json
{
  "accepted": true,
  "tick": 10583,
  "source": "AGENT",
  "received_at": "2026-07-27T05:40:06.241Z"
}
```

`202` means stored, not successful. The WebSocket
[`received`](api-websocket.md#received) message carries the plan the server actually
stored, and the next [`state.events`](api-resolution-results.md) carries the action
results.

A rejected request changes nothing — the last valid plan stays in place.

## Safe retries

An idempotency key is 8-128 visible ASCII bytes (`0x21`-`0x7e`). No spaces, tabs,
or line breaks.

| What you send | What the server does |
|---|---|
| Same key and byte-for-byte identical body | Returns the stored response. It does not store or broadcast the plan again. |
| Same key and equivalent JSON with different whitespace or key order | Returns `409 IDEMPOTENCY_CONFLICT`. |
| Same key and different data | Returns `409 IDEMPOTENCY_CONFLICT`. |
| New key | Handles it as a new plan replacement. |

If the connection drops after upload and you have no idea whether it landed, retry
the exact same bytes under the same key. Only reach for a new key once you have
genuinely made a new plan.

## What the server checks

```text
authentication
-> concurrent body limit
-> media type and Idempotency-Key
-> body size and JSON shape
-> Tick window and request rate
-> Unit and Core action fields
-> store the replacement plan
-> return 202 and send received
-> resolve the game
-> send results in the next state.events
```

Any error before the store step rejects the whole body. A failure later, during
game resolution, neither brings back an older plan nor changes the `202` you
already got.

## Concurrency and rate limits

- The server reads at most four command bodies at once for one
  `(player, credential kind)`. Anything beyond that gets
  `429 COMMAND_CONCURRENCY_LIMIT` with `Retry-After: 1`.
- One `(player, Tick, source)` gets at most 64 new admissions after the idempotency
  check, and invalid commands count toward it. Beyond that you get
  `429 COMMAND_RATE_LIMITED`.
- Valid requests for the same plan slot are handled in gate-entry order, and the
  last successful plan replaces the one before it.

For every HTTP error and validation reason, see
[Errors and recovery](api-errors.md).
