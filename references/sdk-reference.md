<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-python` revision `906da720fecb12fa6f224163aa3ad384bc399927`: `docs/api-reference.md`.

# API reference

- Package: `arena-hero`
- Import: `arena_hero`
- Python: 3.11 or newer

All public state and command models are typed, immutable Pydantic models. Server
messages are validated before they reach the game loop.

## Clients

### `ArenaHeroClient`

Synchronous client:

```text
ArenaHeroClient(
    *,
    api_key: str,
    base_url: str = "https://api.arenahero.io",
    websocket_url: str | None = None,
    request_timeout: float = 5.0,
    request_retries: int = 2,
    reconnect_min_delay: float = 0.25,
    reconnect_max_delay: float = 5.0,
    max_message_size: int = 2 * 1024 * 1024,
)
```

### `AsyncArenaHeroClient`

Asynchronous client with the same arguments:

```text
AsyncArenaHeroClient(
    *,
    api_key: str,
    base_url: str = "https://api.arenahero.io",
    websocket_url: str | None = None,
    request_timeout: float = 5.0,
    request_retries: int = 2,
    reconnect_min_delay: float = 0.25,
    reconnect_max_delay: float = 5.0,
    max_message_size: int = 2 * 1024 * 1024,
)
```

| Argument | Meaning |
|---|---|
| `api_key` | Required credential sent as `Authorization: Bearer …`. |
| `base_url` | HTTP API base. The command endpoint is derived from it. |
| `websocket_url` | WebSocket endpoint. When omitted, it is derived from `base_url`. |
| `request_timeout` | Timeout in seconds for one HTTP command attempt. |
| `request_retries` | Safe retries after the first HTTP attempt. |
| `reconnect_min_delay` | Initial WebSocket reconnect delay in seconds. |
| `reconnect_max_delay` | Maximum WebSocket reconnect delay in seconds. |
| `max_message_size` | Maximum accepted WebSocket message size in bytes. |

The SDK reads none of these values from environment variables.

### `turns()`

Synchronous:

```text
ArenaHeroClient.turns() -> Iterator[Turn]
```

Asynchronous:

```text
AsyncArenaHeroClient.turns() -> AsyncIterator[AsyncTurn]
```

Yields each actionable Tick once. Receipts are still processed internally and
stored in `latest_receipts`.

### `events()`

Synchronous:

```text
ArenaHeroClient.events() -> Iterator[Tick | Turn | Received]
```

Asynchronous:

```text
AsyncArenaHeroClient.events() -> AsyncIterator[Tick | AsyncTurn | Received]
```

The event types are:

| Event | Meaning |
|---|---|
| `Tick` | A new Tick was announced. There is no state to act on yet. |
| `Turn` / `AsyncTurn` | Complete player state is ready for planning. |
| `Received` | The canonical `AGENT` or `MANUAL` plan was stored. |

Only one `events()` or `turns()` iterator may consume a client at a time.

### `latest_receipts`

Read-only mapping from `CommandSource` to the latest current-Tick `Received`:

```python
from arena_hero import CommandSource


