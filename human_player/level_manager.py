import json
import os
from datetime import datetime, timezone

from human_player.config import PROGRESS_FILE, DATA_DIR


class LevelManager:
    """Manage level completion progress for each game.

    Progress is persisted as a single JSON file mapping game IDs to their
    level completion data (best steps, best time, attempt count, etc.).
    """

    def __init__(self, progress_file: str = None):
        self._progress_file = progress_file or PROGRESS_FILE
        self.progress = self._load_progress()

    def set_progress_file(self, progress_file: str):
        """Switch to a different progress file and reload."""
        self._progress_file = progress_file
        self.progress = self._load_progress()

    def get_game_progress(self, game_id: str) -> dict:
        """Return the progress dict for a game, or a default empty one."""
        games = self.progress.get("games", {})
        if game_id not in games:
            return {"game_id": game_id, "levels": {}, "total_levels": 0}
        return games[game_id]

    def update_level_status(self, game_id: str, level_index: int,
                            steps: int, time_ms: int):
        """Record a level completion, keeping the best steps and time.

        Args:
            game_id: The 4-character game identifier.
            level_index: Zero-based level index.
            steps: Number of actions taken to complete the level.
            time_ms: Elapsed time in milliseconds.
        """
        if "games" not in self.progress:
            self.progress["games"] = {}

        if game_id not in self.progress["games"]:
            self.progress["games"][game_id] = {
                "levels": {},
                "total_levels": 0,
            }

        game = self.progress["games"][game_id]
        level_key = str(level_index)

        existing = game["levels"].get(level_key, {})
        best_steps = existing.get("best_steps")
        best_time_ms = existing.get("best_time_ms")

        if best_steps is None or steps < best_steps:
            best_steps = steps
        if best_time_ms is None or time_ms < best_time_ms:
            best_time_ms = time_ms

        game["levels"][level_key] = {
            "completed": True,
            "best_steps": best_steps,
            "best_time_ms": best_time_ms,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "attempts": existing.get("attempts", 0) + 1,
        }
        self._save_progress()

    def update_total_levels(self, game_id: str, total: int):
        """Set the total number of levels for a game."""
        if "games" not in self.progress:
            self.progress["games"] = {}
        if game_id not in self.progress["games"]:
            self.progress["games"][game_id] = {"levels": {}, "total_levels": 0}
        self.progress["games"][game_id]["total_levels"] = total
        self._save_progress()

    def get_completed_count(self, game_id: str) -> int:
        """Return how many levels are marked as completed for a game."""
        game = self.get_game_progress(game_id)
        return sum(1 for lv in game.get("levels", {}).values() if lv.get("completed"))

    def get_next_uncompleted_level(self, game_id: str) -> int | None:
        """Return the next level index to play, or None if all completed.

        Returns 0 if no levels have been completed yet.
        """
        game = self.get_game_progress(game_id)
        levels = game.get("levels", {})
        if not levels:
            return 0
        completed_indices = sorted(
            int(k) for k, v in levels.items() if v.get("completed")
        )
        if not completed_indices:
            return 0
        next_level = completed_indices[-1] + 1
        total = game.get("total_levels", 0)
        if total > 0 and next_level >= total:
            return None
        return next_level

    def get_total_levels(self, game_id: str) -> int:
        """Return the total number of levels for a game."""
        game = self.get_game_progress(game_id)
        return game.get("total_levels", 0)

    def get_best_steps(self, game_id: str, level_index: int) -> int | None:
        """Return the best step count for a level, or None if not completed."""
        game = self.get_game_progress(game_id)
        level = game.get("levels", {}).get(str(level_index), {})
        return level.get("best_steps")

    def get_best_time_ms(self, game_id: str, level_index: int) -> int | None:
        """Return the best time (ms) for a level, or None if not completed."""
        game = self.get_game_progress(game_id)
        level = game.get("levels", {}).get(str(level_index), {})
        return level.get("best_time_ms")

    def is_fully_completed(self, game_id: str) -> bool:
        """Check whether all levels of a game are completed."""
        total = self.get_total_levels(game_id)
        if total <= 0:
            return False
        return self.get_completed_count(game_id) >= total

    def get_level_info(self, game_id: str, level_index: int) -> dict:
        """Return completion info for a single level.

        Returns:
            Dict with keys: completed, best_steps, best_time_ms, attempts.
        """
        game = self.get_game_progress(game_id)
        level = game.get("levels", {}).get(str(level_index), {})
        return {
            "completed": level.get("completed", False),
            "best_steps": level.get("best_steps"),
            "best_time_ms": level.get("best_time_ms"),
            "attempts": level.get("attempts", 0),
        }

    def get_current_level(self, game_id: str) -> int | None:
        """Return the saved current level index, or None if unset."""
        game = self.get_game_progress(game_id)
        return game.get("current_level")

    def set_current_level(self, game_id: str, level_index: int):
        """Persist the current level index for a game."""
        if "games" not in self.progress:
            self.progress["games"] = {}
        if game_id not in self.progress["games"]:
            self.progress["games"][game_id] = {"levels": {}, "total_levels": 0}
        self.progress["games"][game_id]["current_level"] = level_index
        self._save_progress()

    def get_last_played_game_id(self) -> str | None:
        """Return the game_id with the most recent completion timestamp."""
        latest_time = None
        latest_game = None
        for game_id, game in self.progress.get("games", {}).items():
            for level_data in game.get("levels", {}).values():
                ts = level_data.get("completed_at")
                if ts and (latest_time is None or ts > latest_time):
                    latest_time = ts
                    latest_game = game_id
        return latest_game

    def _load_progress(self) -> dict:
        if os.path.exists(self._progress_file):
            try:
                with open(self._progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[LevelManager] Failed to load progress: {e}")
        return {"version": "1.0", "games": {}}

    def _save_progress(self):
        try:
            os.makedirs(os.path.dirname(self._progress_file), exist_ok=True)
            self.progress["last_updated"] = datetime.now(timezone.utc).isoformat()
            with open(self._progress_file, "w", encoding="utf-8") as f:
                json.dump(self.progress, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"[LevelManager] Failed to save progress: {e}")
