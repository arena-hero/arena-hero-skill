<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `03a945270b74c53b26cb52f2295a052f7e88c015`: `docs/api/websocket.md`.

# WebSocket

Connect when the Agent starts, and keep that connection open:

```text
wss://api.arenahero.io/api/v1/game/ws
```

This socket is for receiving game state and plan receipts. Commands go through
[`POST /api/v1/game/commands`](api-commands.md) instead.

<nav className="api-model-nav" aria-label="WebSocket sections">
  <strong>Jump to</strong>
  <a href="#game-loop">Game loop</a>
  <a href="#messages">Messages</a>
  <a href="#connect">Connect</a>
  <a href="#reconnect">Reconnect</a>
  <a href="#connection-policy">Limits and heartbeat</a>
</nav>

## Game loop {#game-loop}

| Step | Message or request | Client action |
|---:|---|---|
| 1 | Receive `tick` | Save the Tick number and wait for `state`. |
| 2 | Receive `state` | Replace local state, compute a plan, then submit it. |
| 3 | POST command plan | Use the Tick associated with that state. |
| 4 | Receive `received` | Save the plan the server stored for that source. |
| 5 | Receive next `state` | Replace local state and read the previous Tick's results. |

```text
tick(N)
  → state
  → zero or more received messages
  → quiet while N resolves
  → tick(N + 1)
  → state containing results for N
```

The command window is fixed at 15 seconds for everyone, and it opens before
player states go out. Act as soon as `state` arrives, and never assume you have
the full 15 seconds to work with.

## Messages {#messages}

Every server message is one UTF-8 JSON text frame with two fields:

| `type` | `data` contains | What it means |
|---|---|---|
| `"tick"` | positive int64 | A new Tick is being prepared. Wait for `state`. |
| `"state"` | [`PlayerState`](api-state-model.md) | Replace local state. You can now submit a plan. |
| `"received"` | stored plan receipt | The server replaced the plan for one source. |

Parse `type` first. There are no incremental patches, no cursors, no replay
offsets, and no client-to-server business messages of any kind.

### `tick`

```json
{
  "type": "tick",
  "data": 10583
}
```

Save `10583` as the current Tick. The `state` that follows belongs to it, since
`state.data` does not repeat the number.

Do not submit yet — when `tick` goes out the server is still building each
player's view.

### `state`

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

When `state` arrives:

1. replace the previous state;
2. associate it with the most recent `tick`;
3. compute a plan;
4. POST it before the current window closes.

Everything you own is in there. Enemy entities, obstacles, and currently
available natural points or cargo piles appear only while they are visible. Resource
observations can become stale outside vision. For every field, see the
[State model](api-state-model.md); for `events`, see
[Resolution results](api-resolution-results.md).

### `received`

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
      },
      "core_action": {"type": "WAIT"}
    }
  }
}
```

| Field | Format | Meaning |
|---|---|---|
| `tick` | positive int64 | Tick that owns the stored plan. |
| `source` | `"AGENT"` or `"MANUAL"` | Plan slot that was replaced. |
| `received_at` | RFC3339Nano UTC string | Time the plan was written to the database. |
| `plan` | [`CommandPlan`](api-commands.md#commandplan-model) | Plan currently stored for this source. |

A successful new plan broadcasts `received` to every live connection that player
owns, other tabs and clients included.

Keep the latest receipt per source. A newer `AGENT` receipt replaces only the
previous `AGENT` one — the `MANUAL` receipt lives its own life.

You will not get a `received` for:

- rejected requests;
- an implicit default `WAIT`;
- an idempotent replay of a request that already completed.

And remember the receipt confirms storage, not success. Read the next
`state.data.events` for what actually happened.

### Dispatch example

```js
function onMessage(frame) {
  const message = JSON.parse(frame);

  if (message.type === 'tick') currentTick = message.data;
  else if (message.type === 'state') onState(currentTick, message.data);
  else if (message.type === 'received') onReceipt(message.data);
}
```

Check `type` before you touch `data`. If your client ignores unknown message
types, make that a deliberate compatibility decision rather than an accident.

## Connect {#connect}

Agents that are not browsers send the credential in the upgrade request:

```http
GET /api/v1/game/ws HTTP/1.1
Host: api.arenahero.io
Authorization: Bearer <token>
Upgrade: websocket
Connection: Upgrade
```

| Client | Credential | `Origin` |
|---|---|---|
| Non-browser Agent | `Authorization: Bearer <token>` | May be omitted. If present, it must be allowed. |
| Arena Hero web client | Secure Session Cookie | Required and must exactly match an allowed public origin. |

Credentials in the URL or query string are not supported at all.

### Handshake errors

Until the connection upgrades, errors come back as ordinary HTTP JSON:

| Status | `error` | Recovery |
|---:|---|---|
| 401 | `UNAUTHORIZED` | Replace the missing, invalid, revoked, or inactive credential. |
| 403 | `WEBSOCKET_ORIGIN_INVALID` | Correct the missing, malformed, duplicated, or disallowed `Origin`. |
| 409 | `PLAYER_NOT_READY` | Wait until the server starts a Tick for this player. |
| 429 | `REALTIME_CONNECTION_LIMIT` | Wait for `Retry-After: 1`, then reconnect. |

## Reconnect {#reconnect}

What you get back depends on which phase the server is in:

| Phase | Messages after reconnect |
|---|---|
| Preparing state | Current `tick`; `state` follows when ready. |
| Command window `OPEN` | Current `tick`, current `state`, latest `AGENT` receipt if present, latest `MANUAL` receipt if present. |
| Resolving | Nothing stale; wait for the next `tick`. |
| Recovered `OPEN` after crash | Same Tick, rebuilt state, restored receipts, and a new full 15-second window. |

This is a snapshot of right now, not a replay of message history. Replace your
local state and receipt assumptions with whatever arrives.

```text title="Recommended retry loop"
delay = 250ms

connect
if connected:
  delay = 250ms
  read until closed
if close code == 1008:
  stop and fix the credential or client
otherwise:
  wait random_jitter(delay)
  delay = min(delay × 2, 5s)
```

Reconnecting never extends a normal command window that is already running.

## Limits and heartbeat {#connection-policy}

This socket carries server-to-client business messages and nothing else.

| Property | Value |
|---|---|
| WebSocket Ping interval | 20 seconds |
| Pong deadline | 60 seconds |
| Credential revalidation | Approximately every 5 seconds |
| Server write deadline | 10 seconds per message |
| Client inbound frame limit | 1024 bytes |
| Compression | Disabled |

Ordinary WebSocket libraries answer protocol Ping on their own. Do not push
heartbeat JSON, command JSON, or binary business frames through this socket.

### Close codes {#close-codes}

| Code | Meaning | Client action |
|---:|---|---|
| 1000 | Normal closure | Reconnect only if continued play is desired. |
| 1001 | Server shutdown or heartbeat failure | Reconnect with jittered backoff. |
| 1008 | Credential inactive or prohibited client frame | Stop retrying and fix the client or credential. |
| 1011 | Internal stream or credential-check failure | Reconnect with backoff. |
| 1013 | Slow-client queue overflow | Discard delivery assumptions and rebuild from reconnect snapshot. |

A closed socket says nothing about whether an HTTP command was rejected. If you
lost an HTTP response, retry the exact request body under the same
`Idempotency-Key`.