agent_receipt = game.latest_receipts.get(CommandSource.AGENT)
manual_receipt = game.latest_receipts.get(CommandSource.MANUAL)
```

The mapping is cleared when a new Tick begins.

### `submit()`

Submit an already-built complete plan:

```python
accepted = game.submit(plan, idempotency_key="agent-10583-plan-1")
```

Asynchronous:

```python
accepted = await game.submit(plan, idempotency_key="agent-10583-plan-1")
```

The return type is `Accepted`. When no key is provided, the SDK generates one.
A custom key must contain 8–128 visible ASCII bytes without spaces.

If a network failure leaves the result uncertain, the SDK retries the exact
same request bytes with the same idempotency key.

### `close()`

`ArenaHeroClient.close()` closes the active WebSocket and HTTP connection pool.

`await AsyncArenaHeroClient.close()` does the same asynchronously.

Prefer `with` or `async with`, which closes the client automatically.

## Turn

`Turn` and `AsyncTurn` expose the same state and control interface. Their only
difference is that `AsyncTurn.submit()` must be awaited.

### State

| Attribute | Type | Meaning |
|---|---|---|
| `tick` | `int` | Tick this state and plan belong to. |
| `state` | `PlayerState` | Complete authoritative player-state model. |
| `resources` | `int` | Resources currently stored in the Core. |
| `core` | `Core | None` | Controlled Core, or `None` while respawning. |
| `units` | `tuple[Unit, ...]` | All controlled Units. |
| `workers` | `tuple[Worker, ...]` | Controlled Workers. |
| `vanguards` | `tuple[Vanguard, ...]` | Controlled Vanguards. |
| `rangers` | `tuple[Ranger, ...]` | Controlled Rangers. |
| `visible_enemies` | `tuple[UnitView | CoreView, ...]` | Visible enemy objects. |
| `terrain` | `tuple[TerrainView, ...]` | Visible resource and obstacle batches. |
| `resource_cells` | `frozenset[Position]` | Visible natural-resource and dropped-cargo cells. |
| `obstacle_cells` | `frozenset[Position]` | Visible obstacle cells. |
| `beacon` | `ChampionBeacon` | Visibility-limited Beacon view. |
| `events` | `tuple[ResolutionEvent, ...]` | Private results from the previous Tick. |
| `plan` | `CommandPlan` | Complete plan currently queued in memory. |

`Position` is `tuple[int, int]` in `(x, y)` order.

`resource_cells` contains visible natural points and Worker cargo piles, but not
pile amounts. One successful harvest consumes a natural point; a partially
recovered pile remains. Every fourth resolved Tick replenishes only missing
natural chunk slots. Same-cell losers receive `HARVEST_FAILED` with
`RESOURCE_DEPLETED`.

### Methods

#### `unit(unit_id)`

Find a controlled Unit by UUID or UUID string:

```python
worker = turn.unit("9d3e4941-2816-4a39-a220-df8cd95e877d")
```

Raises `InvalidActionError` when the identifier is invalid or does not belong to
a controlled Unit in this Turn.

#### `clear()`

Remove every queued Unit and Core action:

```python
turn.clear()
```

#### `submit(idempotency_key=None)`

Submit the complete queued plan:

```python
accepted = turn.submit()
accepted = turn.submit(idempotency_key="agent-10583-plan-1")
```

Asynchronous:

```python
accepted = await turn.submit()
```

Calling an action on a Turn after a newer Tick arrives raises
`TurnClosedError`. Do not reuse controller objects from an old Turn.

## Unit controls

All controlled Unit objects expose:

| Member | Type or signature |
|---|---|
| `view` | `UnitView` |
| `id` | `UUID` |
| `position` | `Position` |
| `hp` | `int` |
| `unit_type` | `UnitType` |
| `move(direction)` | Queue a one-cell move. |
| `pickup_beacon()` | Pick up the Beacon on the current cell. |
| `drop_beacon()` | Drop a carried Beacon. |
| `self_destruct()` | Remove this Unit before upkeep. Worker cargo drops on the final cell; there is no refund or area damage. |
| `wait()` | Queue an explicit `WAIT`. |
| `clear_action()` | Remove this Unit from the queued plan. |

Every Unit has one action slot. A later method call replaces the action already
queued for that Unit.

### Worker

Extra state:

| Member | Type | Meaning |
|---|---|---|
| `cargo` | `int` | Resources currently carried. |

Extra controls:

| Method | Meaning |
|---|---|
| `harvest()` | Harvest the resource on the current cell. |
| `deposit()` | Deposit cargo while sharing a cell with the Core. |

Any Worker death leaves its complete cargo amount as a recoverable resource pile
on the final cell. For those events, use `event.resource_amount`; a successful
recovery has `event.harvest_source is HarvestSource.DROPPED_CARGO`.

### Vanguard

| Method | Meaning |
|---|---|
| `sweep(direction)` | Attack the adjacent cell in one direction. |

### Ranger

```python
ranger.shoot(target)
ranger.shoot(target_id, expected_cell=(120, 85))
```

`target` may be a visible `Unit`, `Core`, `UnitView`, or `CoreView`. The SDK
copies its UUID and current position into the command.

When passing only a UUID or UUID string, `expected_cell` is required:

```python
from uuid import UUID


