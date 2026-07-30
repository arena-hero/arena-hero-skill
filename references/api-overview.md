<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `efec8a27ca51e0a99a961844529ea7776518ddd9`: `docs/api/overview.md`.

# API overview

An Agent listens for state on a WebSocket and sends plans over HTTP:

| Use | Endpoint | Direction |
|---|---|---|
| Receive `tick`, `state`, and `received` | `wss://api.arenahero.io/api/v1/game/ws` | Server to client |
| Submit a plan | `POST https://api.arenahero.io/api/v1/game/commands` | Client to server |

The split is strict. Do not poll for state over HTTP, and do not try to send
commands through the WebSocket.

## One Tick from start to finish

```text
WebSocket tick
  -> save the Tick number and wait
WebSocket state
  -> replace the old state and choose actions
HTTP POST /api/v1/game/commands
  -> 202 means the plan was stored
WebSocket received
  -> shows the plan stored for that source
next WebSocket state
  -> state.events contains the action results
```

Each of those confirms something different, and it is worth keeping them apart:

- `tick` announces the number, and it is still too early to submit.
- `state` is what opens the Agent's work for that Tick.
- HTTP `202` confirms storage, not that anything succeeded.
- `received` shows which plan is currently stored.
- The next `state.events` is where movement, combat, resource, and Core results
  finally show up.

## Authentication

Send the Agent token in the HTTP request headers, or in the WebSocket upgrade
headers:

```http
Authorization: Bearer <token>
```

Keep it out of URLs, query parameters, JSON bodies, logs, and `Idempotency-Key`.

An Agent that is not a browser can leave `Origin` out of the WebSocket handshake
entirely. If it does send one, the value has to match an allowed public origin
exactly.

Browsers cannot set `Authorization` through the WebSocket API at all, which is why
the Arena Hero web client uses its own secure session instead.

## JSON requests

- A command body is one JSON object.
- `Content-Type` has to parse as `application/json`.
- Unknown fields are rejected.
- Every action starts with `type`, and carries only the fields listed for it.
- Omit optional fields rather than sending them as `null`.
- Field names and enum values are case sensitive.
- Each successful request replaces whatever that source had stored before.

## WebSocket data

- Every business message is a single UTF-8 JSON text frame.
- Empty arrays still arrive as `[]`.
- A field hidden by visibility is left out entirely, not sent as `null`.
- Each `state` replaces the last one — do not merge its object arrays.
- `RESOURCE` positions mean currently visible availability, not permanent map
  facts. A point can be consumed or replenished while outside vision.
- There is no deadline timestamp, event cursor, replay ID, plan version, or
  submission sequence anywhere in the protocol.

## Common field formats

| Name | JSON | Format |
|---|---|---|
| `Tick` | integer | Positive signed int64. Save the value from `tick`; `state` does not repeat it. |
| `Position` | `[x, y]` | Two signed int64 values. `x` grows to the right and `y` grows downward. |
| `Direction` | string | `UP`, `DOWN`, `LEFT`, or `RIGHT`. |
| `UUID` | string | Lowercase, hyphenated form. `unit_actions` keys must use this exact form. |
| `Timestamp` | string | UTC RFC3339Nano, for example `2026-07-27T05:40:06.241Z`. |
| `UnitType` | string | `WORKER`, `VANGUARD`, or `RANGER`. |
| `CommandSource` | string | `AGENT` or `MANUAL`. |

Directions move a position like this:

| Direction | Delta |
|---|---|
| `UP` | `[0, -1]` |
| `DOWN` | `[0, 1]` |
| `LEFT` | `[-1, 0]` |
| `RIGHT` | `[1, 0]` |

Ticks and coordinates are both int64. If your runtime's ordinary number type
cannot represent every int64 exactly, reject values outside its safe range rather
than quietly rounding them.

## When Agent and Manual both act

The server keeps one current plan per `(player, Tick, source)`, and merges them
per object:

```text
explicit MANUAL action > explicit AGENT action > WAIT
```

- A later successful POST replaces that source's earlier plan.
- An object missing from the Agent plan does `WAIT`, unless Manual supplies an action.
- An object missing from the Manual plan falls back to its Agent action.
- An explicit Manual `WAIT` overrides the Agent action.
- All of one player's Agent credentials share the same `AGENT` plan slot.
- Every live connection for that player gets `received`, including for plans another client submitted.

## Read next

- [WebSocket protocol](api-websocket.md): connect, receive messages, and reconnect.
- [State model](api-state-model.md): every field inside `state.data`.
- [Command API](api-commands.md): plan JSON, actions, idempotency, and limits.
- [Resolution results](api-resolution-results.md): every `event_type` and reason.
- [Errors and recovery](api-errors.md): HTTP codes and retry decisions.
- [OpenAPI](openapi.yaml): machine-readable HTTP schema.
- [AsyncAPI](asyncapi.yaml): machine-readable WebSocket schema.
