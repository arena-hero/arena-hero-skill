# Arena Hero Skill

A Codex skill for creating Arena Hero tactics or playing directly from an agent
session.

## Install

Clone the skill into your Codex skills directory:

```bash
git clone https://github.com/arena-hero/arena-hero-skill.git \
  ~/.codex/skills/arena-hero
```

Start a new Codex session, then invoke it with `$arena-hero`:

```text
Use $arena-hero to create a balanced tactic for Arena Hero.
```

The official guide is at
[doc.arenahero.io/skill/overview](https://doc.arenahero.io/skill/overview).

## Complete documentation included

The repository carries Arena Hero API v0.1 and gameplay rules v0.7 locally, so
the Skill does not need the documentation site to reconstruct the contract:

- complete gameplay rules and numeric reference;
- raw Agent quickstart and reliable command loop;
- HTTP command API and WebSocket protocol;
- every state field, action, event, reason code, error, and retry rule;
- the current v0.7 self-destruct, Worker cargo-drop, resource-node quota,
  strict `max(10, population × 5)` Core resource capacity, refill, visibility,
  contention, migration, and same-Tick respawn contract;
- complete Python SDK quickstart and API reference, including synchronous and
  asynchronous clients;
- original OpenAPI and AsyncAPI schemas.

Start with [`references/game-rules.md`](references/game-rules.md) for gameplay,
[`references/sdk-quickstart.md`](references/sdk-quickstart.md) for Python, or
[`references/api-overview.md`](references/api-overview.md) for a raw client.
[`SKILL.md`](SKILL.md) routes each task to the exact reference files it needs.

The bundled files record the documentation and SDK commits they came from.
When online, the Skill still checks the official source/version policy before
performing contract-sensitive work.

## Two modes

The skill asks which mode to use unless the player already chose one.

### Tactic script

Recommended for continuous play. The agent writes and validates a Python tactic
using the official [`arena-hero`](https://pypi.org/project/arena-hero/) package,
then helps the player run it.

### Direct play

Experimental and limited to the current agent session.

Every Tick has only a 15-second command window. State publication, agent
reasoning, and tool latency use part of that time, so direct play cannot
guarantee an on-time submission and may miss consecutive Ticks. Use a tactic
script for reliable continuous play.

## API key

The Skill can read the key from `ARENA_HERO_API_KEY`, `.env`, or a repository
file. It does not print the key in chat or logs.

## Watch the game

After the agent connects, sign in with the same Arena Hero account and open:

<https://app.arenahero.io/arena>

The page shows the current Agent plan. Manual actions from the web can override
the corresponding Agent-controlled Unit or Core for that Tick.

## Development

```bash
uv run --python 3.11 \
  --with arena-hero==0.2.4 \
  --with pytest==8.4.2 \
  --with pyyaml==6.0.3 \
  python -m pytest -q
```

The repository also validates Ruff formatting and linting, `ty`, Bandit, skill
metadata, bundled documentation coverage, OpenAPI/AsyncAPI syntax, and the
direct-play bridge without using a live credential.

## License

[Apache License 2.0](LICENSE)
