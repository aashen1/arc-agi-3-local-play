# ARC-AGI-3 Human Player Console

> TL;DR: Install [`pixi` ](https://pixi.prefix.dev/latest/installation/), start a terminal at this folder, then `pixi run game` to start.

A local desktop client built with [Pygame-ce](https://pyga.me/) for playing [ARC-AGI-3](https://arcprize.org/) games.

**(Note: The core game engine and logic come from the official `arc-agi` library. This repo is just a simple `pygame-ce` based wrapper that adds UI, console interface, and some small feat like local save. I did not design the games themselves.)**

The official ARC Prize website already offers a web demo with leaderboards for top players tracking minimal step counts, but If you want to play these puzzles as a local game, there seems to be no convenient ways to do it directly. So I built this Pygame-based wrapper that packages the `arc-agi` SDK into something closer to a real mini-game.

It also runs entirely offline after you've start for once and cached all games. No need for internet connection besides downloading game updates.

## What It Does

- Browse and select specific ARC-AGI-3 levels and sub-levels from a simple menu
- Play with keyboard + mouse, interact with game maps and menu buttons (support all 7 standard actions)
- Switch between multiple player profiles, each with their own progress and stats
- Pick any sub-level you've reached before — no need to always replay from the sublevel 1
- Record gameplay in lightweight JSONL and ARC-AGI-3 official format

## Features

- Grid/list game browser with progress bars and completion indicators
- Frame animation playback, behave 70% similar to the official web game
- Per-game progress tracking
- Multi-player profiles with isolated data
- Dual recording system:
  - Lightweight JSONL — step-by-step action log
  - Official format — compatible with ARC-AGI-3 recording schema

## Quick Start

### Prerequisites

- [pixi](https://pixi.sh/) package manager
- Python 3.14+ (managed by pixi)

### Install & Run

```bash
git clone https://github.com/aashen1/arc-agi-3-human-player.git
cd arc-agi-3-human-player

pixi install
pixi run game
```

No API key needed if you care nothing about **AI AGENT** scoreboard — runs in offline mode by default.

### Agent Mode (In Future Plans, not tested yet)

To run in online/agent mode with scorecard tracking:

```bash
cp .env.example .env
# Edit .env and add your ARC_API_KEY
```

Then set the player mode to `agent` in `data/user_config.json`.

## Controls

### WASD Scheme (default)

| Key   | Action     |
|-------|------------|
| W     | Up         |
| S     | Down       |
| A     | Left       |
| D     | Right      |
| Space | Interact   |
| Z     | Undo       |
| R     | Reset      |
| Mouse | Click grid |
| Esc   | Menu       |

### Arrow Scheme

| Key   | Action     |
|-------|------------|
| ↑     | Up         |
| ↓     | Down       |
| ←     | Left       |
| →     | Right      |
| F     | Interact   |
| Z     | Undo       |
| R     | Reset      |
| Mouse | Click grid |
| Esc   | Menu       |

Switch schemes in **Settings** (press `S` on the main menu).

## Project Structure

```plain
human_player/
├── __main__.py           # Entry point, main loop, state machine
├── config.py             # Window, palette, keymaps, paths
├── game_manager.py       # Arcade/Environment interaction wrapper
├── renderer.py           # Pygame grid rendering + HUD
├── menu.py               # Main menu, settings, stats, level select
├── level_manager.py      # Level progress JSON persistence
├── stats_manager.py      # Per-game attempt/win statistics
├── player_manager.py     # Multi-player profile management
├── recording.py          # Lightweight JSONL recording
├── official_recording.py # ARC-AGI-3 official format recording
├── mode.py               # Human/Agent mode, operation mode
└── agent_base.py         # Abstract base class for AI agents
```

Runtime data is stored in `data/` (auto-created, git-ignored):

```plain
data/
├── user_config.json
└── players/
    └── <player_name>/
        ├── progress.json
        ├── records/
        └── recordings/
            └── <game_id>/
                ├── index.json
                └── *.recording.jsonl
```

## Recording Formats

### Lightweight Recording

One JSON line per step:

```json
{
  "timestamp": "2025-01-15T10:30:00+00:00",
  "step": 5,
  "action": "ACTION1",
  "action_data": {},
  "frame_state": "NOT_FINISHED",
  "levels_completed": 0,
  "elapsed_ms": 3200,
  "player_type": "human"
}
```

### Official Recording

Compatible with ARC-AGI-3 submission format. Includes frame data, action IDs, available actions, and a session summary with `won`, `played`, `total_actions`, `actions_by_level`, and `resets`.

## Extending: Custom Agents

The `AgentBase` class provides a minimal interface for building AI agents:

```python
from human_player.agent_base import AgentBase
from arcengine import GameAction

class MyAgent(AgentBase):
    agent_type = AgentType.CUSTOM

    def is_done(self, frames, latest_frame) -> bool:
        return False

    def choose_action(self, frames, latest_frame) -> GameAction:
        return GameAction.ACTION1

    def get_reasoning(self) -> dict | str | None:
        return "Chose ACTION1 because..."
```

## Tech Stack

- [arc-agi](https://pypi.org/project/arc-agi/) — Official ARC-AGI-3 Python toolkit
- [pygame-ce](https://pyga.me/) — Community Edition of Pygame
- [pixi](https://pixi.sh/) — Package manager
- [rich](https://rich.readthedocs.io/) — Terminal formatting (for terminal mode only)

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

- [ARC Prize Foundation](https://arcprize.org/) for the ARC-AGI-3 toolkit