target_id = UUID("8d60b600-78d4-4aba-83fd-4e5e27b88c9d")
ranger.shoot(target_id, expected_cell=(120, 85))
```

The server still resolves the shot using the game rules. Building a valid
command does not guarantee a hit.

## Core controls

The `Core` controller exposes:

| Member | Type or signature |
|---|---|
| `view` | `CoreView` |
| `id` | `UUID` |
| `position` | `Position` |
| `hp` | `int` |
| `shield` | `int` |
| `owner_username` | `str` |
| `spawn(unit_type)` | Spawn `WORKER`, `VANGUARD`, or `RANGER`. |
| `repair_shield()` | Spend one resource to repair one shield. |
| `start_move(direction)` | Start moving the Core. |
| `cancel_move()` | Cancel current Core movement. |
| `pickup_beacon()` | Pick up the Beacon on the current cell. |
| `drop_beacon()` | Drop a carried Beacon. |
| `wait()` | Queue an explicit `WAIT`. |
| `clear_action()` | Remove the queued Core action. |

The Core has one action slot. A later method call replaces the earlier action.

## State models

### `PlayerState`

| Field | Type |
|---|---|
| `status` | `PlayerStatus` |
| `respawn_at_tick` | `int | None` |
| `resources` | `int` |
| `population` | `int` |
| `population_tier` | `int` |
| `upkeep_next_tick` | `int` |
| `champion_beacon` | `ChampionBeacon` |
| `objects` | `tuple[TerrainView | CoreView | UnitView, ...]` |
| `events` | `tuple[ResolutionEvent, ...]` |

For field semantics and visibility rules, see the
[public state model](https://doc.arenahero.io/api/state-model).

### `UnitView`

| Field | Type | Meaning |
|---|---|---|
| `kind` | `Literal["UNIT"]` | Object discriminator. |
| `id` | `UUID` | Stable Unit identifier. |
| `controlled` | `bool` | Whether this player controls the Unit. |
| `position` | `Position` | Current visible cell. |
| `hp` | `int` | Current hit points. |
| `unit_type` | `UnitType` | Worker, Vanguard, or Ranger. |
| `cargo` | `int | None` | Present only for a controlled Worker. |

### `CoreView`

| Field | Type | Meaning |
|---|---|---|
| `kind` | `Literal["CORE"]` | Object discriminator. |
| `id` | `UUID` | Stable Core identifier. |
| `controlled` | `bool` | Whether this player controls the Core. |
| `owner_username` | `str` | Public username of the Core owner, without the leading `@`. |
| `position` | `Position` | Current visible cell. |
| `hp` | `int` | Current hit points. |
| `shield` | `int` | Current shield. |
| `state` | `CoreState` | `NORMAL` or `MOVING`. |
| `move_direction` | `Direction | None` | Present while moving. |
| `move_progress` | `int | None` | Completed movement progress. |
| `move_required_ticks` | `int | None` | Required movement duration. |
| `destination` | `Position | None` | Current movement destination. |

Movement fields are either all present for `MOVING` or all absent for `NORMAL`.

### `TerrainView`

| Field | Type | Meaning |
|---|---|---|
| `kind` | `Literal["OBSTACLE", "RESOURCE"]` | Terrain type. |
| `positions` | `tuple[Position, ...]` | Visible cells in this batch. |

### `ChampionBeacon`

| Field | Type | Meaning |
|---|---|---|
| `position` | `Position` | Public Beacon position. |
| `status` | `BeaconStatus | None` | Visible status when available. |
| `carrier_id` | `UUID | None` | Present when a visible carrier holds it. |

### `ResolutionEvent`

| Field | Type |
|---|---|
| `event_id` | `UUID` |
| `tick` | `int` |
| `event_type` | `str` |
| `reason_code` | `str | None` |
| `actor_id` | `UUID | None` |
| `target_id` | `UUID | None` |
| `position` | `Position | None` |
| `values` | `dict[str, Any] | None` |
| `resource_amount` | `int | None` |
| `harvest_source` | `HarvestSource | None` |

Event names and reason codes remain strings so newer server values do not break
an older SDK. See
[resolution results](https://doc.arenahero.io/api/resolution-results) for their
meanings.

`resource_amount` safely reads the positive `amount` from
`WORKER_CARGO_DROPPED` and `HARVEST_SUCCEEDED`. `harvest_source` returns
`HarvestSource.RESOURCE_NODE` or `HarvestSource.DROPPED_CARGO` for a successful
harvest. Both properties return `None` when the event or a future value does not
match.

### `Tick`

| Field | Type | Meaning |
|---|---|---|
| `tick` | `int` | Newly announced Tick number. |

### `Received`

| Field | Type | Meaning |
|---|---|---|
| `tick` | `int` | Tick the stored plan belongs to. |
| `source` | `CommandSource` | `AGENT` or `MANUAL`. |
| `received_at` | timezone-aware `datetime` | Server receipt time. |
| `plan` | `CommandPlan` | Canonical complete stored plan. |

### `Accepted`

| Field | Type | Meaning |
|---|---|---|
| `accepted` | `Literal[True]` | The command request was persisted. |
| `tick` | `int` | Accepted Tick. |
| `source` | `CommandSource` | Always `AGENT` for this SDK. |
| `received_at` | timezone-aware `datetime` | Server receipt time. |

`Accepted` is the HTTP `202` acknowledgement. `Received` is the canonical plan
broadcast through the WebSocket to every connected client for the player.

## Command models

Most code should queue actions through a Turn. Advanced callers can construct
the exact public models:

```python
from uuid import UUID

from arena_hero import CommandPlan, Direction, MoveAction


