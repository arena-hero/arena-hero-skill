# Direct play

Direct play is an experimental, session-scoped bridge between an agent and the
official Python SDK.

Read [game-rules.md](game-rules.md) completely before starting the bridge. Do
not spend the live command window discovering basic mechanics.

Use the bundled [command model](api-commands.md), [state model](api-state-model.md),
and [resolution results](api-resolution-results.md) when interpreting bridge
payloads. Read [sdk-reference.md](sdk-reference.md) when diagnosing the bridge's
official SDK behavior.

## Required warning

Tell the user before mode selection:

> Every Tick has only a 15-second command window. State publication, agent
> reasoning, and tool latency use part of that time, so direct play cannot
> guarantee a timely command and may miss consecutive Ticks. Use a tactic script
> for reliable continuous play.

## Start the bridge

Use Python 3.11 or newer and a compatible official SDK. Prefer an isolated
environment. With `uv`:

```bash
uv run --python 3.11 --with 'arena-hero>=0.2.2,<0.3' \
  python /absolute/path/to/arena-hero/scripts/direct_session.py
```

The bridge reads `ARENA_HERO_API_KEY`, `.env`, or a file passed with
`--api-key-file`. If none is available, an interactive run falls back to a
hidden prompt.

For a non-production server, pass only the public endpoint:

```bash
python scripts/direct_session.py --base-url http://localhost:8080
```

The bridge uses an eight-second decision timeout by default to leave some room
for submission. This still cannot guarantee the server's unknown deadline.

## Read bridge events

The bridge writes one JSON object per line.

### Ready

```json
{
  "type": "ready",
  "base_url": "https://api.arenahero.io",
  "viewer_url": "https://app.arenahero.io/arena",
  "decision_timeout_seconds": 8.0
}
```

Open the viewer only after this event.

### Tick

```json
{"type": "tick", "tick": 10583}
```

A Tick notice is not actionable. Wait for `turn`.

### Turn

```json
{
  "type": "turn",
  "tick": 10583,
  "decision_timeout_seconds": 8.0,
  "state": {}
}
```

`state` is the complete private `PlayerState`. Replace the previous state; do
not merge arrays or reuse controllers from an earlier Tick.

### Accepted and received

`accepted` is the minimal HTTP acknowledgement. `received` is the canonical
plan stored by the server. Keep them distinct.

### Missed, skipped, input error, submit error, and error

- `missed` means no valid control line arrived before the bridge deadline.
- `skipped` means the agent deliberately sent no plan for that Tick.
- `input_error` means the control line was malformed or stale. Correct it only
  if the same Turn still has time.
- `submit_error` means the current plan was rejected or exhausted safe transport
  retries. Do not retick it; wait for fresh state unless the same Turn clearly
  remains open.
- `error` means the connection or API failed. Follow its message; never expose
  the credential while diagnosing.

## Send one control line

Write exactly one JSON object followed by a newline.

Submit a complete Agent plan:

```json
{
  "type": "submit",
  "plan": {
    "tick": 10583,
    "unit_actions": {
      "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
        "type": "MOVE",
        "direction": "RIGHT"
      }
    },
    "core_action": null
  }
}
```

Skip the current Turn:

```json
{"type": "skip", "tick": 10583}
```

Stop and close both connections:

```json
{"type": "stop"}
```

The bridge rejects plans and skips whose Tick does not equal the current Turn.
Never change only the Tick number on an old plan.

## Decide safely

Use only the current state. Prefer no submission to a fabricated UUID, target,
position, or action. A valid plan must contain the current positive `tick`, a
complete `unit_actions` object, and one `core_action` or `null`.

Manual plans from the web UI use a separate source. For the same Tick, the
player's Manual action overrides the Agent action for each corresponding Unit or
Core.

Stop direct play when the user asks, the agent session is ending,
authentication fails, or repeated latency makes the mode misleading. Offer
tactic-script mode for continued play.
