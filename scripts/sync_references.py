"""Bundle the public Arena Hero documentation into this skill."""

from __future__ import annotations

import argparse
import ast
import posixpath
import re
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"

DOC_FILES = {
    "docs/agent/quickstart.md": "agent-quickstart.md",
    "docs/agent/command-loop.md": "agent-command-loop.md",
    "docs/api/overview.md": "api-overview.md",
    "docs/api/websocket.md": "api-websocket.md",
    "docs/api/commands.md": "api-commands.md",
    "docs/api/state-model.md": "api-state-model.md",
    "docs/api/resolution-results.md": "api-resolution-results.md",
    "docs/api/errors.md": "api-errors.md",
    "docs/reference/numbers.md": "reference-numbers.md",
    "docs/reference/glossary.md": "reference-glossary.md",
    "docs/reference/changelog.md": "reference-changelog.md",
    "docs/reference/source-and-version.md": "reference-source-and-version.md",
}

SDK_FILES = {
    "docs/quickstart.md": "sdk-quickstart.md",
    "docs/api-reference.md": "sdk-reference.md",
}

SCHEMA_FILES = {
    "static/openapi.yaml": "openapi.yaml",
    "static/asyncapi.yaml": "asyncapi.yaml",
}

LINK_ALIASES = {
    "docs/sdk/quickstart.md": "sdk-quickstart.md",
    "docs/sdk/reference.md": "sdk-reference.md",
    "/openapi.yaml": "openapi.yaml",
    "/asyncapi.yaml": "asyncapi.yaml",
}

DOC_GAME_CONTRACT: Mapping[str, tuple[str, ...]] = {
    "docs/api/commands.md": (
        "CORE_RESOURCE_FULL",
        "exact 45-degree diagonal",
        "`HEAL`",
        "RESOURCE_DEPLETED",
        "SELF_DESTRUCT",
        "WORKER_CARGO_DROPPED",
    ),
    "docs/api/resolution-results.md": (
        "CORE_HEAL_SUCCEEDED",
        "CORE_RESOURCES_CAPTURED",
        "CORE_RESOURCE_OVERFLOW_DESTROYED",
        "RESOURCE_DEPLETED",
        "UNIT_SELF_DESTRUCTED",
        "UNIT_HEAL_FAILED",
        "WORKER_CARGO_DROPPED",
        "DROPPED_CARGO",
    ),
    "docs/api/state-model.md": ("dead Workers", "owner_username"),
    "docs/reference/numbers.md": (
        "axis(c)",
        "Cargo piles",
        "HP recovery",
        "eight-direction range 1-3",
        "resource_capacity = max(10, population × 5)",
    ),
    "docs/reference/source-and-version.md": (
        "Gameplay rules | v0.10",
        "Python SDK",
        "v0.2.6",
    ),
    "static/openapi.yaml": ("HEAL", "RESOURCE_DEPLETED", "SELF_DESTRUCT"),
    "static/asyncapi.yaml": (
        "RESOURCE_DEPLETED",
        "UNIT_HEAL_SUCCEEDED",
        "CORE_HEAL_FAILED",
        "SELF_DESTRUCT",
        "WORKER_CARGO_DROPPED",
        "owner_username",
    ),
}

SDK_GAME_CONTRACT: Mapping[str, tuple[str, ...]] = {
    "docs/quickstart.md": (
        "unit.heal()",
        "RESOURCE_DEPLETED",
        "cargo piles left by dead Workers",
        "exact 45-degree diagonal",
        "minimum capacity of 10",
        "resource_space",
    ),
    "docs/api-reference.md": (
        "HealAction",
        "HealingResult",
        "CORE_RESOURCES_CAPTURED",
        "core_resource_capture",
        "CORE_RESOURCE_OVERFLOW_DESTROYED",
        "exact 45-degree diagonal",
        "RESOURCE_DEPLETED",
        "SelfDestructAction",
        "WORKER_CARGO_DROPPED",
        "CORE_RESOURCE_MINIMUM_CAPACITY",
        "owner_username",
    ),
}

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n+", re.DOTALL)
MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")


def git_head(repo: Path) -> str:
    git_dir = repo / ".git"
    if git_dir.is_file():
        marker = git_dir.read_text().strip()
        git_dir = (repo / marker.removeprefix("gitdir: ").strip()).resolve()

    head = (git_dir / "HEAD").read_text().strip()
    if not head.startswith("ref: "):
        return head

    ref = head.removeprefix("ref: ")
    loose_ref = git_dir / ref
    if loose_ref.is_file():
        return loose_ref.read_text().strip()

    for line in (git_dir / "packed-refs").read_text().splitlines():
        if line and not line.startswith(("#", "^")):
            commit, name = line.split(" ", 1)
            if name == ref:
                return commit
    raise RuntimeError(f"Could not resolve {ref} in {repo}")


