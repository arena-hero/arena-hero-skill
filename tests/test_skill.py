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
    assert "15-second command window" in skill
    assert "cannot guarantee" in skill
    assert "Never guess costs, ranges, caps" in skill
    assert "references/tactic-authoring.md" in skill
    assert "references/direct-play.md" in skill
    assert "[TODO" not in skill

    assert (ROOT / "scripts/direct_session.py").is_file()
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
