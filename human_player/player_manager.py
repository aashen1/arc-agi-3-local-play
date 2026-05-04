import json
import os
import shutil

from human_player.config import PLAYERS_DIR, USER_CONFIG_FILE, _load_user_config, _save_user_config


class PlayerManager:
    def __init__(self):
        self._current_player = _load_user_config().get("current_player", "default")
        self._ensure_player_dir(self._current_player)

    def get_current_player(self) -> str:
        return self._current_player

    def set_player(self, name: str) -> None:
        name = name.strip()
        if not name:
            return
        self._current_player = name
        self._ensure_player_dir(name)
        cfg = _load_user_config()
        cfg["current_player"] = name
        _save_user_config(cfg)

    def list_players(self) -> list[str]:
        if not os.path.exists(PLAYERS_DIR):
            return ["default"]
        players = [
            d for d in os.listdir(PLAYERS_DIR)
            if os.path.isdir(os.path.join(PLAYERS_DIR, d))
        ]
        if "default" not in players:
            players.insert(0, "default")
        return sorted(players)

    def get_player_data_dir(self, name: str = None) -> str:
        name = name or self._current_player
        path = os.path.join(PLAYERS_DIR, name)
        os.makedirs(path, exist_ok=True)
        return path

    def get_recordings_dir(self, game_id: str, name: str = None) -> str:
        base = self.get_player_data_dir(name)
        path = os.path.join(base, "recordings", game_id)
        os.makedirs(path, exist_ok=True)
        return path

    def get_records_dir(self, name: str = None) -> str:
        base = self.get_player_data_dir(name)
        path = os.path.join(base, "records")
        os.makedirs(path, exist_ok=True)
        return path

    def get_progress_file(self, name: str = None) -> str:
        return os.path.join(self.get_player_data_dir(name), "progress.json")

    def _ensure_player_dir(self, name: str) -> None:
        path = os.path.join(PLAYERS_DIR, name)
        os.makedirs(path, exist_ok=True)

    def get_player_metadata(self, name: str = None) -> dict:
        name = name or self._current_player
        progress_file = self.get_progress_file(name)
        total_levels_completed = 0
        total_games_played = 0
        total_time_ms = 0
        last_played = None

        if os.path.exists(progress_file):
            try:
                with open(progress_file, "r", encoding="utf-8") as f:
                    progress = json.load(f)
            except (json.JSONDecodeError, OSError):
                progress = {}

            for game_id, game in progress.get("games", {}).items():
                levels = game.get("levels", {})
                game_completed = sum(1 for lv in levels.values() if lv.get("completed"))
                if game_completed > 0 or game.get("total_levels", 0) > 0:
                    total_games_played += 1
                total_levels_completed += game_completed
                for lv in levels.values():
                    if lv.get("completed"):
                        total_time_ms += lv.get("best_time_ms", 0)
                        ts = lv.get("completed_at")
                        if ts and (last_played is None or ts > last_played):
                            last_played = ts

        records_dir = os.path.join(PLAYERS_DIR, name, "records") if name else os.path.join(PLAYERS_DIR, self._current_player, "records")
        if os.path.exists(records_dir):
            for fname in os.listdir(records_dir):
                if not fname.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(records_dir, fname), "r", encoding="utf-8") as f:
                        records = json.load(f)
                    if isinstance(records, list):
                        for r in records:
                            total_time_ms += r.get("time_ms", 0)
                            ts = r.get("timestamp")
                            if ts and (last_played is None or ts > last_played):
                                last_played = ts
                except (json.JSONDecodeError, OSError):
                    pass

        return {
            "total_levels_completed": total_levels_completed,
            "total_games_played": total_games_played,
            "total_time_ms": total_time_ms,
            "last_played": last_played,
        }

    def delete_player(self, name: str) -> bool:
        if name == self._current_player:
            return False
        player_dir = os.path.join(PLAYERS_DIR, name)
        if not os.path.isdir(player_dir):
            return False
        if not os.path.abspath(player_dir).startswith(os.path.abspath(PLAYERS_DIR)):
            return False
        shutil.rmtree(player_dir)
        return True
