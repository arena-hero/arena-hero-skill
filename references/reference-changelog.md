<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `ad6fc27a28727617858abc7cbb6832e7653ba3a9`: `docs/reference/changelog.md`.

# Changelog

This page is curated from the Git history of the server, public frontend,
Python SDK, documentation, and Arena Hero Skill repositories. It records changes
that players or developers can observe. Pure refactors, CI maintenance, and
internal security fixes are grouped instead of copied commit by commit.

Gameplay rule versions are independent from the Python SDK version. The public
HTTP and WebSocket API is still v0.1. For the exact currently reviewed source,
see [Source and version policy](reference-source-and-version.md).

## 2 August 2026

### Gameplay rules v0.10 — post-combat HP recovery

- Every Unit can use `HEAL` while sharing a cell with its own stationary Core;
  the Core can also use `HEAL` as its action.
- Healing runs after simultaneous combat damage and costs 1 Core resource per
  HP actually restored. One action may spend several resources to reach full HP.
- Unit heals resolve by Unit UUID before the Core action. Fatal damage cannot be
  healed, and a failed heal spends nothing.
- Core healing, shield repair, and spawning now resolve after combat. Newly
  spawned Units cannot be attacked during their birth Tick, and repaired shield
  cannot absorb damage from the Tick that just ended.
- Inventory captured from a destroyed enemy Core can immediately fund Unit
  healing and the surviving Core action in the same Tick.
- Added private healing result events, lifetime HP-recovery counters, frontend
  controls and feedback, plus Python SDK v0.2.6 with `unit.heal()`,
  `core.heal()`, `HealAction`, and typed `HealingResult` values.

