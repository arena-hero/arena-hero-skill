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
[doc.arenahero.io/agent/agent-skill](https://doc.arenahero.io/agent/agent-skill).

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

## API key safety

The skill accepts an Arena Hero API key only through a hidden terminal or
host-provided secret prompt. It must never enter chat, source code, environment
variables, command-line arguments, logs, patches, or repository files.

If secure hidden input is unavailable, direct play stops and offers tactic
script mode instead.

## Watch the game

After the agent connects, sign in with the same Arena Hero account and open:

<https://app.arenahero.io/arena>

The page shows the current Agent plan. Manual actions from the web can override
the corresponding Agent-controlled Unit or Core for that Tick.

## Development

```bash
uv run --python 3.11 \
  --with arena-hero==0.1.0 \
  --with pytest==8.4.2 \
  --with pyyaml==6.0.3 \
  python -m pytest -q
```

The repository also validates Ruff formatting and linting, `ty`, Bandit, skill
metadata, and the direct-play bridge without using a live credential.

## License

[MIT](LICENSE)
