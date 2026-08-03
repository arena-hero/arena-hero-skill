"""Structural and security checks for the Arena Hero skill."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

import arena_hero
import pytest
import yaml

from scripts.sync_references import (
    DOC_GAME_CONTRACT,
    SDK_GAME_CONTRACT,
    require_contract,
)

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"

BUNDLED_DOCUMENTATION = {
    "agent-quickstart.md",
    "agent-command-loop.md",
    "api-overview.md",
    "api-leaderboard.md",
    "api-websocket.md",
    "api-commands.md",
    "api-state-model.md",
    "api-resolution-results.md",
    "api-errors.md",
    "sdk-quickstart.md",
    "sdk-reference.md",
    "reference-numbers.md",
    "reference-glossary.md",
    "reference-changelog.md",
    "reference-source-and-version.md",
    "openapi.yaml",
    "asyncapi.yaml",
}


def frontmatter() -> dict[str, object]:
    content = (ROOT / "SKILL.md").read_text()
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict)
    return parsed


def test_skill_metadata_and_references() -> None:
    metadata = frontmatter()
    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == "arena-hero"

    skill = (ROOT / "SKILL.md").read_text()
    normalized_skill = " ".join(skill.split())
    assert "15-second command window" in skill
    assert "cannot guarantee" in skill
    assert "Never guess costs, ranges, caps" in normalized_skill
    assert "references/game-rules.md" in skill
    assert "completely" in skill
    assert "references/tactic-authoring.md" in skill
    assert "references/direct-play.md" in skill
    for filename in BUNDLED_DOCUMENTATION:
        assert f"references/{filename}" in skill
    assert "[TODO" not in skill

    assert (ROOT / "scripts/direct_session.py").is_file()
    assert (ROOT / "scripts/sync_references.py").is_file()
    assert (ROOT / "references/game-rules.md").is_file()
    assert (ROOT / "references/tactic-authoring.md").is_file()
    assert (ROOT / "references/direct-play.md").is_file()
    for filename in BUNDLED_DOCUMENTATION:
        assert (REFERENCES / filename).is_file()


def test_api_key_sources_do_not_expose_the_value() -> None:
    script = (ROOT / "scripts/direct_session.py").read_text()
    assert "from getpass import getpass" in script
    assert "--api-key-file" in script
    assert "--env-file" in script
    assert "os.environ.get(API_KEY_ENV" in script
    assert "Authorization" not in script

    skill = (ROOT / "SKILL.md").read_text()
    assert "environment variables" in skill
    assert "repository" in skill
    assert "never\ndisplay it in chat or logs" in skill


def test_protocol_failures_upgrade_the_sdk_before_network_diagnosis() -> None:
    skill = (ROOT / "SKILL.md").read_text()
    assert "invalid Arena Hero WebSocket message" in skill
    assert "missing/extra-field validation error" in skill
    assert "update the official SDK before" in skill
    assert "python -m pip install --upgrade --no-cache-dir arena-hero" in skill
    assert "Do not work around a mismatch by weakening SDK validation" in skill
    assert "If the live contract is older than the bundle" in skill
    assert "requires a newer SDK than PyPI publishes" in " ".join(skill.split())

    readme = (ROOT / "README.md").read_text()
    tactic_authoring = (REFERENCES / "tactic-authoring.md").read_text()
    direct_play = (REFERENCES / "direct-play.md").read_text()
    workflow = (ROOT / ".github/workflows/validate.yml").read_text()
    assert "arena-hero==0.2.8" in readme
    assert "arena-hero>=0.2.8,<0.3" in tactic_authoring
    assert "arena-hero>=0.2.8,<0.3" in direct_play
    assert workflow.count("arena-hero==0.2.8") == 2
    assert "CoreResourceCapture" in arena_hero.__all__
    assert "HealAction" in arena_hero.__all__
    assert "HealingResult" in arena_hero.__all__
    assert hasattr(arena_hero.Ranger, "shoot_cell")


def test_agent_metadata_matches_skill() -> None:
    metadata = yaml.safe_load((ROOT / "agents/openai.yaml").read_text())
    interface = metadata["interface"]
    assert interface["display_name"] == "Arena Hero"
    assert 25 <= len(interface["short_description"]) <= 64
    assert "$arena-hero" in interface["default_prompt"]


def test_readme_explains_installation_and_both_modes() -> None:
    readme = (ROOT / "README.md").read_text()
    normalized = " ".join(readme.split())
    assert "Tactic script" in normalized
    assert "Direct play" in normalized
    assert "15-second command window" in normalized
    assert "cannot guarantee" in normalized
    assert "Complete documentation included" in normalized
    assert "references/game-rules.md" in normalized
    assert "references/sdk-quickstart.md" in normalized
    assert "references/api-overview.md" in normalized
    assert "OpenAPI and AsyncAPI" in normalized
    assert (
        "current v0.13 rules for target-free eight-direction Ranger cell fire"
        in normalized
    )
    assert "unpaid-upkeep damage to excess Units" in normalized
    assert "max(10, population × 5)" in normalized
    assert "Worker cargo-drop" in normalized
    assert "resource-node quota" in normalized
    assert "https://doc.arenahero.io/skill/overview" in normalized
    assert "Python SDK v0.2.8" in normalized
    assert "Core self-destruct" in normalized


def test_bundled_rules_cover_complete_gameplay_contract() -> None:
    rules = (ROOT / "references/game-rules.md").read_text()

    required_sections = {
        "World and terrain",
        "Tick lifecycle and resolution order",
        "Vision and information boundaries",
        "Core, production, migration, and upkeep",
        "Units and actions",
        "Movement and cell capacity",
        "Champion Beacon",
        "Combat",
        "Core destruction and respawn",
        "Commands, priority, replacement, and receipts",
    }
    for section in required_sections:
        assert f"## {section}" in rules

    required_rules = {
        "15 seconds",
        "32 x 32",
        "axis(c) = -c - 1",
        "quota(cx, cy) = max(2, floor(16 * 8 / (8 + ring(cx, cy))))",
        "After settlement of every fourth logical Tick",
        "RESOURCE_DEPLETED",
        "tier = floor(N / 20)",
        "upkeep = tier x (tier + 1) / 2",
        "SELF_DESTRUCT",
        "UNIT_SELF_DESTRUCTED",
        "WORKER_CARGO_DROPPED",
        "CORE_RESOURCE_OVERFLOW_DESTROYED",
        "CORE_RESOURCES_CAPTURED",
        "CORE_HEAL_SUCCEEDED",
        "UNIT_HEAL_FAILED",
        "resource_capacity = max(10, population x 5)",
        "DROPPED_CARGO",
        "Worker | 2 | 3 | 5",
        "Vanguard | 4 | 4 | 10",
        "Ranger | 2 | 5 | 12",
        "exact 45-degree diagonal",
        "`(3, 3)` is range 3",
        "lowest-HP hostile",
        "cell-shot miss omits `target_id`",
        "obstacles beside the line do not block it",
        "at most two occupying entities",
        "Manual explicit action > Agent explicit action > WAIT",
        "64 new submissions",
        "There is no respawn cooldown",
        "Any living Core may submit",
        "Combat has priority",
        "reason `SELF_DESTRUCT`",
        "Highest damage wins; tied damage uses the lower raw player UUID",
        "If the winner's Core also dies in that combat Tick",
        "Unit heals resolve in ascending raw UUID byte order",
        "Fatal damage cannot be healed",
        "nearest 19 Units",
        "UPKEEP_DEFICIT",
    }
    for rule in required_rules:
        assert rule in rules

    normalized_rules = " ".join(rules.split())
    assert (
        "Only obstacles in intermediate shot cells block the shot" in normalized_rules
    )
    assert "Units, Cores, and obstacles beside a diagonal never do" in normalized_rules
    assert "obstacle, Unit, or Core" not in normalized_rules


def test_bundled_api_and_sdk_documentation_is_complete() -> None:
    expected_markers = {
        "agent-quickstart.md": {
            "# Agent quickstart",
            "wss://api.arenahero.io/api/v1/game/ws",
            "POST /api/v1/game/commands",
        },
        "agent-command-loop.md": {
            "# Reliable command loop",
            "15-second window",
            "received",
            "consumed, partially recovered, or replenished",
        },
        "api-overview.md": {
            "# API overview",
            "api-websocket.md",
            "openapi.yaml",
            "asyncapi.yaml",
        },
        "api-leaderboard.md": {
            "# Leaderboard API",
            "GET https://api.arenahero.io/api/v1/leaderboard",
            "beacon_ticks_held",
        },
        "api-websocket.md": {
            "# WebSocket",
            'type": "tick',
            'type": "state',
            'type": "received',
            "Close codes",
        },
        "api-commands.md": {
            "# Command API",
            "## Plan body",
            "PICKUP_BEACON",
            "DROP_BEACON",
            "SELF_DESTRUCT",
            "HEAL",
            "Idempotency-Key",
            "RESOURCE_DEPLETED",
            "exact 45-degree diagonal",
        },
        "api-state-model.md": {
            "# State model",
            "PlayerState",
            "Champion Beacon",
            "### Terrain",
            "`RESOURCE` positions are current",
            "owner_username",
        },
        "api-resolution-results.md": {
            "# Resolution results",
            "CORE_SPAWN_SUCCEEDED",
            "SHOT_MISSED",
            "RESPAWN_DELAYED",
            "RESOURCE_DEPLETED",
            "UNIT_SELF_DESTRUCTED",
            "CORE_DESTROYED",
            "UNIT_HEAL_SUCCEEDED",
            "CORE_HEAL_FAILED",
            "WORKER_CARGO_DROPPED",
            "DROPPED_CARGO",
            "UPKEEP_DEFICIT",
        },
        "api-errors.md": {
            "# Errors and recovery",
            "COMMAND_WINDOW_CLOSED",
            "INVALID_COMMAND",
            "COMMAND_RATE_LIMITED",
        },
        "sdk-quickstart.md": {
            "# Quickstart",
            "ArenaHeroClient",
            "AsyncArenaHeroClient",
            "turn.submit()",
            "RESOURCE_DEPLETED",
            "exact 45-degree diagonal",
            "UPKEEP_DEFICIT",
            "turn.core.self_destruct()",
        },
        "sdk-reference.md": {
            "# API reference",
            "Complete public export catalog",
            "TurnClosedError",
            "latest_receipts",
            "RESOURCE_DEPLETED",
            "SelfDestructAction",
            "HealAction",
            "HealingResult",
            "exact 45-degree diagonal",
            "UPKEEP_DEFICIT",
            "self_destruct()",
        },
        "reference-numbers.md": {
            "# Rules at a glance",
            "Global command window",
            "Core migration",
            "HP recovery",
            "axis(c)",
            "eight-direction range 1-3",
            "nearest 19",
        },
        "reference-glossary.md": {
            "# Glossary",
            "**Complete plan**",
            "**World snapshot**",
            "**Resource point**",
        },
        "reference-changelog.md": {
            "# Changelog",
            "Gameplay rules v0.13",
            "Python SDK releases",
        },
        "reference-source-and-version.md": {
            "# Source and version policy",
            "Gameplay rules | v0.13",
            "Python SDK",
            "v0.2.8",
            "Reviewed server commit",
        },
    }

    for filename, markers in expected_markers.items():
        content = (REFERENCES / filename).read_text()
        for marker in markers:
            assert marker in content, f"{filename} is missing {marker!r}"

    sdk_reference = (REFERENCES / "sdk-reference.md").read_text()
    for public_name in arena_hero.__all__:
        assert f"`{public_name}`" in sdk_reference


def test_bundled_openapi_and_asyncapi_are_valid() -> None:
    openapi = yaml.safe_load((REFERENCES / "openapi.yaml").read_text())
    asyncapi = yaml.safe_load((REFERENCES / "asyncapi.yaml").read_text())

    assert openapi["openapi"] == "3.1.0"
    assert "/api/v1/game/commands" in openapi["paths"]
    assert openapi["components"]["schemas"]["CommandPlan"]
    assert (
        "RESOURCE_DEPLETED"
        in openapi["components"]["schemas"]["HarvestAction"]["description"]
    )
    assert (
        openapi["components"]["schemas"]["SelfDestructAction"]["properties"]["type"][
            "const"
        ]
        == "SELF_DESTRUCT"
    )
    assert {
        item["$ref"] for item in openapi["components"]["schemas"]["CoreAction"]["oneOf"]
    } >= {"#/components/schemas/SelfDestructAction"}
    openapi_shoot = openapi["components"]["schemas"]["ShootAction"]
    assert openapi_shoot["required"] == ["type", "expected_cell"]
    assert "lowest-HP hostile" in openapi_shoot["description"]

    assert asyncapi["asyncapi"] == "3.1.0"
    assert asyncapi["channels"]["gameStream"]
    messages = asyncapi["components"]["messages"]
    assert {"TickMessage", "StateMessage", "ReceivedMessage"} <= set(messages)
    schemas = asyncapi["components"]["schemas"]
    assert "cargo piles" in schemas["TerrainBatch"]["description"]
    assert "owner_username" in schemas["NormalCoreObject"]["required"]
    assert "owner_username" in schemas["MovingCoreObject"]["required"]
    assert schemas["Username"]["pattern"] == "^[a-z0-9_]+$"
    assert "RESOURCE_REFILLED" not in schemas["EventType"]["enum"]
    assert "UNIT_SELF_DESTRUCTED" in schemas["EventType"]["enum"]
    assert "WORKER_CARGO_DROPPED" in schemas["EventType"]["enum"]
    assert "UPKEEP_DEFICIT" in schemas["ResolutionEvent"]["description"]
    assert "RESOURCE_DEPLETED" in schemas["HarvestAction"]["description"]
    assert schemas["SelfDestructAction"]["properties"]["type"]["const"] == (
        "SELF_DESTRUCT"
    )
    assert {item["$ref"] for item in schemas["CoreAction"]["oneOf"]} >= {
        "#/components/schemas/SelfDestructAction"
    }
    assert schemas["HealAction"]["properties"]["type"]["const"] == "HEAL"
    assert schemas["ShootAction"]["required"] == ["type", "expected_cell"]
    assert "lowest-HP hostile" in schemas["ShootAction"]["description"]
    for event_type in {
        "UNIT_HEAL_SUCCEEDED",
        "UNIT_HEAL_FAILED",
        "CORE_HEAL_SUCCEEDED",
        "CORE_HEAL_FAILED",
    }:
        assert event_type in schemas["EventType"]["enum"]


def test_dynamic_resource_contract_is_consistent_across_bundle() -> None:
    files = {
        "SKILL.md": (ROOT / "SKILL.md").read_text(),
        "game-rules.md": (REFERENCES / "game-rules.md").read_text(),
        "agent-command-loop.md": (REFERENCES / "agent-command-loop.md").read_text(),
        "api-commands.md": (REFERENCES / "api-commands.md").read_text(),
        "api-state-model.md": (REFERENCES / "api-state-model.md").read_text(),
        "api-resolution-results.md": (
            REFERENCES / "api-resolution-results.md"
        ).read_text(),
        "sdk-quickstart.md": (REFERENCES / "sdk-quickstart.md").read_text(),
        "sdk-reference.md": (REFERENCES / "sdk-reference.md").read_text(),
        "tactic-authoring.md": (REFERENCES / "tactic-authoring.md").read_text(),
    }

    required_markers = {
        "game-rules.md": {
            "ring(cx, cy) = axis(cx) + axis(cy)",
            "quota(cx, cy) = max(2, floor(16 * 8 / (8 + ring(cx, cy))))",
            "only the lowest Worker UUID",
            "post-settlement world",
            "old resource coordinates are not grandfathered",
        },
        "api-resolution-results.md": {
            "RESOURCE_DEPLETED",
            "WORKER_CARGO_DROPPED",
            "DROPPED_CARGO",
            "Replenishment does not create player events",
        },
        "sdk-reference.md": {
            "resource_cells",
            "RESOURCE_DEPLETED",
            "WORKER_CARGO_DROPPED",
        },
        "tactic-authoring.md": {
            "Recompute resource targets",
            "current visible-resource set",
        },
    }
    for filename, markers in required_markers.items():
        normalized = " ".join(files[filename].split())
        for marker in markers:
            assert marker in normalized, f"{filename} is missing {marker!r}"

    combined = "\n".join(files.values())
    for obsolete in {
        "Resource cells never deplete",
        "Resource cells never run out",
        "permanent and infinite",
        "richness(d) = 1 + 256 / (256 + d)",
    }:
        assert obsolete not in combined


@pytest.mark.parametrize(
    ("repo_name", "requirements"),
    [
        ("arena-hero-doc", DOC_GAME_CONTRACT),
        ("arena-hero-python", SDK_GAME_CONTRACT),
    ],
)
def test_reference_sync_refuses_stale_game_sources(
    tmp_path: Path,
    repo_name: str,
    requirements: Mapping[str, tuple[str, ...]],
) -> None:
    with pytest.raises(RuntimeError, match="current game contract"):
        require_contract(tmp_path, repo_name, requirements)

    for relative_path, markers in requirements.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(markers))

    require_contract(tmp_path, repo_name, requirements)


def test_bundled_reference_links_resolve_locally() -> None:
    for path in REFERENCES.glob("*.md"):
        content = path.read_text()
        for href in re.findall(r"\]\(([^)]+)\)", content):
            if href.startswith(("https://", "http://", "#", "mailto:")):
                continue
            target_name = href.partition("#")[0]
            target = path.parent / target_name
            assert target.is_file(), f"{path.name} links to missing {target_name}"
