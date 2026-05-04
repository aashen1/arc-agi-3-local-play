import json
import os
from datetime import UTC, datetime

from arcengine import FrameDataRaw, GameAction

from human_player.config import RECORDINGS_DIR
from human_player.mode import PlayerMode, get_agent_type, get_player_mode


class RecordingManager:
    """Lightweight JSONL-based gameplay recorder.

    Each session creates one ``.jsonl`` file where every line is a JSON
    object describing a single step (action, frame state, timing, etc.).
    """

    def __init__(self):
        self.current_session_id = None
        self.current_file = None
        self.current_game_id = None
        self._step_count = 0

    def start_session(self, game_id: str) -> str:
        """Open a new recording session and return its ID.

        Args:
            game_id: The 4-character game identifier.

        Returns:
            A session ID string in the form ``<game_id>_<timestamp>``.
        """
        os.makedirs(RECORDINGS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session_id = f"{game_id}_{timestamp}"
        self.current_game_id = game_id
        self._step_count = 0

        filename = f"{self.current_session_id}.jsonl"
        filepath = os.path.join(RECORDINGS_DIR, filename)
        try:
            self.current_file = open(filepath, "a", encoding="utf-8")
        except OSError as e:
            print(f"[RecordingManager] Failed to open recording file: {e}")
            self.current_file = None

        return self.current_session_id

    def record_step(
        self,
        action: GameAction,
        data: dict | None,
        obs: FrameDataRaw | None,
        step_count: int,
        elapsed_ms: int,
    ):
        """Write one step record to the current session file.

        Args:
            action: The GameAction that was executed.
            data: Optional action payload (e.g. x/y coordinates for ACTION6).
            obs: The frame observation returned after the action, or None.
            step_count: Current step number within the level.
            elapsed_ms: Milliseconds elapsed since the level started.
        """
        if self.current_file is None:
            return

        self._step_count += 1
        player_mode = get_player_mode()
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "step": step_count,
            "action": action.name,
            "action_data": data or {},
            "frame_state": obs.state.name if obs else "UNKNOWN",
            "levels_completed": obs.levels_completed if obs else 0,
            "score": getattr(obs, "score", 0) or 0,
            "elapsed_ms": elapsed_ms,
            "player_type": player_mode.value,
            "session_id": self.current_session_id,
        }
        if player_mode == PlayerMode.AGENT:
            agent_type = get_agent_type()
            record["agent_type"] = agent_type.value if agent_type else "unknown"

        self.current_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.current_file.flush()

    def end_session(self):
        """Close the current session file and reset session state."""
        if self.current_file:
            self.current_file.close()
            self.current_file = None
        self.current_session_id = None
        self.current_game_id = None

    def list_recordings(self, game_id: str = None) -> list[dict]:
        """List available recording files, newest first.

        Args:
            game_id: If given, only list recordings for this game.

        Returns:
            List of dicts with filename, filepath, game_id, session_id,
            size_bytes, and modified timestamp.
        """
        if not os.path.exists(RECORDINGS_DIR):
            return []

        results = []
        for filename in sorted(os.listdir(RECORDINGS_DIR), reverse=True):
            if not filename.endswith(".jsonl"):
                continue
            if game_id and not filename.startswith(game_id):
                continue

            filepath = os.path.join(RECORDINGS_DIR, filename)
            stat = os.stat(filepath)
            parts = filename.replace(".jsonl", "").split("_", 1)
            results.append(
                {
                    "filename": filename,
                    "filepath": filepath,
                    "game_id": parts[0] if parts else "unknown",
                    "session_id": filename.replace(".jsonl", ""),
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
        return results

    def load_recording(self, filepath: str) -> list[dict]:
        """Parse a JSONL recording file into a list of step dicts.

        Args:
            filepath: Absolute path to the ``.jsonl`` file.

        Returns:
            List of parsed JSON objects, one per step.
        """
        records = []
        try:
            with open(filepath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[RecordingManager] Failed to load recording: {e}")
        return records
