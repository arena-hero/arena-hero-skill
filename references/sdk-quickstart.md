<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-python` revision `9cfe08821b468002887e5dea2b4bc603a76abe47`: `docs/quickstart.md`.

# Quickstart

The Arena Hero SDK handles the WebSocket connection, command requests, typed
state models, receipts, safe retries, and reconnects. You write the game loop
and decide what every Unit should do.

Python 3.11 or newer is required.

## Install

Install the published release:

```bash
python -m pip install arena-hero
```

The package name is `arena-hero`. The import name is `arena_hero`.

## Synchronous loop

Use `ArenaHeroClient` in a normal Python program:

```python
from getpass import getpass

from arena_hero import ArenaHeroClient, Direction


api_key = getpass("Arena Hero API key: ")

with ArenaHeroClient(api_key=api_key) as game:
    for turn in game.turns():
        for worker in turn.workers:
            if worker.position in turn.resource_cells:
                worker.harvest()
            else:
                worker.move(Direction.RIGHT)

        turn.submit()
```

Action methods only change the plan being built in memory. They do not make
network requests. `turn.submit()` sends the complete queued plan in one command
request.

Calling another action method for the same object before submission replaces
that object's earlier action:

```python
worker.move(Direction.UP)
worker.harvest()  # HARVEST replaces MOVE for this Worker.
```

The context manager closes the HTTP and WebSocket connections when the loop
ends.

## Asynchronous loop

Use `AsyncArenaHeroClient` when your application runs on `asyncio`:

```python
import asyncio
from getpass import getpass

from arena_hero import AsyncArenaHeroClient, Direction


async def play(api_key: str) -> None:
    async with AsyncArenaHeroClient(api_key=api_key) as game:
        async for turn in game.turns():
            for vanguard in turn.vanguards:
                vanguard.sweep(Direction.LEFT)

            await turn.submit()


asyncio.run(play(getpass("Arena Hero API key: ")))
```

The synchronous and asynchronous clients expose the same models and control
methods:

| Synchronous | Asynchronous |
|---|---|
| `ArenaHeroClient` | `AsyncArenaHeroClient` |
| `for turn in game.turns()` | `async for turn in game.turns()` |
| `turn.submit()` | `await turn.submit()` |
| `game.close()` | `await game.close()` |

## API key

Pass the API key directly to the constructor:

```python
game = ArenaHeroClient(api_key="your-api-key")
```

The SDK does not read the API key or endpoint from environment variables. How
your application loads and protects the value before passing it to the client
is up to you. Never commit a real key to source control.

## Read a Turn

Each `Turn` is a complete authoritative state snapshot for one Tick:

```python
turn.tick
turn.state
turn.resources
turn.resource_capacity
turn.resource_space
turn.core
turn.units
turn.workers
turn.vanguards
turn.rangers
turn.visible_enemies
turn.terrain
turn.resource_cells
turn.obstacle_cells
turn.beacon
turn.events
turn.plan
```

Core storage has a minimum capacity of 10, then accepts 5 resources per living
Unit. A partial deposit leaves its remainder on the Worker; a full Core rejects
the deposit without deleting cargo. If population falls, stored resources above
the new capacity are destroyed immediately. Use `turn.resource_space` before
choosing `deposit()`.

Use the filtered collections when possible:

- `turn.workers`, `turn.vanguards`, and `turn.rangers` contain controlled Units.
- `turn.visible_enemies` contains visible enemy Units and Cores.
- Every `CoreView` includes `owner_username`; display it as
  `f"@{core.owner_username}"`. Unit owners remain private.
- `turn.resource_cells` and `turn.obstacle_cells` are ready for membership
  checks.
- `turn.events` contains private resolution results from the previous Tick.

Treat `turn.resource_cells` as current visible availability, not permanent map
data. It includes natural points and cargo piles left by dead Workers, but not
pile amounts. A successful harvest consumes a natural point; a partially
recovered pile remains. Every fourth resolved Tick fills only missing natural
slots back to each chunk's quota. When multiple eligible Workers contest one
cell, only the lowest UUID succeeds and the others receive `HARVEST_FAILED` with
`RESOURCE_DEPLETED`.

Cargo-drop events have typed helpers:

```python
from arena_hero import HarvestSource

for event in turn.events:
    if event.event_type == "WORKER_CARGO_DROPPED":
        print("dropped", event.resource_amount, "at", event.position)
    elif event.harvest_source is HarvestSource.DROPPED_CARGO:
        print("recovered", event.resource_amount, "at", event.position)
```

`turn.core` is `None` only during initial admission or a spawn retry after the
server could not find a legal position. Core destruction has no cooldown and
normally produces a replacement in the same Tick.

## Control every object

```python
from arena_hero import Direction, UnitType


for worker in turn.workers:
    if worker.cargo:
        worker.move(Direction.LEFT)
    else:
        worker.harvest()

for vanguard in turn.vanguards:
    vanguard.sweep(Direction.UP)

for ranger in turn.rangers:
    if turn.visible_enemies:
        ranger.shoot(turn.visible_enemies[0])

if turn.core is not None:
    turn.core.spawn(UnitType.WORKER)

turn.submit()
```

A Ranger hits only when the target resolves 1-3 cells away on the same row,
column, or exact 45-degree diagonal. The SDK queues the shot but leaves this
dynamic rule to the server, so choose targets from the current Turn carefully.

Every controlled Unit and the Core has one action slot. A later action call
replaces the earlier action in that slot.

See [API reference](sdk-reference.md) for every field, control method, event,
model, and exception.

## Complete event stream

Most Agents only need `game.turns()`. Use `game.events()` when you also need Tick
notices or canonical plans submitted by another connected client:

```python
from arena_hero import ArenaHeroClient, Received, Tick, Turn


with ArenaHeroClient(api_key=api_key) as game:
    for event in game.events():
        if isinstance(event, Tick):
            current_tick = event.tick
        elif isinstance(event, Turn):
            event.submit()
        elif isinstance(event, Received):
            print(event.source, event.plan)
```

Use either `events()` or `turns()` on one client, not both at the same time.

The latest current-Tick receipt for each source is also available through
`game.latest_receipts`.

## Local backend

Production is the default. Pass both endpoints explicitly when testing against
a local server:

```python
game = ArenaHeroClient(
    api_key=api_key,
    base_url="http://localhost:8080",
    websocket_url="ws://localhost:8080/api/v1/game/ws",
)
```

The asynchronous constructor accepts the same arguments.

## Before running unattended

- Submit promptly after a Turn arrives; the global command window is already
  running.
- Treat each Turn as a complete replacement, not a patch over an older state.
- Read `turn.events` to learn what happened to the previous commands.
- Do not retain Unit or Core controller objects across Turns.
- Let the SDK safely reconnect transient WebSocket failures.
- Stop and fix credentials or policy violations when the SDK raises a terminal
  authentication error.

For gameplay rules and wire-level API details, read
[doc.arenahero.io](https://doc.arenahero.io/).