def require_contract(
    repo: Path,
    repo_name: str,
    requirements: Mapping[str, tuple[str, ...]],
) -> None:
    missing: list[str] = []
    for relative_path, markers in requirements.items():
        path = repo / relative_path
        if not path.is_file():
            missing.append(f"{relative_path} (missing file)")
            continue
        content = path.read_text()
        for marker in markers:
            if marker not in content:
                missing.append(f"{relative_path} (missing {marker!r})")
    if missing:
        details = ", ".join(missing)
        raise RuntimeError(
            f"{repo_name} does not contain the current game "
            f"contract; refusing to overwrite bundled references: {details}"
        )


def rewrite_links(
    text: str,
    source: str,
    targets: dict[str, str],
) -> str:
    source_path = PurePosixPath(source)

    def replace(match: re.Match[str]) -> str:
        href = match.group(1)
        if href.startswith(("https://", "http://", "#", "mailto:")):
            return match.group(0)

        if href.startswith("pathname:///"):
            path, separator, anchor = href.removeprefix("pathname:///").partition("#")
            target = SCHEMA_FILES.get(f"static/{path}")
        elif href.startswith("/"):
            path, separator, anchor = href.partition("#")
            target = LINK_ALIASES.get(path)
        else:
            path, separator, anchor = href.partition("#")
            resolved = posixpath.normpath(str(source_path.parent / path))
            target = targets.get(resolved)

        if target is None:
            return match.group(0)
        suffix = f"#{anchor}" if separator else ""
        return f"]({target}{suffix})"

    return MARKDOWN_LINK.sub(replace, text)


def write_markdown_bundle(
    source_repo: Path,
    repo_name: str,
    source_commit: str,
    sources: dict[str, str],
    link_targets: dict[str, str],
) -> None:
    for source, target in sources.items():
        content = FRONTMATTER.sub("", (source_repo / source).read_text())
        content = rewrite_links(content, source, link_targets)
        header = (
            "<!-- Generated from contract-aligned upstream sources by "
            "scripts/sync_references.py. -->\n\n"
            f"> Bundled from `{repo_name}` revision `{source_commit}`: `{source}`.\n\n"
        )
        (REFERENCES / target).write_text(header + content)


def public_exports(sdk_repo: Path) -> list[str]:
    module = ast.parse((sdk_repo / "src/arena_hero/__init__.py").read_text())
    for node in module.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in node.targets
            ):
                exports = ast.literal_eval(node.value)
                if isinstance(exports, list) and all(
                    isinstance(item, str) for item in exports
                ):
                    return exports
    raise RuntimeError("Could not find arena_hero.__all__")


def append_sdk_exports(sdk_repo: Path) -> None:
    target = REFERENCES / SDK_FILES["docs/api-reference.md"]
    exports = public_exports(sdk_repo)
    catalog = (
        "\n\n## Complete public export catalog\n\n"
        "The `arena_hero` package exports the following public names from its "
        "top-level module:\n\n" + ", ".join(f"`{name}`" for name in exports) + ".\n"
    )
    target.write_text(target.read_text().rstrip() + catalog)


def write_schema_bundle(
    docs_repo: Path,
    docs_commit: str,
) -> None:
    for source, target in SCHEMA_FILES.items():
        header = (
            "# Generated from contract-aligned upstream sources by "
            "scripts/sync_references.py.\n"
            f"# Bundled from arena-hero-doc revision {docs_commit}: {source}.\n"
        )
        content = (docs_repo / source).read_text()
        (REFERENCES / target).write_text(header + content)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--docs-repo",
        type=Path,
        default=ROOT.parent / "arena-hero-doc",
    )
    parser.add_argument(
        "--sdk-repo",
        type=Path,
        default=ROOT.parent / "arena-hero-python",
    )
    parser.add_argument(
        "--skip-sdk",
        action="store_true",
        help="refresh docs and schemas without replacing the bundled SDK references",
    )
    parser.add_argument(
        "--revision-suffix",
        default="",
        help="append a source-revision label such as +working-tree",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    docs_repo = args.docs_repo.resolve()
    sdk_repo = args.sdk_repo.resolve()
    require_contract(
        docs_repo,
        "arena-hero-doc",
        DOC_GAME_CONTRACT,
    )
    docs_commit = git_head(docs_repo) + args.revision_suffix
    link_targets = {**DOC_FILES, **SCHEMA_FILES, **LINK_ALIASES}

    REFERENCES.mkdir(exist_ok=True)
    write_markdown_bundle(
        docs_repo,
        "arena-hero-doc",
        docs_commit,
        DOC_FILES,
        link_targets,
    )
    if not args.skip_sdk:
        require_contract(
            sdk_repo,
            "arena-hero-python",
            SDK_GAME_CONTRACT,
        )
        sdk_commit = git_head(sdk_repo) + args.revision_suffix
        write_markdown_bundle(
            sdk_repo,
            "arena-hero-python",
            sdk_commit,
            SDK_FILES,
            SDK_FILES,
        )
        append_sdk_exports(sdk_repo)
    write_schema_bundle(docs_repo, docs_commit)


if __name__ == "__main__":
    main()
