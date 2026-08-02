<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `d7c383f8c317b8c86d6c9ca8e9ac0c50c79d6709`: `docs/api/state-model.md`.

# State model

`state.data` is everything this player can see right now, and each message
replaces the one before it.

<nav className="api-model-nav" aria-label="State model sections">
  <strong>Jump to</strong>
  <a href="#playerstate">PlayerState</a>
  <a href="#champion-beacon">Champion Beacon</a>
  <a href="#world-objects">World objects</a>
  <a href="#visibility">Visibility</a>
  <a href="#updating-state">Updating state</a>
</nav>

## Read a state

| Rule | Client behavior |
|---|---|
| A new message arrives | Replace the previous `PlayerState`. Do not merge arrays. |
| You read an object | Check `kind` first, then read the fields listed for that kind. |
| You need a Core owner | Read `owner_username` and add `@` only when displaying it. |
| You need a Unit owner | `controlled: true` means yours; `false` means a visible enemy. Unit owner identity stays private. |
| A field is missing | Its value is unknown or does not apply. The server does not send `null`. |

```json title="Minimal state message"
{
  "type": "state",
  "data": {
    "status": "ACTIVE",
    "resources": 5,
    "population": 1,
    "population_tier": 0,
    "upkeep_next_tick": 0,
    "champion_beacon": {"position": [0, 0]},
    "objects": [
      {
        "kind": "CORE",
        "id": "2ea3c3dc-42b0-4b92-9754-7558bd4ff834",
        "controlled": true,
        "owner_username": "arena_hero",
        "position": [12, 8],
        "hp": 5,
        "shield": 5,
        "state": "NORMAL"
      },
      {
        "kind": "UNIT",
        "id": "9d3e4941-2816-4a39-a220-df8cd95e877d",
        "controlled": true,
        "position": [11, 8],
        "hp": 2,
        "unit_type": "WORKER",
        "cargo": 0
      }
    ],
    "events": []
  }
}
```

If you want machine-readable definitions, use the
[AsyncAPI schema](asyncapi.yaml).

## PlayerState {#playerstate}

| Field | Format | Required | Meaning |
|---|---|---:|---|
| `status` | `"ACTIVE"` or `"RESPAWNING"` | Yes | Whether the player has an active Core or is waiting for a spawn retry. |
| `respawn_at_tick` | positive int64 | Only when respawning | Tick of the next spawn attempt after a placement failure. |
| `resources` | integer ≥ 0 | Yes | Resources stored by the Core, capped at `max(10, population × 5)`; Worker cargo is separate. |
| `population` | integer ≥ 0 | Yes | Living owned Units; the Core is not counted. |
| `population_tier` | integer ≥ 0 | Yes | `floor(population / 20)`. |
| `upkeep_next_tick` | integer ≥ 0 | Yes | `tier × (tier + 1) / 2` for the current population. Core resources pay first; a deficit damages farthest excess Units while protecting the nearest 19. |
| `champion_beacon` | object | Yes | Public position and, when visible, carrier state. |
| `objects` | array | Yes | Owned entities plus currently visible terrain and enemies. |
| `events` | array | Yes | Resolution results addressed to this player. |

When there is nothing to report, `objects` and `events` come through as empty
arrays rather than going missing. Core destruction normally respawns in the same
Tick, so `RESPAWNING` is published only during initial admission or after the
resolver cannot find a legal spawn. The resource and population fields remain,
but you have no Core until `CORE_RESPAWNED` arrives.

## Champion Beacon {#champion-beacon}

The position is always public. Everything else depends on what you can see.

### Outside vision

```json
{
  "position": [120, 85]
}
```

You know where it is and nothing more — not whether it is lying on the ground or
riding along with someone.

### Visible on the ground

```json
{
  "position": [120, 85],
  "status": "GROUND"
}
```

There is no `carrier_id` here.

### Visible and carried

```json
{
  "position": [120, 85],
  "status": "CARRIED",
  "carrier_id": "9d3e4941-2816-4a39-a220-df8cd95e877d"
}
```

`carrier_id` names the Core or Unit doing the carrying. If the next state leaves
`status` or `carrier_id` out, throw the old value away rather than keeping it
around.

## World objects {#world-objects}

Every entry in `objects` begins with `kind`.

| `kind` | Represents | Identity |
|---|---|---|
| `"CORE"` | One Core | `id` |
| `"UNIT"` | One Worker, Vanguard, or Ranger | `id` |
| `"OBSTACLE"` | All visible obstacle cells | Individual positions |
| `"RESOURCE"` | All visible, currently available resource points | Individual positions |

```js title="Dispatch by kind"
for (const object of state.objects) {
  if (object.kind === 'CORE') handleCore(object);
  else if (object.kind === 'UNIT') handleUnit(object);
  else handleTerrain(object);
}
```

