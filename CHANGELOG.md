# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-06

### Added

- Interactive player console built with Pygame for ARC-AGI-3 gameplay
- Full game environment lifecycle management (create, play, reset, step)
- Multi-player support with isolated data directories and per-player statistics
- Level progress tracking with JSON-based save/load persistence
- Comprehensive statistics tracking (scores, move counts, completion times)
- Lightweight action recording in JSONL format for replay and analysis
- Official recording format export for competition submissions
- Configurable key bindings with multiple preset schemes
- Pygame-based menu system for player selection and game navigation
- HUD overlay displaying game state, controls, and real-time stats
- Pre-commit hooks with ruff for linting and code formatting
- GitHub Actions CI pipeline for automated testing
- Full test coverage for core modules (pytest)
- Project documentation covering usage, architecture, and API reference

### Technical

- Modular architecture with separated concerns (renderer, game manager, level manager, etc.)
- Pixi-based Python environment management
- Support for Python 3.12+
- Cross-platform support (Windows, Linux, macOS)

[0.1.0]: https://github.com/aashen1/arc-agi-3-human-player/releases/tag/v0.1.0
