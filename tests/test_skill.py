"""Structural and security checks for the Arena Hero skill."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


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
    assert "[TODO" not in skill

    assert (ROOT / "scripts/direct_session.py").is_file()
    assert (ROOT / "references/game-rules.md").is_file()
    assert (ROOT / "references/tactic-authoring.md").is_file()
    assert (ROOT / "references/direct-play.md").is_file()


def test_api_key_has_no_unsafe_input_path() -> None:
    script = (ROOT / "scripts/direct_session.py").read_text()
    assert "getpass(" in script
    assert "--api-key" not in script
    assert "os.environ" not in script
    assert "environ[" not in script
    assert "Authorization" not in script


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
    assert "Complete rules included" in normalized
    assert "references/game-rules.md" in normalized
    assert "https://doc.arenahero.io/skill/overview" in normalized


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
        "richness(d) = 1 + 256 / (256 + d)",
        "tier = floor(N / 20)",
        "upkeep = tier x (tier + 1) / 2",
        "Worker | 2 | 3 | 5",
        "Vanguard | 4 | 4 | 10",
        "Ranger | 2 | 5 | 12",
        "at most two occupying entities",
        "Manual explicit action > Agent explicit action > WAIT",
        "64 new submissions",
        "20 logical Ticks",
    }
    for rule in required_rules:
        assert rule in rules
