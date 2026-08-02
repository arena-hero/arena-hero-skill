<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `ad6fc27a28727617858abc7cbb6832e7653ba3a9`: `docs/api/resolution-results.md`.

# Resolution results

HTTP `202` means the server stored a plan, nothing more — the actions have not
resolved yet. Their results turn up in the next `state.data.events` array.

Start from `event_type`, then read the fields listed for that event:

```json
{
  "event_id": "3f360e7e-d9bd-4f48-9a51-5cf751b04075",
  "tick": 10583,
  "event_type": "UNIT_MOVE_FAILED",
  "reason_code": "MOVE_BLOCKED_TERRAIN",
  "actor_id": "9d3e4941-2816-4a39-a220-df8cd95e877d",
  "position": [120, 85]
}
```

| Looking for | Go to |
|---|---|
| Unit self-destruction | [Unit lifecycle events](#unit-lifecycle-events) |
| HP recovery | [Healing events](#healing-events) |
| Upkeep, Core damage, repair, or spawning | [Economy and Core events](#economy-and-core-events) |
| Harvesting or depositing | [Worker events](#worker-events) |
| Sweeps, shots, and damage | [Combat events](#combat-events) |
| Unit movement or Core migration | [Movement events](#movement-events) |
| Beacon actions or respawning | [Beacon and respawn events](#beacon-and-respawn-events) |

## Field rules

| Field | Presence and meaning |
|---|---|
| `event_id` | Always present. Use this UUID to avoid processing the same event twice after reconnecting. |
| `tick` | Always present. Tick in which the result was resolved. |
| `event_type` | Always present. Read this before the other optional fields. |
| `reason_code` | Present only when the event has a defined reason. Successful events do not send an empty string. |
| `actor_id` | The player's Core or Unit whose action produced the result, when there is one. |
| `target_id` | The affected Core or Unit, when exposing it is part of the result. |
| `position` | Cell relevant to the resolved result. Its exact meaning is stated in each catalog row. |
| `values` | Event-specific object. Keys are stable per event row; the object is omitted when no values apply. |

Optional fields that do not apply are left out rather than sent as `null`.

## Unit lifecycle events

| `event_type` | `reason_code` | IDs and position | `values` | Meaning |
|---|---|---|---|---|
| `UNIT_SELF_DESTRUCTED` | absent | `actor_id`: removed Unit; `position`: its final cell | absent | The owner deliberately removed the Unit before upkeep. |
| `WORKER_CARGO_DROPPED` | absent | `actor_id`: dead Worker; `position`: its final cell | `{amount: int}` | The Worker's complete cargo amount was added to the resource pile on this cell. |

Self-destruction also increments the owner's `units_lost`. It creates no attack
damage or destruction participation. A Beacon carrier additionally receives
`BEACON_DROPPED_ON_DEATH`.

## Healing events

| `event_type` | `reason_code` | IDs and position | `values` | Meaning |
|---|---|---|---|---|
| `UNIT_HEAL_SUCCEEDED` | absent | `actor_id`: healed Unit; `position`: shared Core cell | `{amount: int, hp: int, cost: int}` | The Unit recovered `amount` HP, now has `hp`, and spent the equal `cost`. |
| `UNIT_HEAL_FAILED` | `HP_FULL`, `NOT_AT_OWN_CORE`, `CORE_MOVING`, or `INSUFFICIENT_RESOURCES` | `actor_id`: Unit; `position`: Unit cell | absent | Post-combat Unit healing could not start; nothing was spent. |
| `CORE_HEAL_SUCCEEDED` | absent | `actor_id`: healed Core; `position`: Core cell | `{amount: int, hp: int, cost: int}` | The Core recovered `amount` HP, now has `hp`, and spent the equal `cost`. |
| `CORE_HEAL_FAILED` | `HP_FULL` or `INSUFFICIENT_RESOURCES` | `actor_id`: Core; `position`: Core cell | absent | Post-combat Core healing could not start; nothing was spent. |

A Unit killed during combat is gone before the healing phase, so it produces no
heal event and spends no resource. `unit_hp_recovered` and `core_hp_recovered`
count actual HP restored over the player's lifetime.

## Economy and Core events

| `event_type` | `reason_code` | IDs and position | `values` | Meaning |
|---|---|---|---|---|
| `UPKEEP_PAID` | absent | `actor_id`: Core; `position`: Core cell | `{due: int, paid: int, deficit: int}` | Upkeep was collected. A positive deficit is then applied as Core damage. |
| `CORE_DAMAGED` | `ATTACK` or `UPKEEP_DEFICIT` | `target_id`: Core; `position`: Core cell | `{damage: int, shield_damage: int, hp_damage: int}` | Total Core damage and how it was split between shield and HP. |
| `CORE_DESTROYED` | `ATTACK` or `UPKEEP_DEFICIT` | `target_id`: destroyed Core; `position`: destruction cell | For an attack with named participants: `{destroyed_by: string[]}`; otherwise absent | The player's Core and remaining Units were removed. A replacement spawn is attempted later in the same Tick. |
| `CORE_RESOURCE_OVERFLOW_DESTROYED` | absent | `actor_id`: Core; `position`: Core cell | `{amount: int, capacity: int}` | Population fell and resources above the new capacity were destroyed. |
| `CORE_RESOURCES_CAPTURED` | absent | `actor_id`: winner's surviving Core; `target_id`: destroyed Core; `position`: destruction cell | `{amount: int, available: int, destroyed: int, capacity: int}` | The highest-damage player stored `amount` from the victim's `available` inventory; `destroyed` did not fit. `amount` may be zero. No event is emitted if the winner's Core also died. |
| `CORE_ACTION_FAILED` | `CORE_NOT_MOVING` or `CORE_ALREADY_MOVING` | `actor_id`: Core; `position`: Core cell | absent | `CANCEL_MOVE` was used on a normal Core, or an incompatible Core action was used during migration. |
| `CORE_REPAIR_FAILED` | `SHIELD_FULL` or `INSUFFICIENT_RESOURCES` | `actor_id`: Core; `position`: Core cell | absent | One-shield repair could not be applied. |
| `CORE_REPAIR_SUCCEEDED` | absent | `actor_id`: Core; `position`: Core cell | `{shield: int, cost: int}` | Shield after repair and resources spent. |
| `CORE_SPAWN_FAILED` | `CELL_UNIT_LIMIT` | `actor_id`: Core; `position`: Core cell | `{limit: int}` | Core cell has reached the occupiable-entity limit. |
| `CORE_SPAWN_FAILED` | `INSUFFICIENT_RESOURCES` | `actor_id`: Core; `position`: Core cell | `{required: int}` | Resources are below the selected Unit's cost. |
| `CORE_SPAWN_FAILED` | `DETERMINISTIC_ID_COLLISION` | `actor_id`: Core; `position`: Core cell | absent | Defensive collision check rejected the deterministic spawn ID. |
| `CORE_SPAWN_SUCCEEDED` | absent | `actor_id`: Core; `target_id`: new Unit; `position`: Core cell | `{unit_type: UnitType, cost: int}` | One Unit was created on the Core cell. |

`destroyed_by` lists participant usernames in a deterministic order. You only see
it for an attack, and only when at least one participant can be named.

## Worker events

| `event_type` | `reason_code` | IDs and position | `values` | Meaning |
|---|---|---|---|---|
| `DEPOSIT_FAILED` | `WORKER_EMPTY` | `actor_id`: Worker; `position`: Worker cell | absent | Worker has no cargo. |
| `DEPOSIT_FAILED` | `CORE_NOT_PRESENT` | `actor_id`: Worker; `position`: Worker cell | absent | Owned Core is absent or not on the same cell. |
| `DEPOSIT_FAILED` | `CORE_MOVING` | `actor_id`: Worker; `target_id`: Core; `position`: Worker cell | absent | The colocated Core is migration-restricted this Tick. |
| `DEPOSIT_FAILED` | `CORE_RESOURCE_FULL` | `actor_id`: Worker; `target_id`: Core; `position`: shared cell | `{capacity: int}` | The Core is full at `max(10, population × 5)`; cargo is unchanged. |
| `DEPOSIT_SUCCEEDED` | absent | `actor_id`: Worker; `target_id`: Core; `position`: shared cell | `{amount: int, capacity: int, remaining: int}` | `amount` entered Core storage and `remaining` stayed on the Worker. |
| `HARVEST_FAILED` | `NOT_RESOURCE_CELL` | `actor_id`: Worker; `position`: Worker cell | absent | Current terrain is not a resource cell. |
| `HARVEST_FAILED` | `CARGO_FULL` | `actor_id`: Worker; `position`: Worker cell | absent | Worker already carries resources. |
| `HARVEST_FAILED` | `RESOURCE_DEPLETED` | `actor_id`: Worker; `position`: consumed point | absent | Another eligible empty Worker with a lower UUID won this same point in the Tick. |
| `HARVEST_SUCCEEDED` | absent | `actor_id`: Worker; `position`: resource cell | `{amount: int, source: "RESOURCE_NODE" or "DROPPED_CARGO"}` | Cargo was loaded from a natural point or recovered from a Worker cargo pile. |
| `BEACON_HARVEST_BONUS` | absent | `actor_id`: Worker; `position`: Worker cell | `{amount: int}` | Bonus portion of the harvest granted by carrying the Beacon. |

For every resource position, all eligible empty Workers are ordered by UUID raw
bytes. Only the lowest UUID succeeds and consumes the point. All other contenders
receive `RESOURCE_DEPLETED`, even if their player holds the Beacon. Replenishment
does not create player events; later complete states expose newly available
points only when they are visible.

Recovering `DROPPED_CARGO` never takes more than the pile contains and does not
increment `resources_harvested` or `beacon_bonus_resources_harvested`.

## Combat events

| `event_type` | `reason_code` | IDs and position | `values` | Meaning |
|---|---|---|---|---|
| `SWEEP_RESOLVED` | absent | `actor_id`: Vanguard; `position`: swept adjacent cell | `{targets_hit: int}` | Sweep resolved; `0` is a valid result. |
| `SHOT_MISSED` | always `SHOT_MISSED` | `actor_id`: Ranger; `target_id`: requested UUID; `position`: submitted `expected_cell` | absent | Shot failed dynamically. The detailed cause is intentionally hidden. |
| `SHOT_HIT` | absent | `actor_id`: Ranger; `target_id`: hit Core or Unit; `position`: target cell | `{damage: int}` | Valid shot contributed damage. |
| `UNIT_DAMAGED` | `ATTACK` | `target_id`: damaged Unit; `position`: Unit cell | `{damage: int, hp: int}` | Aggregated damage and HP after damage, clamped to `0`. `hp: 0` means the Unit was destroyed. |
| `DESTRUCTION_PARTICIPATION` | `UNIT` or `CORE` | `target_id`: destroyed object; `position`: destruction cell | absent | This player contributed at least one damage to the destroyed object. |

The victim never gets a separate `UNIT_DESTROYED` event. Detect a kill from
`UNIT_DAMAGED.values.hp === 0`, together with the Unit's absence from the new
complete state.

Every dynamic Ranger failure carries the same `SHOT_MISSED` reason — a missing or
moved target, a friendly target, bad range, an obstacle-blocked line, all of them. The
result is designed to reveal nothing about hidden state.

## Movement events

| `event_type` | `reason_code` | IDs and position | `values` | Meaning |
|---|---|---|---|---|
| `UNIT_MOVE_SUCCEEDED` | absent | `actor_id`: Unit; `position`: destination | absent | Unit completed its one-cell move. |
| `UNIT_MOVE_FAILED` | See Unit movement reasons | `actor_id`: Unit; `position`: unchanged origin | absent | Unit stayed at its origin. |
| `CORE_MOVE_STARTED` | absent | `actor_id`: Core; `position`: origin | `{destination: Position, progress: int, required: int}` | A migration began. Current values are progress `1`, required `4`. |
| `CORE_MOVE_PROGRESS` | absent | `actor_id`: Core; `position`: origin | `{progress: int, required: int}` | Existing migration advanced but did not yet move the Core. |
| `CORE_MOVE_SUCCEEDED` | absent | `actor_id`: Core; `position`: destination | absent | Final migration Tick moved the Core. |
| `CORE_MOVE_FAILED` | See resolved movement reasons | `actor_id`: Core; `position`: unchanged origin | absent | Final migration move failed; Core returns to `NORMAL`. |
| `CORE_MOVE_START_FAILED` | See start reasons | `actor_id`: Core; `position`: origin | absent | `START_MOVE` failed before migration state began. |
| `CORE_MOVE_CANCELLED` | absent | `actor_id`: Core; `position`: origin | absent | Existing migration was cancelled and Core returned to `NORMAL`. |

Unit movement reasons:

- `MOVE_OUT_OF_BOUNDS`: signed int64 coordinate overflow would occur;
- `MOVE_BLOCKED_TERRAIN`: destination is obstacle terrain;
- `MOVE_CONTESTED`: different owners claimed the same destination;
- `MOVE_SWAP_BLOCKED`: two hostile entities attempted a two-way swap;
- `MOVE_DESTINATION_OCCUPIED`: a hostile occupant is not successfully leaving;
- `MOVE_DEPENDENCY_FAILED`: a required departure failed;
- `CELL_UNIT_LIMIT`: the destination would exceed the entity limit.

`CORE_MOVE_FAILED` can use
`CORE_DESTINATION_TERRAIN_BLOCKED`, `MOVE_CONTESTED`,
`MOVE_SWAP_BLOCKED`, `MOVE_DESTINATION_OCCUPIED`,
`MOVE_DEPENDENCY_FAILED`, or `CELL_UNIT_LIMIT`.

`CORE_MOVE_START_FAILED` can use
`CORE_DESTINATION_OUT_OF_BOUNDS`,
`CORE_DESTINATION_TERRAIN_BLOCKED`,
`CORE_DESTINATION_OCCUPIED`, or `CELL_UNIT_LIMIT`.

## Beacon and respawn events

| `event_type` | `reason_code` | IDs and position | `values` | Meaning |
|---|---|---|---|---|
| `BEACON_PICKUP_FAILED` | `CORE_MOVING`, `ALREADY_CARRIED`, or `BEACON_NOT_PRESENT` | `actor_id`: Core or Unit; `position`: actor cell | absent | Pickup could not be completed. |
| `BEACON_PICKED_UP` | absent | `actor_id`: new carrier; `position`: pickup cell | absent | Actor became the carrier. |
| `BEACON_DROP_FAILED` | `CORE_MOVING` or `NOT_BEACON_CARRIER` | `actor_id`: Core or Unit; `position`: actor cell | absent | Drop could not be completed. |
| `BEACON_DROPPED` | absent | `actor_id`: former carrier; `position`: drop cell | absent | Voluntary drop completed. |
| `BEACON_DROPPED_ON_DEATH` | absent | `actor_id`: destroyed carrier; `position`: death cell | absent | Beacon automatically moved to the ground. |
| `RESPAWN_DELAYED` | `NO_LEGAL_SPAWN` | no IDs or position | absent | No legal deterministic spawn candidate was found; next attempt is one Tick later. |
| `CORE_RESPAWNED` | absent | `target_id`: new Core; `position`: spawn cell | `{resources: int, workers: int}` | Player became `ACTIVE` with starting resources and Workers. |

## Decoding example

```js
function applyEvent(event) {
  switch (event.event_type) {
    case 'UNIT_MOVE_FAILED':
      markUnitBlocked(event.actor_id, event.position, event.reason_code);
      break;
    case 'CORE_SPAWN_SUCCEEDED':
      registerSpawn(
        event.target_id,
        event.position,
        event.values.unit_type,
      );
      break;
    case 'SHOT_MISSED':
      // The protocol does not reveal why it missed.
      break;
  }
}
```

Replace your old objects with the new `state.objects`. Events are there to
explain how the new state came about — do not replay them as patches against the
old one.
