"""Tests for the direct-play bridge without live credentials or network."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from arena_hero import (
    APIError,
    Accepted,
    CommandPlan,
    PlayerState,
    Received,
    Tick,
    Turn,
)

from scripts.direct_session import (
    ControlError,
    load_api_key,
    main,
    parse_control,
    run_direct_session,
)

DUMMY_API_KEY = "not-a-real-key"  # pragma: allowlist secret


def player_state() -> PlayerState:
    return PlayerState.model_validate(
        {
            "status": "ACTIVE",
            "resources": 3,
            "population": 1,
            "champion_beacon": {"position": [0, 0]},
            "objects": [
                {
                    "kind": "CORE",
                    "id": "00000000-0000-4000-8000-000000000001",
                    "controlled": True,
                    "owner_username": "arena_hero",
                    "position": [0, 0],
                    "hp": 5,
                    "shield": 5,
                    "state": "NORMAL",
                },
                {
                    "kind": "UNIT",
                    "id": "00000000-0000-4000-8000-000000000002",
                    "controlled": True,
                    "position": [1, 0],
                    "hp": 2,
                    "unit_type": "WORKER",
                    "cargo": 0,
                },
            ],
            "events": [],
        }
    )


class FakeClient:
    submitted: list[CommandPlan] = []

    def __init__(self, **_kwargs: Any) -> None:
        self.turn = Turn(tick=9, state=player_state(), submitter=self._submitter)

    def __enter__(self) -> FakeClient:
        type(self).submitted = []
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        return None

    def events(self) -> Iterator[Tick | Turn | Received]:
        yield Tick(tick=9)
        yield self.turn
        yield Received(
            tick=9,
            source="AGENT",
            received_at=datetime(2026, 7, 28, tzinfo=UTC),
            plan=CommandPlan(tick=9),
        )

    def submit(self, plan: CommandPlan) -> Accepted:
        type(self).submitted.append(plan)
        return Accepted(
            accepted=True,
            tick=plan.tick,
            source="AGENT",
            received_at=datetime(2026, 7, 28, tzinfo=UTC),
        )

    @staticmethod
    def _submitter(plan: CommandPlan, _key: str | None) -> Accepted:
        raise AssertionError(f"Turn.submit should not be used: {plan}")


class RejectingClient(FakeClient):
    def submit(self, plan: CommandPlan) -> Accepted:
        raise APIError(status_code=409, error="COMMAND_WINDOW_CLOSED")


def output_events(output: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in output.getvalue().splitlines()]


def test_parse_submit_for_current_tick() -> None:
    control = parse_control(
        json.dumps(
            {
                "type": "submit",
                "plan": {
                    "tick": 9,
                    "unit_actions": {
                        "00000000-0000-4000-8000-000000000002": {"type": "HARVEST"}
                    },
                    "core_action": None,
                },
            }
        ),
        current_tick=9,
    )

    assert control.kind == "submit"
    assert control.plan is not None
    assert control.plan.tick == 9


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "submit", "plan": {"tick": 8}},
        {"type": "skip", "tick": 8},
        {"type": "stop", "tick": 9},
        {"type": "unknown"},
        [],
    ],
)
def test_parse_control_rejects_stale_or_malformed_input(payload: object) -> None:
    with pytest.raises(ControlError):
        parse_control(json.dumps(payload), current_tick=9)


def test_load_api_key_from_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARENA_HERO_API_KEY", DUMMY_API_KEY)

    assert load_api_key(can_prompt=False) == DUMMY_API_KEY


def test_load_api_key_from_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ARENA_HERO_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        f'ARENA_HERO_API_KEY="{DUMMY_API_KEY}"\n',
        encoding="utf-8",
    )

    assert load_api_key(can_prompt=False) == DUMMY_API_KEY


def test_load_api_key_from_repository_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ARENA_HERO_API_KEY", "environment-key")
    key_file = tmp_path / "arena-key.txt"
    key_file.write_text(DUMMY_API_KEY, encoding="utf-8")

    assert load_api_key(api_key_file=key_file, can_prompt=False) == DUMMY_API_KEY


def test_load_api_key_uses_hidden_prompt_as_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ARENA_HERO_API_KEY", raising=False)

    assert (
        load_api_key(
            can_prompt=True,
            prompt=lambda _message: DUMMY_API_KEY,
        )
        == DUMMY_API_KEY
    )


def test_direct_session_submits_and_emits_protocol_events() -> None:
    command = {
        "type": "submit",
        "plan": {
            "tick": 9,
            "unit_actions": {},
            "core_action": {"type": "WAIT"},
        },
    }
    output = io.StringIO()

    exit_code = run_direct_session(
        api_key=DUMMY_API_KEY,
        input_stream=io.StringIO(json.dumps(command) + "\n"),
        output_stream=output,
        client_factory=FakeClient,
    )

    events = output_events(output)
    assert exit_code == 0
    assert [event["type"] for event in events] == [
        "ready",
        "tick",
        "turn",
        "accepted",
        "received",
        "stopped",
    ]
    assert events[2]["state"]["resources"] == 3
    assert FakeClient.submitted == [CommandPlan(tick=9, core_action={"type": "WAIT"})]


def test_direct_session_can_skip_without_submitting() -> None:
    output = io.StringIO()

    exit_code = run_direct_session(
        api_key=DUMMY_API_KEY,
        input_stream=io.StringIO('{"type":"skip","tick":9}\n'),
        output_stream=output,
        client_factory=FakeClient,
    )

    assert exit_code == 0
    assert "skipped" in [event["type"] for event in output_events(output)]
    assert FakeClient.submitted == []


def test_direct_session_reports_submit_rejection_without_exposing_key() -> None:
    command = {
        "type": "submit",
        "plan": {"tick": 9, "unit_actions": {}, "core_action": None},
    }
    output = io.StringIO()

    exit_code = run_direct_session(
        api_key=DUMMY_API_KEY,
        input_stream=io.StringIO(json.dumps(command) + "\n"),
        output_stream=output,
        client_factory=RejectingClient,
    )

    events = output_events(output)
    submit_error = next(event for event in events if event["type"] == "submit_error")
    assert exit_code == 0
    assert submit_error["status_code"] == 409
    assert submit_error["error_code"] == "COMMAND_WINDOW_CLOSED"
    assert DUMMY_API_KEY not in output.getvalue()


def test_direct_session_stops_when_input_closes() -> None:
    output = io.StringIO()

    exit_code = run_direct_session(
        api_key=DUMMY_API_KEY,
        input_stream=io.StringIO(),
        output_stream=output,
        client_factory=FakeClient,
    )

    events = output_events(output)
    assert exit_code == 0
    assert events[-1] == {
        "reason": "requested_or_input_closed",
        "type": "stopped",
    }
    assert FakeClient.submitted == []


def test_cli_rejects_unsafe_timeout_before_requesting_a_key(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--decision-timeout", "13"]) == 2
    assert "at most 12.0 seconds" in capsys.readouterr().err
