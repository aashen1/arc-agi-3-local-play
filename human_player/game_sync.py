import json
import os
from pathlib import Path
from dataclasses import dataclass, field

import arc_agi
from arc_agi import OperationMode


ENVIRONMENTS_DIR = os.getenv("ENVIRONMENTS_DIR", "environment_files")


@dataclass
class SyncResult:
    total: int = 0
    downloaded: int = 0
    skipped: int = 0
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.failed) == 0


def get_local_game_ids() -> set[str]:
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
    return len(get_local_game_ids())


def needs_sync() -> bool:
    return get_local_game_count() == 0


def sync_games(progress_callback=None) -> SyncResult:
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
                    try:
                        wrapper.close()
                    except Exception:
                        pass
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

        try:
            arc.close_scorecard()
        except Exception:
            pass

    finally:
        try:
            del arc
        except Exception:
            pass

    return result