### Terrain

```json
{
  "kind": "OBSTACLE",
  "positions": [[4, 7], [4, 8], [5, 8]]
}
```

| Field | Format | Meaning |
|---|---|---|
| `kind` | `"OBSTACLE"` or `"RESOURCE"` | Visible map-feature type. |
| `positions` | non-empty array of `[x, y]` | Visible cells, sorted by `x` and then `y`. |

All visible positions of one kind arrive in a single entry. If a kind is missing
altogether, none of its positions are currently visible. These batches carry no
`id`, no `controlled`, no HP, and no resource quantity.

`OBSTACLE` positions are permanent terrain. `RESOURCE` positions are current
availability, not permanent terrain memory. They may be natural points or cargo
piles left by dead Workers. One successful harvest consumes a natural point;
a partially recovered cargo pile keeps the same position present. Replenishment
may later create a natural replacement elsewhere in the chunk.

### Core

```json title="Normal Core"
{
  "kind": "CORE",
  "id": "2ea3c3dc-42b0-4b92-9754-7558bd4ff834",
  "controlled": true,
  "owner_username": "arena_hero",
  "position": [12, 8],
  "hp": 5,
  "shield": 4,
  "state": "NORMAL"
}
```

```json title="Moving Core"
{
  "kind": "CORE",
  "id": "2ea3c3dc-42b0-4b92-9754-7558bd4ff834",
  "controlled": true,
  "owner_username": "arena_hero",
  "position": [12, 8],
  "hp": 5,
  "shield": 4,
  "state": "MOVING",
  "move_direction": "RIGHT",
  "move_progress": 2,
  "move_required_ticks": 4,
  "destination": [13, 8]
}
```

| Field | Format | Required |
|---|---|---:|
| `kind` | `"CORE"` | Yes |
| `id` | UUID | Yes |
| `controlled` | boolean | Yes |
| `owner_username` | 3–24 lowercase letters, digits, or underscores | Yes |
| `position` | `[x, y]` | Yes; remains the origin while moving |
| `hp` | integer ≥ 0 | Yes |
| `shield` | integer ≥ 0 | Yes |
| `state` | `"NORMAL"` or `"MOVING"` | Yes |
| `move_direction` | direction string | Moving only |
| `move_progress` | integer ≥ 1 | Moving only |
| `move_required_ticks` | integer ≥ 1 | Moving only; currently `4` |
| `destination` | `[x, y]` | Moving only |

A normal Core has none of the movement fields. Every Core includes its owner's
public username without a leading `@`; display it as `@owner_username`. A visible
enemy Core exposes the same Core fields you would see on your own.

### Unit

```json title="Owned Worker"
{
  "kind": "UNIT",
  "id": "9d3e4941-2816-4a39-a220-df8cd95e877d",
  "controlled": true,
  "position": [11, 8],
  "hp": 2,
  "unit_type": "WORKER",
  "cargo": 1
}
```

| Field | Format | Required |
|---|---|---:|
| `kind` | `"UNIT"` | Yes |
| `id` | UUID | Yes |
| `controlled` | boolean | Yes |
| `position` | `[x, y]` | Yes |
| `hp` | integer ≥ 0 | Yes |
| `unit_type` | `"WORKER"`, `"VANGUARD"`, or `"RANGER"` | Yes |
| `cargo` | integer ≥ 0 | Owned Worker only |

An enemy Worker's cargo is hidden from you. Vanguards and Rangers never carry a
`cargo` field at all, not even your own.

## Visibility {#visibility}

| Data | Included when | Hidden fields |
|---|---|---|
| Owned Core and Units | Always | None from their object format |
| Enemy Core | Its cell is currently visible | Internal owner ID and account details other than `owner_username` |
| Enemy Units | Their cell is currently visible | Owner identity; enemy Worker cargo |
| Obstacles and resource points | Their cells are currently visible | Resource quantity |
| Beacon position | Always | None |
| Beacon status and carrier | Beacon cell is currently visible | Both fields outside vision |

Nothing here carries a last-seen timestamp. Remembered obstacles stay valid, but
remembered resource points can be stale until their cells are visible again. Keep
both kinds of exploration memory apart from current server state and do not treat
an out-of-vision resource coordinate as currently available.

## Updating state {#updating-state}

Rebuild your entity maps from each new state:

```js
const entities = new Map();

for (const object of nextState.objects) {
  if (object.kind === 'CORE' || object.kind === 'UNIT') {
    entities.set(object.id, object);
  }
}
```

The server emits objects in a deterministic order:

1. obstacle batch;
2. resource batch;
3. owned Core;
4. owned Units by UUID;
5. visible enemy Cores by UUID;
6. visible enemy Units by UUID.

Groups with nothing in them are skipped, which is exactly why an array index is
never an object's identity.
