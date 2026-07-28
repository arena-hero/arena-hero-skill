#!/usr/bin/env python3
"""Session-scoped NDJSON bridge for direct Arena Hero play."""

from __future__ import annotations

import argparse
import json
import queue
import sys
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from getpass import getpass
from typing import Any, Literal, Protocol, TextIO

from arena_hero import (
    APIError,
    ArenaHeroClient,
    ArenaHeroError,
    CommandPlan,
    Received,
    Tick,
    TransportError,
    Turn,
)

DEFAULT_BASE_URL = "https://api.arenahero.io"
VIEWER_URL = "https://app.arenahero.io/arena"
DEFAULT_DECISION_TIMEOUT = 8.0
MAX_DECISION_TIMEOUT = 12.0


class DirectClient(Protocol):
    """Small public client surface used by the bridge and its tests."""

    def __enter__(self) -> DirectClient: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None: ...

    def events(self) -> Iterator[Tick | Turn | Received]: ...

    def submit(self, plan: CommandPlan) -> Any: ...


ClientFactory = Callable[..., DirectClient]
ControlKind = Literal["submit", "skip", "stop"]


class ControlError(ValueError):
    """A direct-control line is malformed or stale."""


@dataclass(frozen=True, slots=True)
class Control:
    """Validated direct-control input."""

    kind: ControlKind
    plan: CommandPlan | None = None


