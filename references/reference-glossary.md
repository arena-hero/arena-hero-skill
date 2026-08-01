<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `4d81ed8b200dec739cbabcce81392af3fe5f2d32`: `docs/reference/glossary.md`.

# Glossary

**Agent**

A local automated client authenticated as source `AGENT`. It takes state in over
the WebSocket and pushes plans out over HTTP.

**Server state**

The current `state` the server sent you. Remembered terrain, planned routes,
predictions, and UI animation all belong to your client, and any of them can be
out of date.

**Champion Beacon**

The one indestructible global objective. Its coordinate is public at all times,
and a carrier you can see grants shield-cap and Worker-harvest bonuses.

**Cargo pile**

Resources left on a Worker's final cell when it dies. The amount persists
independently from the chunk's natural-resource quota until Workers recover it.

**Command gate**

The server boundary that accepts correctly received plans, and only during the
window that is currently OPEN.

**Complete plan**

The full action map one source wants for one Tick. A later POST replaces an
earlier plan from that source rather than patching it.

**Controlled**

`controlled: true` marks an object as belonging to whoever is receiving the state.
`controlled: false` marks a currently visible enemy.

**Core owner username**

Every Core carries `owner_username` without a leading `@`. It is public while
that Core is included in the state. Unit owners remain private.

**Core**

Your base: resource store, shielded primary life object, Unit producer, and — very
slowly — a mobile entity.

**Dynamic validation**

The checks that only global resolution can make, such as occupancy, resources,
target position, and line of fire. Failures come back in the next state.

**Exploration memory**

What your client remembers from older states. Remembered obstacles stay correct;
resource points and entities may be stale until their cells are visible again.

**Manual**

The web player's source slot. Per object, an explicit Manual action beats the
Agent action, and leaving an object out falls back to the Agent.

**Occupying entity**

A Core or Unit, taking one of a cell's two capacity slots. The Beacon and terrain
take none.

**Plan receipt**

The HTTP 202 metadata plus the WebSocket `received` message that follow the server
storing a source plan.

**Resolution event**

An action result carried inside the next `state.events`, rather than sent as its
own realtime message.

**Resource point**

One consumable map point. A successful harvest removes it and yields 1 resource,
or 2 to a Worker whose player holds the Beacon. Every fourth resolved Tick,
deterministic replenishment fills only the missing slots in each chunk back to
that chunk's fixed quota.

**Resource quota**

The fixed available-point count for a chunk immediately after replenishment:
`max(2, floor(16 × 8 / (8 + ring)))`, where the central 2×2 chunks form ring 0.

**Static validation**

The checks that happen before global resolution: JSON shape, ownership of the
acting Units, action fields, required fields, and the current Tick gate.

**Supercover line**

An integer grid line that includes every cell it touches, which is what stops
diagonal corner gaps from opening up in obstacle vision blocking.

**Tick**

One logical decision-and-resolution cycle. It advances only after an atomic world
commit, and it never races to catch up after downtime.

**Terrain batch**

A single `OBSTACLE` or `RESOURCE` object, with no UUID, holding a sorted
`positions` array of every currently visible position of that kind. Obstacles are
permanent terrain; resource positions mean current visible availability.

**World snapshot**

The immutable input one phase of deterministic resolution works from. Combat uses
a single shared snapshot, which is what makes all legal attacks simultaneous.
