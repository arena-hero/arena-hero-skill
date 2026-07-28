---
name: arena-hero
description: Create, test, and run Python tactics for Arena Hero or play the game directly through its API. Use when an agent is asked to build or improve an Arena Hero tactic, control Units or a Core, connect to the live game, run a bot, inspect live Turns, submit plans, or help a player watch the agent play.
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

## Protect the API key

- Obtain the key only through a hidden terminal or host-provided secret prompt.
- Pass it explicitly as `ArenaHeroClient(api_key=api_key)`.
- Never request or accept the key in chat.
- Never put it in source code, environment variables, command-line arguments,
  logs, patches, or repository files.
- If hidden input is unavailable, stop direct play and offer tactic-script mode,
  where the user can run a local `getpass()` prompt.

Selecting a live mode and securely entering the key authorizes Agent commands
for that game session. Do not ask for confirmation on every Tick.

## Establish current context

Before writing a tactic or submitting a plan:

1. Read [references/game-rules.md](references/game-rules.md) completely. It is
   the bundled Arena Hero v0.1 rule contract and is mandatory in both modes.
2. When network access is available, check the current
   [rule source and version](https://doc.arenahero.io/reference/source-and-version).
   If it describes a later or incompatible contract, stop and update the
   bundled rules before creating rule-dependent behavior.
3. Read the relevant connection documentation:
   - Reliable loop: <https://doc.arenahero.io/agent/command-loop>
   - Python SDK: <https://doc.arenahero.io/sdk/quickstart>
   - SDK reference: <https://doc.arenahero.io/sdk/reference>
4. Inspect the current project before adding files or dependencies.
5. Use the official `arena-hero` package from PyPI. Do not recreate its HTTP,
   WebSocket, retry, receipt, or state-model logic.
6. Treat each `Turn` as a complete authoritative replacement. Never invent
   UUIDs, coordinates, enemies, resources, or actions.
7. Build and submit only a plan for the current Turn. Never retick a stale plan.
8. Verify every rule-dependent decision against the bundled rules. Never guess
   costs, ranges, caps, timing, population formulas, event names, or stacking
   rules from memory or genre conventions.

The bundled rules make offline tactic authoring possible. Online documentation
is still required when checking whether the public contract has changed, not for
reconstructing the v0.1 mechanics from memory.

Read [references/tactic-authoring.md](references/tactic-authoring.md) when
creating or changing a tactic. Read
[references/direct-play.md](references/direct-play.md) before direct play.

## Tactic-script mode

1. Use the user's stated goal. If none is given, ask once for the desired
   behavior; if the user has no preference, create a balanced starter tactic.
2. Reuse an existing Python project. Otherwise create only the minimal tactic
   file and dependency declaration needed to run it.
3. Default to `ArenaHeroClient`. Use `AsyncArenaHeroClient` only when the
   surrounding project is asynchronous or the user requests it.
4. Separate tactic decisions from connection setup so decisions can be tested
   without a live credential.
5. Handle missing Core state while respawning, visible terrain only, current
   Unit capabilities, and prior resolution events.
6. Submit one complete plan promptly after each Turn. Prefer a simpler valid
   plan over missing the command window.
7. Validate syntax, imports, representative state decisions, and secret absence
   before making a live connection.
8. Run the tactic in an interactive terminal so `getpass()` remains hidden.
   Stop cleanly on `Ctrl-C`.

Do not add a framework, configuration layer, or extra documentation unless the
existing project needs it.

## Direct-play mode

1. Explain the 15-second warning and obtain the user's direct-play choice before
   launching anything.
2. Prepare an isolated Python 3.11+ environment with a compatible official SDK.
3. Run `scripts/direct_session.py` from this skill in a PTY. The user must type
   the API key into its hidden prompt; do not relay the key through chat or a
   tool argument.
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