Source: [server `5a3bcdf`](https://github.com/arena-hero/arena-hero/commit/5a3bcdf5fbc75574938dc35acf48b12145b37582),
[frontend `789cf1b`](https://github.com/arena-hero/arena-hero-web/commit/789cf1b5584a18b2de5f2b2ee5546c3d9fb68166),
and [SDK `4a29585`](https://github.com/arena-hero/arena-hero-python/commit/4a295851002ac5e73b34fa652e8d084f780c01ed).

## 1 August 2026

### Gameplay rules v0.9 — Core resource capture

- A Core destroyed in combat offers its complete stored inventory to the player
  who dealt the most damage to that Core during the destruction Tick.
- Tied damage uses raw player UUID order. Every attacker still receives normal
  destruction participation; that statistic does not decide resource ownership.
- The winner stores only what fits under the post-combat
  `max(10, population × 5)` capacity. Overflow is destroyed.
- If the winner's Core also dies in the same combat Tick, all victim resources
  are destroyed. Upkeep-deficit destruction never yields loot.
- Added private `CORE_RESOURCES_CAPTURED` results, frontend feedback, and the
  typed SDK `CoreResourceCapture` model.

Source: [server `a998d8d`](https://github.com/arena-hero/arena-hero/commit/a998d8d7dd3809f0cf66a60f3afe61a7008ba2e2),
[frontend `0daf69a`](https://github.com/arena-hero/arena-hero-web/commit/0daf69a2a4fc5f7b8a8f1b5af30a7e621f8fb24d),
[SDK `9cfe088`](https://github.com/arena-hero/arena-hero-python/commit/9cfe08821b468002887e5dea2b4bc603a76abe47),
[docs `9a881bf`](https://github.com/arena-hero/arena-hero-doc/commit/9a881bf066fe91ba2eaa4e9d7057c33cb8bd260a),
and [Skill `1c4b126`](https://github.com/arena-hero/arena-hero-skill/commit/1c4b1268bec25254b13e1c92152cd58cdfc146c3).

### Gameplay rules v0.8 — diagonal Ranger fire

- Rangers may shoot horizontally, vertically, or on an exact 45-degree
  diagonal at range 1-3.
- Only obstacles in intermediate shot cells block the shot. Objects beside the
  line do not.

Source: [server `59268f3`](https://github.com/arena-hero/arena-hero/commit/59268f3048f3845dde1358a366365dcaba459185).

### Gameplay rules v0.7 — piercing fire and immediate respawn

- Ranger shots pass through Units and Cores; only terrain obstacles block them.
- The respawn cooldown was removed. A destroyed Core normally gets its
  replacement attempt later in the same resolution Tick.
- The web client also fixed deposit priority around Core movement and restored
  visible Core shield state on the arena map.

Source: [piercing fire `fb7680f`](https://github.com/arena-hero/arena-hero/commit/fb7680fec34338d8f31fa0d656b29639e78c6a34)
and [immediate respawn `2b32550`](https://github.com/arena-hero/arena-hero/commit/2b325502fe40ccda3ee615c48a15855d6822fabd).

## 30 July 2026

### Gameplay rules v0.6 — minimum Core capacity

- Core storage became `max(10, population × 5)`, so zero, one, and two living
  Units still provide 10 capacity.
- Deposits stop at the strict limit and population loss immediately destroys
  existing overflow.

Source: [server `f81b6c9`](https://github.com/arena-hero/arena-hero/commit/f81b6c95db339e144226ca92514ad3d3c87721d9).

### Gameplay rules v0.5 — population-based storage

- Core resource capacity became dependent on the current living Unit
  population.
- The frontend and SDK exposed capacity and remaining resource space.

Source: [server `bc16014`](https://github.com/arena-hero/arena-hero/commit/bc16014cb039c34238bdef0f556219d6638ba4cc).

## 29 July 2026

### Gameplay rules v0.4 — recoverable Worker cargo

- A dead Worker drops all carried resources on its final cell.
- Cargo piles persist separately from natural chunk quotas and can be harvested
  until empty.

Source: [server `f98e22e`](https://github.com/arena-hero/arena-hero/commit/f98e22e74486d3d51a30fd38a708da1716b3b454).

### Gameplay rules v0.3 — Unit self-destruct

- Every Unit may self-destruct before upkeep.
- Self-destruct gives no refund, damage, or enemy destruction participation;
  Worker cargo and a carried Beacon still drop normally.

Source: [server `16b152b`](https://github.com/arena-hero/arena-hero/commit/16b152ba63f5be4fcff2c347d8edddf5324d9558).

### Gameplay rules v0.2 — finite resources

- Natural resource points became consumable instead of permanent.
- Each 32×32 chunk maintains a fixed distance-based quota and replenishes
  missing positions every four resolved Ticks.
- Same-cell harvest contention became deterministic.

Source: [server `c655315`](https://github.com/arena-hero/arena-hero/commit/c6553156d8e4512fd6010a10b6500741f023c9da).

### Frontend and visible-state changes

- Terrain rendering was cached by chunk and the arena moved toward a sharper,
  smoother canvas renderer, especially on Retina displays and during zoom.
- Visible Cores began exposing `owner_username`, displayed as `@username`;
  Unit ownership remained private.

Source: [terrain caching `e2e2ba5`](https://github.com/arena-hero/arena-hero/commit/e2e2ba54f314f6167cd06e9899d0d9756ea403e0),
[Retina rendering `ca2eea4`](https://github.com/arena-hero/arena-hero/commit/ca2eea48308be5e2bdf9a33e2a33808ceaccb2b6),
and [Core usernames `4d6454f`](https://github.com/arena-hero/arena-hero/commit/4d6454fa1eb8fad03e1ccb2fb50c6e82f038f477).

## 28 July 2026

- The official typed Python SDK launched with synchronous and asynchronous
  clients, Turn controllers, retries, receipts, and WebSocket reconnection.
- The bilingual Docusaurus documentation site launched, followed by dedicated
  Python SDK and Arena Hero Skill sections.
- The Arena Hero Skill launched with tactic-script and direct-play modes, then
  bundled the complete gameplay and developer documentation for offline use.

Source: [SDK `b784c81`](https://github.com/arena-hero/arena-hero-python/commit/b784c8122f8cfc2435fc58a28ddc40a7db615970),
[docs `d66a0b8`](https://github.com/arena-hero/arena-hero-doc/commit/d66a0b89fa2b943526cfa8195a59e300529763e4),
and [Skill `7e0422d`](https://github.com/arena-hero/arena-hero-skill/commit/7e0422d730d4294e19af46283ecdb24b9a835458).

## 26 July 2026

- Replaced the long-lived SSE game stream with server-to-client WebSocket
  messages while keeping command submission on HTTP.
- Added canonical `received` plan messages to every connected client for the
  same player, including reconnect snapshots.

Source: [WebSocket transport `243a05b`](https://github.com/arena-hero/arena-hero/commit/243a05b37330e36a481b761d76424e94a7b830e9)
and [cross-client receipts `b9d4de7`](https://github.com/arena-hero/arena-hero/commit/b9d4de7b36c074f0a47856421eacd5eccf675541).

## 23–25 July 2026

- Completed the production-aligned rules, Champion Beacon, deterministic
  movement and combat, PostgreSQL persistence, authentication, and deployment
  foundation.
- Removed the global state-publication barrier: each player can submit as soon
  as their own complete `state` is published.
- Scaled the single-world server design for 5,000 concurrent players.
- Added the interactive web tutorial and completed two security-hardening
  rounds.

Source: [production alignment `a707f66`](https://github.com/arena-hero/arena-hero/commit/a707f66a39aa9acd2b2f3a3d6369573c8a7c19d0),
[state publication `694c4c0`](https://github.com/arena-hero/arena-hero/commit/694c4c0d9671eb32156bd0bf09101a38fe341a0e),
[5,000-player scaling `fb5a3cd`](https://github.com/arena-hero/arena-hero/commit/fb5a3cdcb106e2a1826724932697900ac5e7936a),
and [tutorial `3a9535c`](https://github.com/arena-hero/arena-hero/commit/3a9535c53d0eb9726c609c5b13a671933a24e715).

## 15–17 July 2026

- Created the shared persistent world, deterministic Tick engine, initial
  `tick` / `state` / command protocol, Go server, PostgreSQL storage, and web
  client.
- Added autonomous client-side routes that submit only the next legal step each
  Tick.

Source: [initial implementation `c32c144`](https://github.com/arena-hero/arena-hero/commit/c32c144f6fd82b306fd0fb31a0ce9229dffb063e)
and [movement routes `d9c7d2d`](https://github.com/arena-hero/arena-hero/commit/d9c7d2dcb6e3cf2d9a28c063080574b2be4c786e).

## Python SDK releases

SDK versions are separate from gameplay rule versions.

| Version | Date | Developer-visible change |
|---|---|---|
| 0.2.6 | 2 Aug 2026 | PyPI release adding Unit/Core healing, typed `HealingResult`, and the `CoreResourceCapture` model from the unreleased 0.2.5 source. |
| 0.2.5 source | 1 Aug 2026 | Adds typed `CoreResourceCapture`; committed but not yet published to PyPI. |
| 0.2.4 | 30 Jul 2026 | Adds the minimum Core-capacity contract and release metadata. |
| 0.2.3 | 30 Jul 2026 | Exposes Core resource capacity and available storage space. |
| 0.2.2 | 29 Jul 2026 | Exposes public Core `owner_username`. |
| 0.2.1 | 29 Jul 2026 | Packaging and Apache-2.0 release update; no gameplay protocol change. |
| 0.2.0 | 29 Jul 2026 | Adds self-destruct and cargo recovery event support. |
| 0.1.0 | 28 Jul 2026 | First PyPI release of the official synchronous and asynchronous SDK. |
