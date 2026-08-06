<!-- Generated from contract-aligned upstream sources by scripts/sync_references.py. -->

> Bundled from `arena-hero-doc` revision `166ef865a0ceec280b5fd8b9ffff80eb613674c7`: `docs/api/errors.md`.

# Errors and recovery

Branch on the HTTP status and the `error` code. The optional `message` field is
written for logs and for people, so do not build logic on it.

## Read the response

A request rejected before command handling usually looks like this:

```json
{
  "error": "UNAUTHORIZED"
}
```

Once it has reached the command gate, a rejection also carries
`"accepted": false`:

```json
{
  "accepted": false,
  "error": "TICK_MISMATCH",
  "tick": 10582,
  "current_tick": 10583
}
```

And an invalid plan comes with one or more reasons:

```json
{
  "accepted": false,
  "error": "INVALID_COMMAND",
  "details": [
    {
      "unit_id": "9d3e4941-2816-4a39-a220-df8cd95e877d",
      "reason": "RANGER_CANNOT_HARVEST"
    },
    {
      "reason": "INVALID_UNIT_TYPE"
    }
  ]
}
```

Transport, authentication, JSON, concurrency, and internal errors have no
`accepted` field at all — and its absence never means the command was accepted.

## HTTP errors

| Status | `error` | Extra fields | What went wrong |
|---:|---|---|---|
| 400 | `INVALID_JSON` | `message` | The body is empty or malformed, has multiple JSON values, has an unknown or wrongly typed field, contains a malformed UUID, or uses a noncanonical `unit_actions` UUID key. |
| 400 | `IDEMPOTENCY_KEY_INVALID` | none | The header is missing or is not 8-128 visible ASCII bytes (`0x21`-`0x7e`). |
| 401 | `UNAUTHORIZED` | none | The bearer credential is missing, invalid, or inactive. |
| 403 | `CSRF_INVALID` | none | A browser Manual request failed CSRF validation. Agent bearer requests do not use CSRF. |
| 409 | `COMMAND_WINDOW_CLOSED` | `accepted: false` | The Tick exists, but its command window is closed or the body arrived at or after the deadline. |
| 409 | `TICK_MISMATCH` | `accepted: false`; responses after persistence lookup also include `tick` and `current_tick` | The submitted Tick is not the current command Tick. |
| 409 | `IDEMPOTENCY_CONFLICT` | `accepted: false` | This player and source already used the key with different raw request bytes. |
| 413 | `REQUEST_BODY_TOO_LARGE` | `message` | The body is larger than this deployment allows. |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | none | The parsed media type is not `application/json`. Parameters such as `charset=utf-8` are allowed. |
| 422 | `INVALID_COMMAND` | `accepted: false`, nonempty `details` | The JSON shape is valid, but the plan refers to an invalid player, Unit, or action. |
| 429 | `COMMAND_CONCURRENCY_LIMIT` | `Retry-After: 1` header | More than four command bodies are being processed for the same player and credential kind. |
| 429 | `COMMAND_RATE_LIMITED` | `accepted: false`; `Retry-After: 1` header | This `(player, Tick, source)` has attempted more than 64 new admissions. |
| 500 | `INTERNAL_ERROR` | none | The server could not finish the request. |
| 503 | `TICK_NOT_READY` | `accepted: false` | The Tick is not initialized, the player's state is not ready, or Tick processing failed. |

Maximum body size is deployment configuration rather than part of the protocol.
Keep plans small, and leave out actions that would only have said `WAIT`.

## Should you retry?

| Result | Retry the same key and body? | What to do next |
|---|---|---|
| Network timeout or reset after upload | Yes | Keep the same body until you know the original result. |
| `500 INTERNAL_ERROR` | Yes | Use a bounded backoff. |
| `429 COMMAND_CONCURRENCY_LIMIT` | Yes | Wait for `Retry-After`. |
| `503 TICK_NOT_READY` | Usually not yet | Wait for `state` or reconnect. Recompute if a newer state arrives. |
| `409 COMMAND_WINDOW_CLOSED` | Only to recover a possibly completed original request | Wait for the next state before making a new plan. |
| `409 TICK_MISMATCH` | Only to recover an original idempotent result | Recompute from the current state. |
| `409 IDEMPOTENCY_CONFLICT` | No | Use a new key only for a genuinely new request. |
| `422 INVALID_COMMAND` | No | Fix the plan. If the window is still open, submit it as a new request with a new key. |
| `429 COMMAND_RATE_LIMITED` | No new requests for that source and Tick | Keep the last valid plan and wait for the next state. |
| `400`, `401`, `403`, `413`, `415` | Not unchanged | Fix the request or credential first. |