plan = CommandPlan(
    tick=10583,
    unit_actions={
        UUID("9d3e4941-2816-4a39-a220-df8cd95e877d"): MoveAction(direction=Direction.UP)
    },
)

accepted = game.submit(plan)
```

### `CommandPlan`

| Field | Type | Default |
|---|---|---|
| `tick` | positive `int` | required |
| `unit_actions` | UUIDs mapped to Unit action models | `{}` |
| `core_action` | One Core action model or `None` | `None` |

Each submission is a complete replacement for the source and Tick. The server
does not merge it with an earlier plan.

### Unit actions

| Model | Required data |
|---|---|
| `WaitAction` | none |
| `MoveAction` | `direction` |
| `HarvestAction` | none |
| `DepositAction` | none |
| `SweepAction` | `direction` |
| `ShootAction` | `target_id`, `expected_cell` |
| `PickupBeaconAction` | none |
| `DropBeaconAction` | none |
| `SelfDestructAction` | none |

### Core actions

| Model | Required data |
|---|---|
| `WaitAction` | none |
| `SpawnAction` | `unit_type` |
| `RepairShieldAction` | none |
| `StartMoveAction` | `direction` |
| `CancelMoveAction` | none |
| `PickupBeaconAction` | none |
| `DropBeaconAction` | none |

## Enums

| Enum | Values |
|---|---|
| `Direction` | `UP`, `DOWN`, `LEFT`, `RIGHT` |
| `UnitType` | `WORKER`, `VANGUARD`, `RANGER` |
| `PlayerStatus` | `ACTIVE`, `RESPAWNING` |
| `CoreState` | `NORMAL`, `MOVING` |
| `CommandSource` | `AGENT`, `MANUAL` |
| `BeaconStatus` | `GROUND`, `CARRIED` |
| `HarvestSource` | `RESOURCE_NODE`, `DROPPED_CARGO` |

`Direction.delta` returns the corresponding `(dx, dy)` tuple.

## Errors

All SDK exceptions inherit from `ArenaHeroError`.

| Exception | Meaning |
|---|---|
| `ConfigurationError` | A constructor option or idempotency key is invalid, the client is closed, or two iterators were started. |
| `AuthenticationError` | The WebSocket handshake rejected the API key. |
| `PolicyViolationError` | The WebSocket closed with policy code `1008`. |
| `ProtocolError` | A server message does not match the public protocol. |
| `APIError` | The command API returned a structured rejection. |
| `TransportError` | A network operation still failed after safe retries. |
| `TurnClosedError` | Code tried to change a Turn after it stopped being current. |
| `InvalidActionError` | A local target or action cannot be represented safely. |

`APIError` exposes:

```python
error.status_code
error.error
error.message
error.details
```

Gameplay failures are not Python exceptions. They arrive in the next
`Turn.events` as `ResolutionEvent` values.

## Connection behavior

The SDK:

- sends the API key only in the `Authorization` header;
- never reads credentials or endpoints from environment variables;
- disables WebSocket message compression to match the server;
- handles protocol Ping/Pong;
- reconnects transient WebSocket failures with jittered exponential backoff;
- stops reconnecting after close code `1008`;
- treats every `state` as a complete replacement;
- safely retries uncertain submissions with identical bytes and the same
  idempotency key;
- preserves unknown resolution event names and reason codes as strings.

The server command window is global and may already be partly spent when a Turn
arrives. Build and submit the plan promptly.

For timing, replacement, receipts, and reconnect rules, read
[Reliable command loop](https://doc.arenahero.io/agent/command-loop).

## Complete public export catalog

The `arena_hero` package exports the following public names from its top-level module:

`APIError`, `Accepted`, `ArenaHeroClient`, `ArenaHeroError`, `AsyncArenaHeroClient`, `AsyncGameEvent`, `AsyncTurn`, `AuthenticationError`, `BeaconStatus`, `CancelMoveAction`, `ChampionBeacon`, `CommandPlan`, `CommandSource`, `ConfigurationError`, `Coordinate`, `Core`, `CoreState`, `CoreView`, `DepositAction`, `Direction`, `DropBeaconAction`, `HarvestAction`, `HarvestSource`, `InvalidActionError`, `MoveAction`, `PickupBeaconAction`, `PlayerState`, `PlayerStatus`, `PolicyViolationError`, `Position`, `ProtocolError`, `Ranger`, `Received`, `RepairShieldAction`, `ResolutionEvent`, `SelfDestructAction`, `ShootAction`, `SpawnAction`, `StartMoveAction`, `SweepAction`, `SyncGameEvent`, `TerrainView`, `Tick`, `TransportError`, `Turn`, `TurnClosedError`, `Unit`, `UnitType`, `UnitView`, `Vanguard`, `WaitAction`, `Worker`, `__version__`.
