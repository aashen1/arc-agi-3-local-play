import json
import os
from datetime import datetime, timezone

from arcengine import GameAction, FrameDataRaw

from human_player.config import RECORDINGS_DIR


class RecordingManager:
    def __init__(self):
        self.current_session_id = None
        self.current_file = None
        self.current_game_id = None
        self._step_count = 0

    def start_session(self, game_id: str) -> str:
        os.makedirs(RECORDINGS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session_id = f"{game_id}_{timestamp}"
        self.current_game_id = game_id
        self._step_count = 0

        filename = f"{self.current_session_id}.jsonl"
        filepath = os.path.join(RECORDINGS_DIR, filename)
        self.current_file = open(filepath, "a", encoding="utf-8")

        return self.current_session_id

    def record_step(self, action: GameAction, data: dict | None,
                    obs: FrameDataRaw | None, step_count: int, elapsed_ms: int):
        if self.current_file is None:
            return

        self._step_count += 1
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step_count,
            "action": action.name,
            "action_data": data or {},
            "frame_state": obs.state.name if obs else "UNKNOWN",
            "levels_completed": obs.levels_completed if obs else 0,
            "score": getattr(obs, 'score', 0) or 0,
            "elapsed_ms": elapsed_ms,
            "player_type": "human",
            "session_id": self.current_session_id,
        }

        self.current_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.current_file.flush()

    def end_session(self):
        if self.current_file:
            self.current_file.close()
            self.current_file = None
        self.current_session_id = None
        self.current_game_id = None

    def list_recordings(self, game_id: str = None) -> list[dict]:
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
            results.append({
                "filename": filename,
                "filepath": filepath,
                "game_id": parts[0] if parts else "unknown",
                "session_id": filename.replace(".jsonl", ""),
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return results

    def load_recording(self, filepath: str) -> list[dict]:
        records = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def find_best_recording(self, game_id: str) -> str | None:
        recordings = self.list_recordings(game_id)
        if not recordings:
            return None
        winning = []
        for rec in recordings:
            records = self.load_recording(rec["filepath"])
            max_lc = max((r.get("levels_completed", 0) for r in records), default=0)
            if max_lc > 0:
                winning.append((rec["filepath"], max_lc))
        if not winning:
            return None
        winning.sort(key=lambda x: x[1], reverse=True)
        return winning[0][0]

    def extract_winning_sequences(self, game_id: str) -> dict[int, list[dict]]:
        filepath = self.find_best_recording(game_id)
        if filepath is None:
            return {}
        records = self.load_recording(filepath)
        return self._parse_level_actions(records)

    def _parse_level_actions(self, records: list[dict]) -> dict[int, list[dict]]:
        result: dict[int, list[dict]] = {}
        current_level = 0
        current_actions: list[dict] = []

        for rec in records:
            action_name = rec.get("action", "")
            if action_name == "RESET":
                current_actions = []
                continue

            lc = rec.get("levels_completed", 0)
            action_data = rec.get("action_data", {})

            current_actions.append({
                "action": action_name,
                "action_data": action_data,
            })

            if lc > current_level:
                result[current_level] = current_actions[:]
                current_level = lc
                current_actions = []

        return result
