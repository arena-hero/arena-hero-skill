# Tactic authoring

Use this reference for tactic-script mode. Before making any tactical decision,
read the complete bundled rules:

- [Complete Arena Hero v0.6 rules](game-rules.md)

Use the bundled documentation while authoring:

- [Source and version policy](reference-source-and-version.md)
- [Reliable command loop](agent-command-loop.md)
- [Python SDK quickstart](sdk-quickstart.md)
- [Complete Python SDK reference](sdk-reference.md)
- [Complete command API](api-commands.md)
- [Complete state model](api-state-model.md)
- [Resolution results](api-resolution-results.md)
- [Errors and recovery](api-errors.md)

Never infer a numeric rule from an enum name, an old tactic, or general game
knowledge. If the live contract is newer than the bundled v0.6 rules, stop and
update the bundle; do not fill the gap with a plausible constant.

Add a compatible PyPI release through the project's existing dependency
manager. For a standalone script:

```bash
python -m pip install 'arena-hero>=0.2.4,<0.3'
```

Do not install the SDK from a Git repository.

## Build the smallest useful program

Prefer the synchronous client unless the surrounding application already uses
`asyncio`.

```python
import os
from getpass import getpass

from arena_hero import ArenaHeroClient


def choose_actions(turn) -> None:
    # Read this Turn only. Queue at most one action per object.
    ...


def play(api_key: str) -> None:
    with ArenaHeroClient(api_key=api_key) as game:
        for turn in game.turns():
            choose_actions(turn)
            accepted = turn.submit()
            print(f"tick={accepted.tick} accepted={accepted.accepted}")


if __name__ == "__main__":
    play(os.environ.get("ARENA_HERO_API_KEY") or getpass("Arena Hero API key: "))
```

It is also fine for the project to load the key from `.env` or another
repository file and pass it to `play()`.

The SDK receives WebSocket state, reconnects, validates models, submits complete
plans, and safely retries exact request bodies. Do not rebuild those parts.

## Decide in this order

1. **Lifecycle:** `turn.core` can be `None` while respawning. Submit no invented
   actions.
2. **Immediate survival:** react to visible threats and Core damage.
3. **Economy:** use `turn.resources`, Worker cargo, resource cells visible in
   the current Turn, and Core position.
4. **Combat:** attack only visible targets with current positions.
5. **Movement:** avoid visible obstacle cells; remember that fog is not current
   truth.
6. **Champion Beacon:** use only the status and carrier details visible in the
   current state.
7. **Production and migration:** account for costs, upkeep, population, and
   multi-Tick Core movement from the current Core view.

If the requested tactic is underspecified, use a balanced starter policy:

- deposit carried Worker cargo when sharing the Core cell;
- harvest when an empty Worker stands on a resource cell visible in this Turn;
- move Workers toward a currently visible resource or home using a
  deterministic, obstacle-aware choice;
- reconsider a resource target after success or `RESOURCE_DEPLETED`, then use
  the next complete state to see whether a cargo pile remains;
- defend against visible nearby enemies before pursuing distant goals;
- spawn conservatively so expected upkeep does not starve the Core;
- leave an object without an action when no legal useful action is known.

Do not claim this default is optimal.

## Use the typed controls

| Controller | Extra controls |
|---|---|
| Any Unit | `move`, `pickup_beacon`, `drop_beacon`, `wait` |
| Worker | `harvest`, `deposit` |
| Vanguard | `sweep` |
| Ranger | `shoot` |
| Core | `spawn`, `repair_shield`, `start_move`, `cancel_move`, Beacon controls, `wait` |

Use `turn.workers`, `turn.vanguards`, `turn.rangers`, `turn.core`,
`turn.visible_enemies`, `turn.resource_cells`, and `turn.obstacle_cells`.
Controller calls only queue actions. Call `turn.submit()` once after the full
plan is ready. Look up every available client argument, controller method,
model, action, enum, receipt, and exception in
[sdk-reference.md](sdk-reference.md); do not infer an SDK interface from these
examples.

Every later submission for the same Tick replaces the complete earlier Agent
plan. Never assume omitted actions are merged from an earlier submission.

## Recompute resource targets

Treat `turn.resource_cells` as a current visible-resource set, not exploration
memory. Natural nodes disappear after one successful harvest, but a dropped
Worker cargo pile can remain after partial recovery. Pile amounts are not
exposed. When multiple eligible empty Workers act on the same cell, only the lowest raw-byte UUID succeeds and
the others receive `HARVEST_FAILED/RESOURCE_DEPLETED`.

At the start of each decision:

1. process `turn.events` from the previous Tick;
2. use `WORKER_CARGO_DROPPED` and `HARVEST_SUCCEEDED.values.source` to update
   local intent, without inventing a hidden pile amount;
3. replace the visible resource index from `turn.resource_cells`;
4. discard any remembered target whose cell is visible but absent from that
   index;
5. choose again from current visible nodes with deterministic tie-breaking.

Do not wait on an old coordinate for the four-Tick refill. Unharvested nodes
stay put, but harvested nodes do not return in place and newly refilled nodes
are known only when visible.

## Keep decisions testable

Put tactical choices in a function that receives a `Turn`. Test it with
representative `PlayerState` fixtures and a `Turn` whose submitter is a stub.
Cover at least:

- active state and respawning state;
- no visible resource or enemy;
- Worker harvesting and depositing;
- same-cell Worker contention, cargo-pile persistence, and
  `RESOURCE_DEPLETED` retargeting;
- resource disappearance, four-Tick refill, and fog-memory invalidation;
- legal combat target selection;
- obstacle-aware movement;
- no stale controller reuse.

Before live play, run the project's existing tests and:

```bash
python -m compileall -q .
python -m pip check
```

Use the existing formatter, linter, and type checker when present. Search the
diff for credentials and authorization headers before committing.

## Stay inside the command window

The global window is 15 seconds, opens before state publication, and has no
client-visible deadline. Start immediately when a Turn arrives. Precompute
reusable indexes outside the critical path, set a shorter internal budget, and
fall back to a simpler plan when needed.

Use current resolution events to learn from the previous Tick. Treat
`COMMAND_WINDOW_CLOSED` as final for that Tick and wait for fresh state.
