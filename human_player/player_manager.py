import json
import os

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
