import json
import os
from datetime import datetime, timezone

from human_player.config import RECORDS_DIR


class StatsManager:
    def __init__(self):
        self._cache = {}

    def record_attempt(self, game_id: str, level_index: int, steps: int,
                       time_ms: int, result: str, session_id: str):
        os.makedirs(RECORDS_DIR, exist_ok=True)
        filepath = os.path.join(RECORDS_DIR, f"{game_id}.json")

        records = self._load_records(filepath)

        records.append({
            "level_index": level_index,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "steps": steps,
            "time_ms": time_ms,
            "result": result,
        })

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def get_best_record(self, game_id: str, level_index: int) -> dict | None:
        records = self._get_all_records(game_id)
        level_records = [r for r in records if r.get("level_index") == level_index and r.get("result") == "WIN"]
        if not level_records:
            return None
        return min(level_records, key=lambda r: r.get("steps", float("inf")))

    def get_all_records(self, game_id: str) -> list[dict]:
        return self._get_all_records(game_id)

    def get_level_stats(self, game_id: str, level_index: int) -> dict:
        records = self._get_all_records(game_id)
        level_records = [r for r in records if r.get("level_index") == level_index]
        wins = [r for r in level_records if r.get("result") == "WIN"]
        return {
            "attempts": len(level_records),
            "wins": len(wins),
            "best_steps": min((r["steps"] for r in wins), default=None),
            "best_time_ms": min((r["time_ms"] for r in wins), default=None),
        }

    def get_game_summary(self, game_id: str) -> dict:
        records = self._get_all_records(game_id)
        wins = [r for r in records if r.get("result") == "WIN"]
        levels_won = set(r.get("level_index") for r in wins)
        return {
            "total_attempts": len(records),
            "total_wins": len(wins),
            "levels_completed": len(levels_won),
            "best_steps": min((r["steps"] for r in wins), default=None),
        }

    def _get_all_records(self, game_id: str) -> list[dict]:
        if game_id in self._cache:
            return self._cache[game_id]
        filepath = os.path.join(RECORDS_DIR, f"{game_id}.json")
        records = self._load_records(filepath)
        self._cache[game_id] = records
        return records

    def _load_records(self, filepath: str) -> list[dict]:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return data.get("records", [])
        return []
