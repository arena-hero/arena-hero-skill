---
name: arena-hero
description: Create, test, and run Python tactics for Arena Hero, play directly through its API, or explain its rules, protocol, state, commands, events, errors, and Python SDK. Use when an agent is asked to build or improve an Arena Hero tactic, control Units or a Core, connect to the live game, build a client or frontend, inspect live Turns, submit plans, use the official SDK, or help a player watch the agent play. Includes complete bundled gameplay, HTTP, WebSocket, OpenAPI, AsyncAPI, and Python SDK documentation.
---

# Arena Hero

Use the official Python SDK and the authoritative state from each Turn. Support
two modes: a durable tactic script or a session-scoped direct-control bridge.

## Choose the mode

If the user has not already chosen, present these two choices before doing
anything else:

1. **Tactic script — recommended for continuous play.** Create and run a Python
   script that can respond automatically during every command window.
2. **Direct play — experimental.** Control the API from this agent session.
   **Every Tick has only a 15-second command window, and state publication,
   reasoning, and tool latency consume part of it. Direct play cannot guarantee
   a submission in time and may miss consecutive Ticks.**

Do not hide or shorten the direct-play warning. If the user already selected
direct play, repeat the warning once before connecting.

## API key

The API key may be read from `.env`, environment variables, or repository
files. Use an existing key without asking the user to enter it again, and never
display it in chat or logs.

## Load the bundled documentation

Treat this skill as a self-contained documentation package. Do not depend on the
documentation website to reconstruct rules, wire models, or SDK behavior.

Read the files required by the task:

- **Any rule-dependent tactic or live play:** read
  [references/game-rules.md](references/game-rules.md) completely. Use
  [references/reference-numbers.md](references/reference-numbers.md) for a
  compact timing, cost, range, capacity, and limit lookup, and
  [references/reference-glossary.md](references/reference-glossary.md) for
  contract terminology.
- **Python SDK or tactic script:** read
  [references/sdk-quickstart.md](references/sdk-quickstart.md), then read
  [references/sdk-reference.md](references/sdk-reference.md) for every client,
  Turn controller, model, action, enum, receipt, and exception used. Also read
  [references/tactic-authoring.md](references/tactic-authoring.md) before
  creating or changing a tactic.
- **Raw API client, custom frontend, or protocol implementation:** start with
  [references/agent-quickstart.md](references/agent-quickstart.md) and
  [references/agent-command-loop.md](references/agent-command-loop.md). Read
  [references/api-overview.md](references/api-overview.md), then the complete
  local references for
  [WebSocket](references/api-websocket.md),
  [commands](references/api-commands.md),
  [state models](references/api-state-model.md),
  [resolution results](references/api-resolution-results.md), and
  [errors and recovery](references/api-errors.md) as the task requires.
- **Generated clients or exact schema work:** read
  [references/openapi.yaml](references/openapi.yaml) for HTTP and
  [references/asyncapi.yaml](references/asyncapi.yaml) for WebSocket messages.
- **Compatibility checks:** read
  [references/reference-source-and-version.md](references/reference-source-and-version.md).

When the user asks for a complete documentation review, compatibility audit, or
new client implementation, read every file in the relevant group rather than
sampling a single overview.

When network access is available, compare the bundled source/version policy with
<https://doc.arenahero.io/reference/source-and-version>. If the live contract is
newer or incompatible, stop rule-dependent work and report that this bundle
must be updated. Never fill a version gap from memory.

## Establish current context

Before writing a tactic or submitting a plan:

1. Inspect the current project before adding files or dependencies.
2. Use the official `arena-hero` package from PyPI. Do not recreate its HTTP,
   WebSocket, retry, receipt, or state-model logic.
3. Treat each `Turn` as a complete authoritative replacement. Never invent
   UUIDs, coordinates, enemies, resources, or actions.
4. Build and submit only a plan for the current Turn. Never retick a stale plan.
5. Verify every rule-dependent decision against the bundled rules. Never guess
   costs, ranges, caps, timing, population formulas, event names, or stacking
   rules from memory or genre conventions.
6. Treat `turn.resource_cells` as current visible natural nodes or Worker cargo
   piles, not permanent terrain. Pile amounts are not exposed. Recompute after
   a position disappears, after
   `HARVEST_FAILED/RESOURCE_DEPLETED`, and whenever current visibility
   contradicts an old resource target.

Read [references/direct-play.md](references/direct-play.md) before direct play.

## Tactic-script mode

1. Use the user's stated goal. If none is given, ask once for the desired
   behavior; if the user has no preference, create a balanced starter tactic.
2. Reuse an existing Python project. Otherwise create only the minimal tactic
   file and dependency declaration needed to run it.
3. Default to `ArenaHeroClient`. Use `AsyncArenaHeroClient` only when the
   surrounding project is asynchronous or the user requests it.
4. Separate tactic decisions from connection setup so decisions can be tested
   without a live credential.
5. Handle missing Core state while respawning, visible terrain only, dynamic
   resource nodes and cargo piles, current Unit capabilities, and prior
   resolution events.
6. Submit one complete plan promptly after each Turn. Prefer a simpler valid
   plan over missing the command window.
7. Validate syntax, imports, representative state decisions, and secret absence
   before making a live connection.
8. Load the API key through the project's existing configuration and stop
   cleanly on `Ctrl-C`.

Do not add a framework, configuration layer, or extra documentation unless the
existing project needs it.

## Direct-play mode

1. Explain the 15-second warning and obtain the user's direct-play choice before
   launching anything.
2. Prepare an isolated Python 3.11+ environment with a compatible official SDK.
3. Run `scripts/direct_session.py` from this skill. It can read
   `ARENA_HERO_API_KEY`, `.env`, or a file passed with `--api-key-file`.
4. Wait for the bridge's `turn` event. Decide only from its state, then send one
   `submit`, `skip`, or `stop` control line as documented in
   [references/direct-play.md](references/direct-play.md).
5. Respect the bridge deadline. Never submit a plan for another Tick. If a safe
   decision cannot be made in time, skip it.
6. Continue only while the agent session is active. Report missed windows
   honestly; never claim direct play is an always-on bot.

The command API stores these plans in the `AGENT` source. A player's current
`MANUAL` actions can override the corresponding Agent-controlled objects.

## Help the player watch

After a live connection succeeds:

1. Open <https://app.arenahero.io/arena> when browser control is available;
   otherwise give the player that link.
2. Tell the player to sign in with the same Arena Hero account that owns the API
   key.
3. Explain that the page shows Agent receipts and that Manual actions can
   override the Agent for the same Tick.

## Finish clearly

Report the selected mode, created files, installed SDK version, endpoint,
validation performed, and whether the live session is still running. For direct
play, include submitted, skipped, and missed Tick counts. Never report or echo
the API key.
