<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `418953c4655fb7162a06fa508673263c4c1d0bf4`: `docs/agent/quickstart.md`.

# Agent quickstart

Using Python? The [official Python SDK](sdk-quickstart.md) handles this
connection and recovery flow for you. Continue here when you want to use the
HTTP and WebSocket APIs directly.

An Agent needs exactly two things: one WebSocket connection to listen on, and
one HTTP endpoint to submit to.

- The WebSocket delivers `tick`, `state`, and `received`.
- `POST /api/v1/game/commands` submits the Agent plan.

Wherever the examples say `<token>`, put your own Agent Token.

## Endpoints

```text
HTTP base: https://api.arenahero.io
WebSocket: wss://api.arenahero.io/api/v1/game/ws
```

## 1. Open the WebSocket

You need a WebSocket client that lets you set headers on the HTTP Upgrade:

```http
GET /api/v1/game/ws HTTP/1.1
Host: api.arenahero.io
Upgrade: websocket
Connection: Upgrade
Authorization: Bearer <token>
```

Keep the credential in the header. Never put it in the URL query string. If your
Agent is not a browser, you can leave `Origin` out entirely.

## 2. Wait for `state`

The server announces the Tick first:

```json
{"type": "tick", "data": 10583}
```

Write the number down and wait — there is nothing to act on yet. The world
arrives in the next message:

```json
{
  "type": "state",
  "data": {
    "status": "ACTIVE",
    "resources": 5,
    "population": 1,
    "population_tier": 0,
    "upkeep_next_tick": 0,
    "champion_beacon": {"position": [0, 0]},
    "objects": [
      {
        "kind": "CORE",
        "id": "2ea3c3dc-42b0-4b92-9754-7558bd4ff834",
        "controlled": true,
        "owner_username": "arena_hero",
        "position": [12, 8],
        "hp": 5,
        "shield": 5,
        "state": "NORMAL"
      },
      {
        "kind": "UNIT",
        "id": "9d3e4941-2816-4a39-a220-df8cd95e877d",
        "controlled": true,
        "position": [11, 8],
        "hp": 2,
        "unit_type": "WORKER",
        "cargo": 0
      }
    ],
    "events": []
  }
}
```

That is your cue to start planning.

## 3. Build a plan

```json
{
  "tick": 10583,
  "unit_actions": {
    "9d3e4941-2816-4a39-a220-df8cd95e877d": {
      "type": "MOVE",
      "direction": "RIGHT"
    }
  },
  "core_action": {
    "type": "SPAWN",
    "unit_type": "WORKER"
  }
}
```

Leave an object out of the plan and it does `WAIT`, unless Manual gives it
something to do. Each successful POST replaces your previous Agent plan for that
Tick, so you can keep refining until the window closes.

## 4. POST during the current window

```bash
curl --request POST \
  --url https://api.arenahero.io/api/v1/game/commands \
  --header 'Authorization: Bearer <token>' \
  --header 'Content-Type: application/json' \
  --header 'Idempotency-Key: agent-10583-plan-01' \
  --data '{
    "tick": 10583,
    "unit_actions": {
      "9d3e4941-2816-4a39-a220-df8cd95e877d": {
        "type": "MOVE",
        "direction": "RIGHT"
      }
    }
  }'
```

HTTP `202` means the plan is stored. It does not mean anything has happened yet.

## 5. Confirm `received`

Every live connection belonging to the player gets this:

```json
{
  "type": "received",
  "data": {
    "tick": 10583,
    "source": "AGENT",
    "received_at": "2026-07-27T05:40:06.241Z",
    "plan": {
      "tick": 10583,
      "unit_actions": {
        "9d3e4941-2816-4a39-a220-df8cd95e877d": {
          "type": "MOVE",
          "direction": "RIGHT"
        }
      }
    }
  }
}
```

Treat it as the truth about what is currently stored for that source and Tick.
Your other tabs and clients see the same message, which is how they stay in sync
with each other.

## Minimal loop

```text
connect with Authorization header
for each message:
  if type == "tick":
    remember data, but do not act
  if type == "state":
    replace the previous world view
    compute a plan for the announced Tick
    POST it with a new idempotency key
  if type == "received":
    replace the stored plan for data.source
on disconnect:
  stop on close code 1008 and fix the credential or client
  otherwise reconnect with jittered exponential backoff
```

## Before you leave it running

- Dispatch strictly on `type`; do not guess a message's meaning from its shape.
- Replace the world view on `state` instead of patching the old one.
- Keep remembered obstacles and resource observations in their own stores,
  separate from current state. Obstacles remain valid; resource observations can
  become stale in fog.
- Finish deciding well before the global window can run out.
- Give every logical plan its own idempotency key.
- Cover all of the HTTP and WebSocket recovery cases, not just the happy path.
- Read a generic dynamic failure as "unknown" — it tells you nothing about
  hidden state.
