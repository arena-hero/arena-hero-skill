# Tactic authoring

Use this reference for tactic-script mode. The official documentation remains
authoritative:

- Rules: <https://doc.arenahero.io/rules>
- Reliable command loop: <https://doc.arenahero.io/agent/command-loop>
- Python SDK quickstart: <https://doc.arenahero.io/sdk/quickstart>
- Python SDK reference: <https://doc.arenahero.io/sdk/reference>
- Package: <https://pypi.org/project/arena-hero/>

Read the rule page for every mechanic the tactic uses:

| Mechanic | Required source |
|---|---|
| Unit stats, costs, and attacks | <https://doc.arenahero.io/rules/units> |
| Core actions, population, and upkeep | <https://doc.arenahero.io/rules/core-and-economy> |
| Movement and occupancy | <https://doc.arenahero.io/rules/movement-and-stacking> |
| Targeting and simultaneous combat | <https://doc.arenahero.io/rules/combat> |
| Champion Beacon | <https://doc.arenahero.io/rules/champion-beacon> |

Never infer a numeric rule from an enum name, an old tactic, or general game
knowledge. If a required page is unavailable, omit that rule-dependent behavior
and state the limitation; do not fill the gap with a plausible constant.

Add a compatible PyPI release through the project's existing dependency
manager. For a standalone script:

```bash
python -m pip install 'arena-hero>=0.1.0,<0.2'
```

Do not install the SDK from a Git repository.

## Build the smallest useful program

Prefer the synchronous client unless the surrounding application already uses
`asyncio`.

```python
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
    play(getpass("Arena Hero API key: "))
```

The SDK receives WebSocket state, reconnects, validates models, submits complete
plans, and safely retries exact request bodies. Do not rebuild those parts.

## Decide in this order

1. **Lifecycle:** `turn.core` can be `None` while respawning. Submit no invented
   actions.
2. **Immediate survival:** react to visible threats and Core damage.
3. **Economy:** use `turn.resources`, Worker cargo, resource cells, and Core
   position.
4. **Combat:** attack only visible targets with current positions.
5. **Movement:** avoid visible obstacle cells; remember that fog is not current
   truth.
6. **Champion Beacon:** use only the status and carrier details visible in the
   current state.
7. **Production and migration:** account for costs, upkeep, population, and
   multi-Tick Core movement from the current Core view.

If the requested tactic is underspecified, use a balanced starter policy:

- deposit carried Worker cargo when sharing the Core cell;
- harvest when an empty Worker stands on a resource;
- move Workers toward a visible resource or home using a deterministic,
  obstacle-aware choice;
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
plan is ready.

Every later submission for the same Tick replaces the complete earlier Agent
plan. Never assume omitted actions are merged from an earlier submission.

## Keep decisions testable

Put tactical choices in a function that receives a `Turn`. Test it with
representative `PlayerState` fixtures and a `Turn` whose submitter is a stub.
Cover at least:

- active state and respawning state;
- no visible resource or enemy;
- Worker harvesting and depositing;
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
