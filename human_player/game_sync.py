import contextlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import arc_agi
from arc_agi import OperationMode

from human_player.config import SYNC_MODE_AUTO, SYNC_MODE_CONSERVATIVE, get_sync_mode

ENVIRONMENTS_DIR = os.getenv("ENVIRONMENTS_DIR", "environment_files")


@dataclass
class SyncResult:
    """Outcome summary of a game synchronization run."""

    total: int = 0
    downloaded: int = 0
    skipped: int = 0
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True if no games failed to download."""
        return len(self.failed) == 0


def get_local_game_ids() -> set[str]:
    """Scan the local environments directory for already-downloaded game IDs."""
    env_dir = Path(ENVIRONMENTS_DIR)
    if not env_dir.exists():
        return set()
    ids = set()
    for mf in env_dir.rglob("metadata.json"):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
            gid = data.get("game_id", "")
            base = gid.split("-", 1)[0] if gid else ""
            if base:
                ids.add(base)
        except Exception:
            continue
    return ids


def get_local_game_count() -> int:
    """Return the number of locally available games."""
    return len(get_local_game_ids())


def needs_sync() -> bool:
    """Check whether a sync should be performed based on config and local state."""
    mode = get_sync_mode()
    if mode == SYNC_MODE_AUTO:
        return True
    return get_local_game_count() == 0


def should_show_sync_button() -> bool:
    """Check whether the sync button should be shown in the menu."""
    mode = get_sync_mode()
    return mode == SYNC_MODE_CONSERVATIVE


def sync_games(progress_callback=None) -> SyncResult:
    """Download all missing game environments from the ARC-AGI-3 API.

    Iterates over every available environment; games already present locally
    are skipped. Each new game is instantiated once (which triggers the SDK
    to cache its data) and then closed.

    Args:
        progress_callback: Optional callable ``callback(current, total, game_id, status)``
            invoked after each game is processed.

    Returns:
        A SyncResult summarizing how many games were downloaded, skipped, or failed.
    """
    result = SyncResult()

    arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)

    try:
        all_envs = arc.get_environments()
        result.total = len(all_envs)

        local_ids = get_local_game_ids()

        for i, env_info in enumerate(all_envs):
            base_id = env_info.game_id.split("-", 1)[0]

            if base_id in local_ids:
                result.skipped += 1
                if progress_callback:
                    progress_callback(i + 1, result.total, base_id, "skipped")
                continue

            try:
                wrapper = arc.make(
                    env_info.game_id,
                    save_recording=False,
                    include_frame_data=False,
                )
                if wrapper is not None:
                    with contextlib.suppress(Exception):
                        wrapper.close()
                    result.downloaded += 1
                    if progress_callback:
                        progress_callback(i + 1, result.total, base_id, "downloaded")
                else:
                    result.failed.append(base_id)
                    if progress_callback:
                        progress_callback(i + 1, result.total, base_id, "failed")
            except Exception as e:
                result.failed.append(base_id)
                if progress_callback:
                    progress_callback(i + 1, result.total, base_id, f"error: {e}")

        with contextlib.suppress(Exception):
            arc.close_scorecard()

    finally:
        with contextlib.suppress(Exception):
            del arc

    return result
