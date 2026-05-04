import json
import os
import uuid
from datetime import UTC, datetime

from arcengine import GameAction

from human_player.mode import PlayerMode, get_agent_type, get_player_mode
from human_player.player_manager import PlayerManager

ACTION_ID_MAP = {
    GameAction.RESET: 0,
    GameAction.ACTION1: 1,
    GameAction.ACTION2: 2,
    GameAction.ACTION3: 3,
    GameAction.ACTION4: 4,
    GameAction.ACTION5: 5,
    GameAction.ACTION6: 6,
    GameAction.ACTION7: 7,
}


class OfficialRecordingManager:
    """Produce ARC-AGI-3 official-format JSONL recordings.

    Each session creates a ``<game_id>.<guid>.recording.jsonl`` file and
    updates an ``index.json`` that tracks all sessions for the game. The
    recording format matches the ARC-AGI-3 specification so files can be
    uploaded directly to arcprize.org.
    """

    def __init__(self, player_manager: PlayerManager):
        self._pm = player_manager
        self._guid = None
        self._file = None
        self._game_id = None
        self._win_levels = 0
        self._step_count = 0
        self._levels_at_start = 0
        self._prev_levels_completed = 0
        self._current_level_actions = 0
        self._actions_by_level = []
        self._reset_count = 0
        self._start_time = None
        self._is_full_reset = False

    @property
    def is_recording(self) -> bool:
        """Return True if a recording session is currently active."""
        return self._file is not None

    def start_session(self, game_id: str, win_levels: int, levels_at_start: int = 0) -> str:
        """Begin a new recording session and return its GUID.

        Args:
            game_id: The 4-character game identifier.
            win_levels: Total number of win levels in this game.
            levels_at_start: Levels already completed when the session starts.

        Returns:
            The UUID string assigned to this session.
        """
        self._guid = str(uuid.uuid4())
        self._game_id = game_id
        self._win_levels = win_levels
        self._step_count = 0
        self._levels_at_start = levels_at_start
        self._prev_levels_completed = levels_at_start
        self._current_level_actions = 0
        self._actions_by_level = []
        self._reset_count = 0
        self._is_full_reset = levels_at_start == 0
        self._start_time = datetime.now(UTC)

        recordings_dir = self._pm.get_recordings_dir(game_id)
        filename = f"{game_id}.{self._guid}.recording.jsonl"
        filepath = os.path.join(recordings_dir, filename)
        try:
            self._file = open(filepath, "w", encoding="utf-8")
        except OSError as e:
            print(f"[OfficialRecording] Failed to open recording file: {e}")
            self._file = None

        return self._guid

    def record_step(
        self,
        action: GameAction,
        action_data: dict | None,
        obs,
        available_actions: list,
        reasoning: dict | str | None = None,
    ) -> None:
        """Append one step record to the current session file.

        Args:
            action: The GameAction that was executed.
            action_data: Optional payload (e.g. x/y for ACTION6).
            obs: The frame observation returned after the action.
            available_actions: List of GameAction values the player can use next.
            reasoning: Optional agent reasoning text (only recorded in AGENT mode).
        """
        if self._file is None:
            return

        self._step_count += 1
        self._current_level_actions += 1

        action_id = ACTION_ID_MAP.get(action, 0)

        action_input_data = {"game_id": self._game_id}
        if action_data:
            action_input_data.update(action_data)

        action_input = {
            "id": action_id,
            "data": action_input_data,
            "reasoning": reasoning if get_player_mode() == PlayerMode.AGENT else None,
        }

        frame = self._extract_frame(obs)
        state = obs.state.name if obs and hasattr(obs, "state") else "UNKNOWN"
        levels_completed = getattr(obs, "levels_completed", self._prev_levels_completed) or 0
        win_levels = getattr(obs, "win_levels", self._win_levels) or self._win_levels

        if levels_completed > self._prev_levels_completed:
            for lvl in range(self._prev_levels_completed, levels_completed):
                self._actions_by_level.append([lvl + 1, self._step_count])
            self._prev_levels_completed = levels_completed
            self._current_level_actions = 0

        if action == GameAction.RESET:
            self._reset_count += 1
            if levels_completed == 0 or self._is_full_reset:
                self._is_full_reset = True
            else:
                self._is_full_reset = False
        else:
            self._is_full_reset = False

        available_ids = []
        if available_actions:
            for a in available_actions:
                aid = ACTION_ID_MAP.get(a)
                if aid is not None:
                    available_ids.append(aid)

        data = {
            "game_id": self._game_id,
            "frame": frame,
            "state": state,
            "levels_completed": levels_completed,
            "win_levels": win_levels,
            "action_input": action_input,
            "guid": self._guid,
            "full_reset": self._is_full_reset,
            "available_actions": available_ids,
        }

        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
        }

        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._file.flush()

    def end_session(self, final_state: str) -> None:
        """Close the session, write a summary record, and update the index.

        Args:
            final_state: The game's terminal state, e.g. "WIN" or "GAME_OVER".
        """
        if self._file is None:
            return

        won = 1 if final_state == "WIN" else 0
        levels_completed = self._prev_levels_completed

        if self._current_level_actions > 0 and final_state != "WIN":
            current_lvl = self._prev_levels_completed + 1
            self._actions_by_level.append([current_lvl, self._step_count])

        summary = {
            "won": won,
            "played": 1,
            "total_actions": self._step_count,
            "levels_completed": levels_completed,
            "cards": {
                self._game_id: {
                    "game_id": self._game_id,
                    "total_plays": 1,
                    "guids": [self._guid],
                    "levels_completed": [levels_completed],
                    "states": [final_state],
                    "actions": [self._step_count],
                    "actions_by_level": [self._actions_by_level],
                    "resets": [self._reset_count],
                    "total_actions": self._step_count,
                }
            },
        }

        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "data": summary,
        }

        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._file.flush()
        self._file.close()
        self._file = None

        self._update_index(final_state)

        self._guid = None
        self._game_id = None

    def get_session_index(self, game_id: str) -> dict:
        """Load or create the session index for a game.

        Args:
            game_id: The 4-character game identifier.

        Returns:
            Dict with keys: game_id, player, first_win_index, sessions.
        """
        recordings_dir = self._pm.get_recordings_dir(game_id)
        index_path = os.path.join(recordings_dir, "index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[OfficialRecording] Failed to load index: {e}")
        return {
            "game_id": game_id,
            "player": self._pm.get_current_player(),
            "first_win_index": None,
            "sessions": [],
        }

    def list_sessions(self, game_id: str = None) -> list[dict]:
        """Return session entries from the index, optionally filtered by game.

        Args:
            game_id: If given, only return sessions for this game.

        Returns:
            List of session entry dicts from the index.
        """
        if game_id:
            index = self.get_session_index(game_id)
            return index.get("sessions", [])

        results = []
        base_dir = os.path.join(self._pm.get_player_data_dir(), "recordings")
        if not os.path.exists(base_dir):
            return results
        for gid in os.listdir(base_dir):
            gid_dir = os.path.join(base_dir, gid)
            if os.path.isdir(gid_dir):
                index = self.get_session_index(gid)
                results.extend(index.get("sessions", []))
        return results

    def _extract_frame(self, obs) -> list:
        if obs is None:
            return []
        frame = getattr(obs, "frame", None)
        if frame is None:
            return []
        return self._to_json_serializable(frame)

    def _to_json_serializable(self, obj):
        import numpy as np

        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, list):
            return [self._to_json_serializable(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._to_json_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        return str(obj)

    def _update_index(self, final_state: str) -> None:
        game_id = self._game_id
        if game_id is None:
            return

        recordings_dir = self._pm.get_recordings_dir(game_id)
        index_path = os.path.join(recordings_dir, "index.json")

        index = self.get_session_index(game_id)

        session_entry = {
            "guid": self._guid,
            "filename": f"{game_id}.{self._guid}.recording.jsonl",
            "started_at": self._start_time.isoformat() if self._start_time else None,
            "ended_at": datetime.now(UTC).isoformat(),
            "total_actions": self._step_count,
            "levels_completed": self._prev_levels_completed,
            "final_state": final_state,
            "phase": "learning",
            "player_mode": get_player_mode().value,
        }
        if get_player_mode() == PlayerMode.AGENT:
            agent_type = get_agent_type()
            session_entry["agent_type"] = agent_type.value if agent_type else "unknown"

        sessions = index.get("sessions", [])

        current_index = len(sessions)

        if final_state == "WIN" and index.get("first_win_index") is None:
            index["first_win_index"] = current_index

        first_win = index.get("first_win_index")
        if first_win is not None and current_index > first_win:
            session_entry["phase"] = "practice"

        sessions.append(session_entry)
        index["sessions"] = sessions

        try:
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"[OfficialRecording] Failed to save index: {e}")