def emit(output: TextIO, payload: dict[str, Any]) -> None:
    """Write one compact JSON event and flush it immediately."""

    output.write(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    output.write("\n")
    output.flush()


def parse_control(raw_line: str, *, current_tick: int) -> Control:
    """Validate one agent control line against the actionable Tick."""

    try:
        payload = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        raise ControlError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ControlError("control input must be a JSON object")

    kind = payload.get("type")
    if kind == "stop":
        if set(payload) != {"type"}:
            raise ControlError("stop accepts no other fields")
        return Control(kind="stop")

    if kind == "skip":
        if set(payload) != {"type", "tick"}:
            raise ControlError("skip requires exactly type and tick")
        tick = payload.get("tick")
        if not isinstance(tick, int) or isinstance(tick, bool):
            raise ControlError("skip tick must be an integer")
        if tick != current_tick:
            raise ControlError(
                f"stale skip tick {tick}; current actionable tick is {current_tick}"
            )
        return Control(kind="skip")

    if kind == "submit":
        if set(payload) != {"type", "plan"}:
            raise ControlError("submit requires exactly type and plan")
        try:
            plan = CommandPlan.model_validate(payload.get("plan"))
        except (TypeError, ValueError) as exc:
            raise ControlError(f"invalid command plan: {exc}") from exc
        if plan.tick != current_tick:
            raise ControlError(
                f"stale plan tick {plan.tick}; current actionable tick is {current_tick}"
            )
        return Control(kind="submit", plan=plan)

    raise ControlError("type must be submit, skip, or stop")


def _read_lines(source: TextIO, lines: queue.Queue[str | None]) -> None:
    """Read controls without blocking WebSocket teardown."""

    while True:
        line = source.readline()
        if line == "":
            lines.put(None)
            return
        lines.put(line)


def _event_payload(event: Tick | Received) -> dict[str, Any]:
    if isinstance(event, Tick):
        return {"type": "tick", "tick": event.tick}
    return {
        "type": "received",
        "receipt": event.model_dump(mode="json"),
    }


def _await_control(
    *,
    turn: Turn,
    lines: queue.Queue[str | None],
    output: TextIO,
    decision_timeout: float,
) -> Control | None:
    deadline = time.monotonic() + decision_timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            emit(
                output,
                {
                    "type": "missed",
                    "tick": turn.tick,
                    "reason": "decision_timeout",
                },
            )
            return None
        try:
            raw_line = lines.get(timeout=remaining)
        except queue.Empty:
            emit(
                output,
                {
                    "type": "missed",
                    "tick": turn.tick,
                    "reason": "decision_timeout",
                },
            )
            return None
        if raw_line is None:
            return Control(kind="stop")
        if not raw_line.strip():
            continue
        try:
            return parse_control(raw_line, current_tick=turn.tick)
        except ControlError as exc:
            emit(
                output,
                {
                    "type": "input_error",
                    "tick": turn.tick,
                    "message": str(exc),
                },
            )


def run_direct_session(
    *,
    api_key: str,
    base_url: str = DEFAULT_BASE_URL,
    decision_timeout: float = DEFAULT_DECISION_TIMEOUT,
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
    client_factory: ClientFactory = ArenaHeroClient,
) -> int:
    """Run a direct session after a key has been obtained securely."""

    if not api_key:
        raise ValueError("api_key must not be empty")
    if not 0 < decision_timeout <= MAX_DECISION_TIMEOUT:
        raise ValueError(
            f"decision_timeout must be greater than 0 and at most {MAX_DECISION_TIMEOUT}"
        )

    lines: queue.Queue[str | None] = queue.Queue()
    reader = threading.Thread(
        target=_read_lines,
        args=(input_stream, lines),
        daemon=True,
        name="arena-hero-direct-input",
    )
    reader.start()

    with client_factory(api_key=api_key, base_url=base_url) as game:
        emit(
            output_stream,
            {
                "type": "ready",
                "base_url": base_url,
                "viewer_url": VIEWER_URL,
                "decision_timeout_seconds": decision_timeout,
                "warning": (
                    "The server has a 15-second command window. "
                    "Direct play cannot guarantee an on-time submission."
                ),
            },
        )
        for event in game.events():
            if isinstance(event, (Tick, Received)):
                emit(output_stream, _event_payload(event))
                continue

            emit(
                output_stream,
                {
                    "type": "turn",
                    "tick": event.tick,
                    "decision_timeout_seconds": decision_timeout,
                    "state": event.state.model_dump(mode="json"),
                },
            )
            control = _await_control(
                turn=event,
                lines=lines,
                output=output_stream,
                decision_timeout=decision_timeout,
            )
            if control is None:
                continue
            if control.kind == "stop":
                emit(
                    output_stream,
                    {"type": "stopped", "reason": "requested_or_input_closed"},
                )
                return 0
            if control.kind == "skip":
                emit(output_stream, {"type": "skipped", "tick": event.tick})
                continue

            if control.plan is None:
                raise RuntimeError("validated submit control has no plan")
            try:
                accepted = game.submit(control.plan)
            except (APIError, TransportError) as exc:
                payload: dict[str, Any] = {
                    "type": "submit_error",
                    "tick": event.tick,
                    "error": type(exc).__name__,
                    "message": str(exc),
                }
                if isinstance(exc, APIError):
                    payload["status_code"] = exc.status_code
                    payload["error_code"] = exc.error
                emit(output_stream, payload)
                if isinstance(exc, APIError) and exc.status_code in {401, 403}:
                    return 1
                continue
            emit(
                output_stream,
                {
                    "type": "accepted",
                    "acknowledgement": accepted.model_dump(mode="json"),
                },
            )

    emit(output_stream, {"type": "stopped", "reason": "server_closed"})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Direct Arena Hero bridge. The API key is accepted only from a "
            "hidden interactive prompt."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"public Arena Hero HTTP origin (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--decision-timeout",
        type=float,
        default=DEFAULT_DECISION_TIMEOUT,
        help=(
            "seconds to wait for an agent control line "
            f"(default: {DEFAULT_DECISION_TIMEOUT}, max: {MAX_DECISION_TIMEOUT})"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0 < args.decision_timeout <= MAX_DECISION_TIMEOUT:
        print(
            "Decision timeout must be greater than 0 and at most "
            f"{MAX_DECISION_TIMEOUT} seconds.",
            file=sys.stderr,
        )
        return 2
    if not sys.stdin.isatty():
        print(
            "Direct play requires an interactive TTY for hidden API-key input. "
            "Do not pipe or pass the key as an argument.",
            file=sys.stderr,
        )
        return 2

    print(
        "WARNING: every Tick has only a 15-second command window. "
        "Direct play cannot guarantee it will submit in time.",
        file=sys.stderr,
    )
    api_key = getpass("Arena Hero API key: ")
    if not api_key:
        print("API key cannot be empty.", file=sys.stderr)
        return 2

    try:
        return run_direct_session(
            api_key=api_key,
            base_url=args.base_url,
            decision_timeout=args.decision_timeout,
        )
    except (ArenaHeroError, OSError, TimeoutError, ValueError) as exc:
        emit(
            sys.stdout,
            {
                "type": "error",
                "error": type(exc).__name__,
                "message": str(exc),
            },
        )
        return 1
    except KeyboardInterrupt:
        emit(sys.stdout, {"type": "stopped", "reason": "keyboard_interrupt"})
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
