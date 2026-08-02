<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `c6cdcee875ba7a985f2f580edc0c47cd4b17876e`: `docs/reference/source-and-version.md`.

# Source and version policy

## Current release

| Item | Value |
|---|---|
| HTTP and WebSocket API | v0.1 |
| Gameplay rules | v0.10 |
| Server repository | [`arena-hero/arena-hero`](https://github.com/arena-hero/arena-hero) |
| Reviewed server commit | `5a3bcdf5fbc75574938dc35acf48b12145b37582` |
| Python SDK | [`arena-hero/arena-hero-python`](https://github.com/arena-hero/arena-hero-python), v0.2.6 |
| Reviewed SDK commit | `4a295851002ac5e73b34fa652e8d084f780c01ed` |
| Server review date | 2 August 2026 |
| SDK review date | 2 August 2026 |
| Documentation repository | [`arena-hero/arena-hero-doc`](https://github.com/arena-hero/arena-hero-doc) |
| Languages | English, Simplified Chinese |

For a release-oriented history assembled from all project repositories, see the
[Changelog](reference-changelog.md).

## If the docs and server disagree

These pages describe the public rules and game API, but what actually happens at
runtime is decided by the server code, the database constraints, and the tests.

So when published prose and released implementation part ways:

1. do not treat the discrepancy as an implied rule and exploit it;
2. write down the exact server version and what you observed;
3. open an issue in the documentation or server repository;
4. update both repositories once the intended behavior has been decided.

## Changes that affect compatibility

Touch any of these and you may break an existing client, so each one needs an
explicit contract-version decision:

- the 15-second global command window, and `state` as the action trigger;
- deterministic resolution phases and atomic commit;
- complete source-plan replacement and Manual precedence;
- action field rules and idempotency;
- WebSocket message types and the reconnect snapshot;
- the fog-of-war privacy boundary;
- the map generator contract;
- the finite-resource quota, cargo-drop, consumption, refresh, and contention rules;
- the strict `max(10, population × 5)` Core storage limit and overflow destruction;
- combat Core-loot winner selection, same-Tick mutual destruction, and capacity overflow destruction;
- post-combat Unit/Core healing, Unit-first resource priority, and the placement
  of Core healing, shield repair, and spawning after combat;
- the Ranger eight-direction line-of-fire geometry and the rule that only
  obstacles on intermediate shot cells block shots;
- the same-Tick Core respawn attempt and retry-only `RESPAWNING` state;
- core balance rules that determine replayed outcomes.

Everything else — copy, layout, diagrams, examples, the order things are explained
in — can improve freely, because none of it changes the game contract.

## Why there is no version picker yet

The public API remains v0.1 and the current gameplay rules are v0.10, so this site
publishes exactly one current version in English and Simplified Chinese. Once
there is a first stable compatibility release, older contracts can be kept
around as Docusaurus versions.

## What a protocol change must update

Any gameplay or game API change has to bring all of this with it:

- implementation and tests in the server repository;
- matching models, behavior, and tests in the official Python SDK;
- updated English and Simplified Chinese pages here;
- an updated OpenAPI or AsyncAPI schema, where one applies;
- verified bilingual production builds;
- a clear compatibility note whenever existing clients may break.