Completed idempotent responses are kept for seven days. Within that window, the
same key with a byte-for-byte identical body returns the original status and
body, even long after the command window closed. Replaying an earlier `202`
stores nothing again and sends no second `received`.

## Validation reasons

When the problem is with a Unit action, `details[].unit_id` names the Unit. It
is absent when the problem is with the whole plan or with the Core action.

The list order is stable: the Tick problem first, then Unit problems in UUID byte
order, then the Core problem.

| `reason` | Applies to | What to fix |
|---|---|---|
| `TICK_MUST_BE_POSITIVE` | Plan | `tick` is missing, zero, or negative. |
| `UNIT_NOT_OWNED` | Unit | The key is not a living Unit owned by this player. |
| `UNKNOWN_ACTION_TYPE` | Unit | `type` is not a Unit action. |
| `UNKNOWN_CORE_ACTION_TYPE` | Core | `type` is not a Core action. |
| `UNEXPECTED_ACTION_FIELDS` | Unit or Core | The action contains a field that its `type` does not allow, even if the value is `null`, empty, or zero. |
| `INVALID_DIRECTION` | `MOVE`, `SWEEP`, `START_MOVE` | `direction` is missing or is not `UP`, `DOWN`, `LEFT`, or `RIGHT`. |
| `INVALID_UNIT_TYPE` | `SPAWN` | `unit_type` is missing or is not `WORKER`, `VANGUARD`, or `RANGER`. |
| `TARGET_ID_REQUIRED` | `SHOOT` | An explicitly supplied `target_id` is the nil UUID. Omit the field for a cell shot; a malformed UUID returns `INVALID_JSON`. |
| `EXPECTED_CELL_REQUIRED` | `SHOOT` | `expected_cell` is missing. |
| `VANGUARD_CANNOT_HARVEST` | Unit | A Vanguard selected `HARVEST`. |
| `RANGER_CANNOT_HARVEST` | Unit | A Ranger selected `HARVEST`. |
| `VANGUARD_CANNOT_DEPOSIT` | Unit | A Vanguard selected `DEPOSIT`. |
| `RANGER_CANNOT_DEPOSIT` | Unit | A Ranger selected `DEPOSIT`. |
| `WORKER_CANNOT_SWEEP` | Unit | A Worker selected `SWEEP`. |
| `RANGER_CANNOT_SWEEP` | Unit | A Ranger selected `SWEEP`. |
| `WORKER_CANNOT_SHOOT` | Unit | A Worker selected `SHOOT`. |
| `VANGUARD_CANNOT_SHOOT` | Unit | A Vanguard selected `SHOOT`. |

`INVALID_COMMAND` leaves your last valid plan alone.

## Where the request stopped

A new request is checked in this order:

1. bearer authentication and, for browser Manual calls, CSRF;
2. the per-player and credential-kind body concurrency limit;
3. `Content-Type` and `Idempotency-Key`;
4. body size and JSON decoding;
5. the Tick, command window, and rate limit;
6. the current player, Unit, and action fields;
7. idempotency storage and plan replacement.

Knowing the order explains errors that otherwise look interchangeable. A
malformed UUID never gets past step 4, so it is `INVALID_JSON`. A well-formed
UUID belonging to someone else survives to step 6 and comes back as
`INVALID_COMMAND` with `UNIT_NOT_OWNED`.

## WebSocket failures

The handshake can return:

- `401 UNAUTHORIZED`
- `403 WEBSOCKET_ORIGIN_INVALID`
- `409 PLAYER_NOT_READY`
- `429 REALTIME_CONNECTION_LIMIT` with `Retry-After: 1`

After the upgrade, work from the close-code table in
[WebSocket protocol](api-websocket.md#close-codes). Retry temporary failures with
randomized exponential backoff from 250 ms up to 5 seconds, and stop retrying
after `1008` until the credential or the client behavior is fixed.

Once reconnected, replace your local state and saved receipts with the snapshot
the server sends. Do not invent heartbeat messages. And treat `SHOT_MISSED` as an
unknown miss rather than as a way to probe for hidden targets.
