# Arena Hero v0.5 game rules

This is the complete gameplay contract bundled with the Arena Hero skill. Read
the whole file before writing a tactic or controlling a live Turn.

This contract was reviewed against Arena Hero server revision
`bc16014cb039c34238bdef0f556219d6638ba4cc` on 30 July 2026.
If a live server reports newer or incompatible rules, stop rule-dependent play
and update this bundle instead of mixing versions.

This reference covers gameplay mechanics. Account registration, OAuth, private
statistics, API-key management, and operator procedures are intentionally
outside its scope.

## Contents

1. [World and terrain](#world-and-terrain)
2. [Tick lifecycle and resolution order](#tick-lifecycle-and-resolution-order)
3. [Vision and information boundaries](#vision-and-information-boundaries)
4. [Core, production, migration, and upkeep](#core-production-migration-and-upkeep)
5. [Units and actions](#units-and-actions)
6. [Movement and cell capacity](#movement-and-cell-capacity)
7. [Champion Beacon](#champion-beacon)
8. [Combat](#combat)
9. [Core destruction and respawn](#core-destruction-and-respawn)
10. [Commands, priority, replacement, and receipts](#commands-priority-replacement-and-receipts)

## World and terrain

### Persistent shared world

- Every player shares one permanent two-dimensional square-grid world.
- There are no seasons, match resets, final winner, NPCs, monsters, or
  server-controlled fleets.
- A player owns at most one living Core at a time.
- Each Unit and each generation of a Core has a non-enumerable UUID. The UUID
  remains stable while the object lives and is never reused after death.
- Enemy state never includes the owning account ID, email address, or username.
- A player activated during resolution is not inserted into a half-resolved
  snapshot. The server assigns a persistent activation Tick and processes the
  player's first spawn through the deterministic respawn resolver.

### Terrain kinds

Every cell has exactly one terrain kind:

| Terrain | Units may enter | Core may migrate into it | Blocks vision | Blocks Ranger fire |
|---|---:|---:|---:|---:|
| `EMPTY` | yes | yes | no | no |
| `RESOURCE` | yes | no | no | no |
| `OBSTACLE` | no | no | yes | yes |

Cores and Units occupy cells but are not terrain. Obstacles and the chunk
backbone are permanent. Resource nodes are dynamic: one successful harvest
removes the node and changes that cell back to `EMPTY`.

### Deterministic infinite generation

- The map is generated in 32 x 32 chunks.
- Generation uses a permanent secret world seed and a versioned HMAC-SHA256
  contract. Clients never receive the seed.
- The same seed, generator version, balance, and coordinates always produce the
  same permanent obstacle and backbone layout.
- Neighboring chunks have deterministic shared boundary passages.
- Every passable pocket connects to the chunk backbone, although one-cell
  chokepoints are allowed.
- `[0, 0]` and its route to the chunk backbone are always `EMPTY`, so the
  Champion Beacon cannot be walled off by generation.
- A Core spawn cell has at least two passable cardinal neighbors.
- A generator-contract mismatch prevents the service from starting. A resource
  contract migration is the exception described below: it preserves world and
  player state while replacing the legacy resource layout.

### Dynamic resource-node quota

Resources use a per-chunk quota. For chunk coordinate `c`, define:

```text
axis(c) = c       when c >= 0
axis(c) = -c - 1  when c < 0

ring(cx, cy) = axis(cx) + axis(cy)
quota(cx, cy) = max(2, floor(16 * 8 / (8 + ring(cx, cy))))
```

The four chunks with `cx` and `cy` each in `{-1, 0}` form ring 0 and each has a
quota of 16 nodes. Quotas decline with the summed ring and never fall below 2.
Chunk size remains 32 x 32.

After settlement of every fourth logical Tick, the server counts the resource
nodes still present in each tracked chunk and adds only the missing number:

```text
missing = max(0, quota(cx, cy) - current_nodes)
```

Unharvested nodes stay at their current positions. They do not move, age,
duplicate, or accumulate above the quota. A successful harvest removes one node
immediately during the Worker phase; refill happens only at the four-Tick
boundary after all ordinary Tick resolution.

Worker cargo dropped on death is a separate persistent pile on the Worker's
final cell. Piles do not count toward the natural-node quota. A normal Worker
recovers 1 resource per successful action; a Beacon Worker recovers up to 2,
never more than the pile actually contains. Any remainder stays on the cell.

Refill is deterministic pseudorandom selection using the permanent world seed,
the resource-contract version, the refill Tick, chunk coordinates, and candidate
coordinates. Candidate cells must:

- be passable non-obstacle cells in the permanent map;
- not belong to the chunk backbone;
- not already contain a resource node;
- contain no Core in the post-settlement world.

A Unit or the ground Champion Beacon does not disqualify a candidate. Resource
nodes occupy no entity-capacity slot. Candidate ordering and selection must not
depend on process randomness, map iteration order, wall-clock time, or unordered
database results.

Refill emits no global coordinate list and does not reveal fogged cells. A new
node appears to a player only when its cell is inside that player's current
vision in a later complete `state`.

At a gameplay-contract migration boundary, keep the existing world, players,
Cores, Units, Beacon, Tick, plans, events, and statistics. The finite-resource
release replaces the legacy permanent resource layout in one atomic migration;
old resource coordinates are not grandfathered. The v0.5 capacity release
preserves the same state, then destroys Core inventory above the current
population capacity during the first v0.5 resolution.

Coordinates are signed 64-bit integers represented as `[x, y]`.

## Tick lifecycle and resolution order

### Command and resolution phases

Every logical Tick has a fixed global command phase and a variable-length
resolution phase:

1. The server announces `tick N`; commands are still closed.
2. The server prepares a complete private state for every player.
3. The server opens one global command window for 15 seconds.
4. It publishes each player's `state`; that player may submit immediately.
5. The gate locks the final valid plans when the global window closes.
6. The engine resolves the Tick.
7. One database transaction atomically commits the world and new clock.
8. The server announces the next Tick.

`tick` is informational. `state` is the only signal to act.

The 15-second window opens before states are published one player at a time. A
player receives only the time left in the global window; receiving `state` does
not start a private 15-second timer. The protocol intentionally does not expose
the opening or deadline timestamps.

Resolution time does not consume the next command window. The server never
skips logical Ticks to catch up with wall-clock time, never resolves two Ticks
concurrently, and pauses logical timers while offline.

### Authoritative resolution order

The following order is part of the rule contract:

1. Lock the final valid Agent and Manual plans.
2. Resolve every `SELF_DESTRUCT`, remove those Units, and drop any Worker cargo
   on their final cells.
3. Destroy Core resources above the new capacity after those removals.
4. Charge upkeep from the remaining population and apply unpaid-upkeep damage. A fleet destroyed here does
   not act later in the Tick.
5. Resolve Unit movement and Core migrations reaching their fourth Tick.
6. Validate new Core `START_MOVE` actions.
7. Resolve Champion Beacon pickup and drop.
8. Resolve Worker harvest and deposit.
9. Resolve Core spawn and shield repair.
10. Freeze one immutable combat snapshot and validate and accumulate all legal
   attacks.
11. Apply damage simultaneously, remove destroyed objects, then destroy Core
    resources above any capacity reduced by combat.
12. Process due respawns.
13. After every fourth resolved Tick, refill each tracked 32 x 32 chunk up to
    its current quota using the post-settlement world.
14. Atomically commit the world, dynamic resources, results, journal, and new
    clock.
15. Announce the next Tick and publish fresh private states.

### Atomicity, determinism, and recovery

- No client can observe a partially resolved Tick.
- Map iteration order, wall-clock time, process randomness, and unordered
  database results cannot decide an outcome.
- The same world state, resource layout, locked plans, and refill Tick produce
  the same result byte for byte.
- If state preparation fails, the server does not open the command window.
- If state publication fails, the gate aborts. Recovery reannounces the same
  Tick and opens a new full 15-second window.
- If the server crashes while the window is open, persisted plans remain.
  Recovery sends the same `tick`, fresh complete `state`, latest receipts, and
  opens a new full window. New submissions may replace the recovered plans.
- If the server crashes after plans are locked, it does not reopen the window.
  It deterministically replays the persisted locked plans.
- Downtime pauses the world.

## Vision and information boundaries

### Vision radii

Vision uses Manhattan distance:

| Object | Radius |
|---|---:|
| Core | 5 |
| Worker | 3 |
| Vanguard | 4 |
| Ranger | 5 |

The player's current view is the union of every living friendly object's view.

Obstacles block vision using an integer supercover line. The obstacle cell
itself is visible, but cells behind it are not. If a line passes exactly through
a corner shared by two cells, both cells count; an obstacle on either side
blocks the line.

Units, Cores, and resource cells do not block vision. Units and Cores do block a
Ranger's shot, which is a separate rule.

### Contents of `state`

Each complete state contains:

- every friendly Core and Unit, even when outside friendly vision;
- enemy Cores and Units only while visible;
- visible terrain, grouped into `OBSTACLE` and `RESOURCE` objects;
- the Champion Beacon coordinate for everybody, always;
- Beacon `GROUND` or `CARRIED` status and an ownerless `carrier_id` only when
  the Beacon cell is visible.

Visible enemy objects have `controlled: false` and no owner identity. Worker
cargo is private and appears only on friendly Workers.

### Exploration memory

The server sends only the current view. It does not store or replay a player's
full explored map. A client may remember permanent obstacles and backbone
knowledge. Remembered resource nodes are stale hints only: a node may have been
harvested outside vision, and a later refill may create a different visible node.
A remembered Unit, Core, resource node, or Beacon carrier must not be treated as
current truth.

## Core, production, migration, and upkeep

### Core attributes and actions

| Attribute | Value |
|---|---:|
| Maximum HP | 5 |
| Maximum shield | 5 |
| Maximum shield while holding the Beacon | 10 |
| Vision | 5 |
| Starting resources after spawn or respawn | 5 |

Damage and unpaid-upkeep damage consume shield before HP.

### Resource storage

Population counts living Units, not the Core. Each Unit provides 5 points of
Core storage:

```text
resource_capacity = population x 5
```

The limit is strict. Whenever self-destruction or combat lowers population,
stored resources above the new capacity are immediately destroyed. The owner
receives `CORE_RESOURCE_OVERFLOW_DESTROYED` with
`{amount: int, capacity: int}`. A new or respawned player starts with one Worker
and 5 resources, exactly filling the initial capacity.

A Worker deposits only what fits. Any remainder stays as Worker cargo. A full
Core resolves the action as `DEPOSIT_FAILED` with `CORE_RESOURCE_FULL`; the
Worker keeps all cargo. A successful full or partial deposit reports
`{amount: int, capacity: int, remaining: int}`.

A plan may specify at most one Core action:

- `SPAWN` with `unit_type`;
- `REPAIR_SHIELD`;
- `START_MOVE` with a cardinal `direction`;
- `CANCEL_MOVE`;
- `PICKUP_BEACON`;
- `DROP_BEACON`;
- `WAIT`.

### Production

| Unit | Cost |
|---|---:|
| Worker | 5 |
| Vanguard | 10 |
| Ranger | 12 |

- A Core may spawn at most one Unit per Tick.
- The new Unit appears on the Core cell.
- A cell holds at most two occupying entities, and the Core already uses one
  slot. A Core colocated with one Unit cannot spawn another.
- A full-cell spawn fails with `CELL_UNIT_LIMIT` and spends no resources.
- A newly spawned Unit cannot act in its creation Tick.
- It does appear in that Tick's combat snapshot, can be attacked, and blocks
  Ranger fire.
- It starts contributing to upkeep on the following Tick.
- Worker deposits resolve before spawn and repair, so deposited resources may
  pay for either in the same Tick. They cannot retroactively pay upkeep already
  charged after the self-destruct phase.

### Shield repair

`REPAIR_SHIELD` spends exactly 1 resource to restore exactly 1 shield and cannot
exceed the current shield cap. A failure reports `SHIELD_FULL` or
`INSUFFICIENT_RESOURCES`.

Holding the Beacon raises the cap to 10 but grants no free shield. Losing the
Beacon immediately clamps shield above 5 back to 5.

### Four-Tick Core migration

Moving a Core one cardinal cell takes four logical Ticks:

```text
START_MOVE resolves -> progress 1/4
next Tick           -> progress 2/4
next Tick           -> progress 3/4
next Tick           -> real movement attempt
```

- Migration progresses without resubmitting an action. `WAIT` does not pause it.
- Changing direction requires `CANCEL_MOVE`, which resets progress to zero.
- While migrating, the Core cannot spawn, repair, pick up or drop the Beacon,
  or receive Worker deposits.
- It still pays upkeep, takes damage, and retains its resource inventory.
- Colocated Units do not move with it.
- A carried Beacon remains at the Core's current logical position until the real
  move succeeds, then follows the Core.
- Completing or cancelling migration restores normal Core functions on the next
  Tick.
- A new `START_MOVE` is checked after this Tick's real movement resolves. A
  previous occupant that successfully left no longer blocks the start; an
  occupant that stayed or an enemy that just entered does. A friendly Unit in
  the destination is allowed if the terrain and final ownership are legal.
- Starting migration reserves nothing. Other objects may occupy or cross the
  destination before the fourth-Tick attempt.
- The real move joins the same global dependency graph as Unit movement.
- The move may fail because of impassable terrain, signed-coordinate overflow,
  an occupant that does not leave, a contested destination, an enemy entering
  the destination, or final cell capacity.
- A failed fourth-Tick move leaves the Core in place and clears migration
  progress.

### Population and upkeep

Population counts Units only:

```text
N = Worker + Vanguard + Ranger
tier = floor(N / 20)
upkeep = tier x (tier + 1) / 2
```

| Population | Tier | Resources per Tick |
|---:|---:|---:|
| 0-19 | 0 | 0 |
| 20-39 | 1 | 1 |
| 40-59 | 2 | 3 |
| 60-79 | 3 | 6 |
| 80-99 | 4 | 10 |
| 100-119 | 5 | 15 |

`SELF_DESTRUCT` resolves first. Upkeep is automatic, uses no Core action, and
uses the remaining population. A newly spawned Unit starts paying on the next
Tick; a Unit killed later in the Tick has already paid for this one.

If resources cannot cover upkeep, inventory becomes zero and each missing
resource deals 1 Core damage, shield first. If this destroys the Core, its fleet
and locked actions are removed before any later phase.

## Units and actions

Every Unit has a stable UUID while alive, occupies one cell slot, moves at most
one cardinal cell per Tick, and performs at most one action.

| Unit | HP | Vision | Cost | Attack |
|---|---:|---:|---:|---|
| Worker | 2 | 3 | 5 | none |
| Vanguard | 4 | 4 | 10 | 1 damage to adjacent target cell |
| Ranger | 2 | 5 | 12 | 1 damage at cardinal range 1-3 |

Every Unit supports `MOVE`, `PICKUP_BEACON`, `DROP_BEACON`,
`SELF_DESTRUCT`, and `WAIT`.

### Self-destruct

`{"type":"SELF_DESTRUCT"}` removes the Unit before upkeep and consumes its
action for the Tick. It gives no production-cost refund, deals no area damage,
and awards no destruction participation. Worker cargo drops on the final cell. A carried
Beacon drops at the Unit's cell and cannot be picked up until the next Tick.
The owner receives `UNIT_SELF_DESTRUCTED`, and `units_lost` increases by one.

### Worker

Worker-specific actions are `HARVEST` and `DEPOSIT`.

- `HARVEST` requires an empty Worker on a `RESOURCE` cell.
- It collects 1 resource, or 2 if the owner holds the Champion Beacon.
- Dropped Worker cargo is recovered before a natural node. Recovery never takes
  more than the pile contains, and an unfinished pile remains on the cell.
- A recovery emits `HARVEST_SUCCEEDED` with source `DROPPED_CARGO`; it does not
  increment harvested-resource or Beacon-bonus statistics.
- One successful natural harvest consumes the whole node, whether it grants 1
  or 2.
- When multiple eligible empty Workers harvest the same node in one Tick, only
  the lowest Worker UUID in ascending raw-byte order succeeds. Every other
  eligible contender receives `HARVEST_FAILED` with reason
  `RESOURCE_DEPLETED`.
- A Worker with cargo receives `HARVEST_FAILED` with `CARGO_FULL` and is not an
  eligible contender. If no resource node exists at resolution, the failure is
  `NOT_RESOURCE_CELL`.
- Bonus cargo already carried remains 2 after the owner loses the Beacon.
- `DEPOSIT` requires the Worker to share a cell with its own normal, receptive
  Core.
- A migrating Core or a Core recovering from migration cannot receive a
  deposit.
- A failed deposit leaves cargo on the Worker.
- Core storage is capped at `population x 5`. `DEPOSIT` moves only what fits;
  a full Core returns `CORE_RESOURCE_FULL`.
- Any Worker death adds its complete cargo amount to a persistent resource pile
  on the final cell. The owner receives `WORKER_CARGO_DROPPED`.
- Workers cannot attack.

### Vanguard

The Vanguard-specific action is `SWEEP` with one cardinal `direction`.

- It targets the adjacent cell.
- Every enemy Unit in that cell takes 1 damage.
- An enemy Core in that cell also takes 1 damage.
- Friendly objects take no damage.
- Damage from several sweeps adds in the shared combat snapshot.

### Ranger

The Ranger-specific action is `SHOOT` with `target_id` and `expected_cell`.

A shot succeeds only when:

1. the target is an enemy Unit or Core;
2. the target is still at `expected_cell`;
3. Ranger and target share one horizontal or vertical line;
4. Manhattan distance is 1, 2, or 3;
5. no intermediate cell contains an obstacle, Unit, or Core.

An object colocated in the target cell does not block the shot to the selected
`target_id`; there is no front-to-back ordering inside one cell.

The command endpoint intentionally accepts an unseen or nonexistent target UUID
so it cannot be used as a fog-of-war oracle. At resolution, a missing target,
friendly target, moved target, diagonal or out-of-range target, and blocked line
all produce the same private `SHOT_MISSED` result.

An action may contain only the fields allowed for its type. An unrelated field,
including `null`, rejects the entire plan with `UNEXPECTED_ACTION_FIELDS`.

## Movement and cell capacity

### Base constraints

- Unit movement is one cardinal cell and consumes the Unit's action.
- Obstacles block every object.
- Resource cells accept Units but reject migrating Cores.
- A cell holds at most two occupying entities. Core, Worker, Vanguard, and
  Ranger each count as one.
- Different players' objects may never finish a Tick in the same cell.
- Unit moves and finishing Core migrations resolve together in one global
  dependency graph, not in request order.
- A historical over-capacity cell is not repaired by deleting objects. It
  cannot receive moves or spawns and may only shed occupants until capacity is
  legal again.

### Contested destinations

- If different players try to enter the same destination, all competing moves
  fail. Submission time, fleet size, source, and database order do not break the
  tie.
- If one player's own objects compete for fewer free slots than requested, the
  lowest object UUIDs in ascending raw-byte order receive the slots. The rest
  fail with `CELL_UNIT_LIMIT`.

### Occupied destinations and dependency chains

An object may enter an occupied cell only if the current occupants all leave
successfully and final ownership and capacity remain legal.

```text
A -> B's old cell
B -> C's old cell
C -> empty cell
```

If `C` succeeds, the chain can succeed. If any dependency cannot leave, failure
propagates backward. If a cell contains two objects belonging to one player,
both must leave before an enemy can enter.

Two objects belonging to different players cannot swap positions across one
edge. Longer cycles of three or more positions may succeed when every final cell
is legal; the shortest cycle normally possible on the cardinal square grid uses
four cells.

A Core completing migration participates in the same graph. A stationary Core
is an occupied dependency that an enemy cannot enter.

A route selected in the official web frontend is local Manual automation, not a
server action. The frontend recalculates after each new state and submits only
the next `MOVE` or `START_MOVE`. Closing the frontend stops that route.

## Champion Beacon

- Exactly one indestructible Champion Beacon exists.
- It starts at `[0, 0]`; restarts do not reset its position.
- Its coordinate is always public. `GROUND` or `CARRIED` status and ownerless
  `carrier_id` appear only when its cell is visible.
- The Beacon occupies no capacity slot and blocks neither movement, vision, nor
  Ranger fire.
- A Unit or normal non-migrating Core sharing the ground Beacon's cell may spend
  its full action on `PICKUP_BEACON`.
- Only the current carrier may use `DROP_BEACON`.
- Moving across the Beacon does not pick it up automatically.
- A living carrier cannot have the Beacon taken directly.
- If several objects try to pick up a ground Beacon in one Tick, the lowest
  carrier UUID in ascending raw-byte order wins.
- Beacon actions resolve before Worker actions. A successful pickup grants the
  harvest bonus in the same Tick; a successful drop removes it in the same Tick.
- Holding the Beacon raises that player's Core shield cap from 5 to 10.
- Pickup grants no shield and performs no repair.
- Losing the Beacon clamps current Core shield above 5 down to 5.
- An eligible empty Worker collects 2 instead of 1 while its owner holds the
  Beacon. Both units come from the same consumed node; the bonus does not create
  or preserve another node.
- Cargo of 2 stays on the Worker after the bonus is lost and may be deposited
  together.
- The Beacon follows a Unit whenever its move succeeds.
- A migrating Core's Beacon remains at the Core's logical position until the
  fourth-Tick real move succeeds.
- If a Beacon carried at the start of the Tick is dropped, its carrier dies, or
  the owner's Core is destroyed, it lands at the carrier's final actual
  position. No other object may pick it up until the next Tick.

## Combat

Combat occurs after movement, Beacon actions, Worker actions, production, and
shield repair.

1. The engine freezes one immutable combat snapshot.
2. It validates every locked attack against that snapshot.
3. It accumulates damage from every legal attack.
4. It applies all damage simultaneously.
5. It removes dead Units and destroyed Cores only afterward.

An object killed during combat still performs a legal attack locked against the
snapshot. Mutual destruction is valid. Request order, completion order, database
row order, and Manual versus Agent source grant no initiative.

v0.5 has no random damage, dodge, critical hits, armor, automatic retaliation,
stamina, levels, or equipment.

### Vanguard damage

`SWEEP` damages every enemy Unit and any enemy Core in the adjacent target cell
for 1. Multiple sweeps add.

### Ranger damage

`SHOOT` damages one selected enemy object for 1 when all targeting and line rules
remain valid in the combat snapshot. Obstacles, Units, and Cores in intermediate
cells block the shot regardless of owner.

### Core damage and fleet removal

All Core damage consumes shield before HP. If combined damage reduces Core HP to
zero, the fleet is removed after every already-locked legal snapshot attack has
contributed. When several players damage the same object in the Tick that
destroys it, input order does not create a unique last-hit winner.

## Core destruction and respawn

When Core HP reaches zero:

- the Core is removed;
- all stored resources are lost;
- every Unit belonging to that player is removed;
- cargo carried by those Workers remains on each final cell;
- locked actions for those objects no longer matter;
- a carried Beacon drops under the Beacon rule;
- the player enters `RESPAWNING`.

The default respawn delay is 20 logical Ticks. Downtime does not advance it.

A successful respawn creates:

| Asset | Value |
|---|---:|
| Core | 5 HP and 5 shield |
| Resources | 5 |
| Workers | 1 |
| Spawn protection | none |

The Core and Worker receive fresh UUIDs.

The deterministic resolver seeks a passable empty spawn cell 20-30 Manhattan
cells from the nearest living Core, prefers lower nearby entity density, and
requires at least two passable neighbors. If it finds no legal cell on the due
Tick, it postpones the attempt by one Tick and tries the next deterministic
candidate set.

## Commands, priority, replacement, and receipts

### Agent and Manual source slots

Each player has one `AGENT` plan slot and one `MANUAL` plan slot per Tick.
Actions merge per controlled object:

```text
Manual explicit action > Agent explicit action > WAIT
```

- An object omitted from the Agent plan waits unless Manual supplies an action.
- An object omitted from the Manual plan falls back to Agent.
- Manual must submit explicit `WAIT` to cancel an Agent action for that object.
- All Agent clients for the player share one Agent slot.
- All browser tabs for the player share one Manual slot.

### Complete replacement

Each successful POST completely replaces the prior plan in that source slot. It
does not patch or merge with the older plan. To preserve actions for other
objects, the new plan must send them again.

### Static and dynamic validation

Static validation occurs before persistence and includes:

- one JSON object with no unknown fields;
- a positive Tick;
- lowercase hyphenated Unit UUID keys;
- every acting Unit belongs to the player;
- each action type is allowed for that object;
- required fields are present;
- unrelated fields are absent.

One static problem atomically rejects the whole request and leaves the previous
valid plan unchanged.

Dynamic facts resolve later, including moved targets, full destinations,
contested movement, insufficient resources, Beacon UUID tie-breaking,
same-node harvest contention or depletion, and blocked Ranger lines. These do
not reject the POST; they fail during Tick resolution.

### Ordering and limits

Valid requests for the same `(player, tick, source)` are serialized in the order
they enter the gate. Each stored plan replaces the prior one. The protocol has
no client-supplied plan version.

Each source accepts at most 64 new submissions per Tick after the idempotency
precheck. Both valid and statically invalid requests count. Further requests
fail with `429 COMMAND_RATE_LIMITED`, leaving the last valid plan unchanged.

An idempotency key is 8-128 visible ASCII bytes:

- same key and same body returns the original HTTP response;
- same key and different body returns `IDEMPOTENCY_CONFLICT`;
- replaying the same request does not broadcast another receipt.

### Acknowledgements and receipts

After storing a plan:

1. HTTP returns minimal `202 Accepted` receipt metadata.
2. Every live connection for that player receives the normalized stored plan in
   `received.plan`.
3. A reconnect during the same open Tick restores the latest receipt from each
   source.

Receipts are cleared when the next Tick begins. They are current-Tick state, not
a plan-history service. Other players never receive the plan.
