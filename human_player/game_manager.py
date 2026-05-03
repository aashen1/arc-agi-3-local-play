import time

import numpy as np
from arcengine import GameAction, GameState, FrameDataRaw
import arc_agi

from human_player.mode import (
    get_operation_mode, get_player_mode, get_player_tag,
    is_agent_mode, is_human_mode, PlayerMode,
)

ANIMATION_FPS = 15


class GameManager:
    def __init__(self):
        op_mode = get_operation_mode()
        player_mode = get_player_mode()

        if is_agent_mode():
            from dotenv import load_dotenv
            load_dotenv()
            print(f"[GameManager] Agent mode — loading .env, operation_mode={op_mode.name}")
        else:
            print(f"[GameManager] Human mode — forced OFFLINE, skipping .env")

        self.arc = arc_agi.Arcade(operation_mode=op_mode)
        self.player_mode = player_mode
        self._scorecard_id = None
        self.env = None
        self.game_id = None
        self.step_count = 0
        self.total_steps = 0
        self.level_start_time = None
        self.game_start_time = None
        self.levels_completed = 0
        self.max_levels = 0
        self._prev_levels_completed = 0

        self._anim_frames: list[np.ndarray] = []
        self._anim_index: int = 0
        self._anim_start_time: float = 0.0
        self._anim_frame_duration: float = 1.0 / ANIMATION_FPS

    def list_games(self):
        return self.arc.get_environments()

    def start_game(self, game_id: str) -> bool:
        self.game_id = game_id
        self.step_count = 0
        self.total_steps = 0
        self.levels_completed = 0
        self._prev_levels_completed = 0
        self.max_levels = 0
        self.game_start_time = time.time()
        self.level_start_time = time.time()
        self._anim_frames = []
        self._anim_index = 0

        if is_agent_mode():
            tag = get_player_tag()
            self._scorecard_id = self.arc.create_scorecard(tags=[tag])
            self.env = self.arc.make(game_id, scorecard_id=self._scorecard_id)
        else:
            self._scorecard_id = None
            self.env = self.arc.make(game_id)

        if self.env is None:
            return False

        obs = self.env.reset()
        if obs:
            self._update_from_obs(obs)
            self._start_animation(obs)
        return True

    def execute_action(self, action: GameAction, data: dict = None,
                       reasoning: dict | str | None = None) -> FrameDataRaw | None:
        if self.env is None:
            return None

        if action == GameAction.RESET:
            return self.reset_level()

        kwargs = {}
        if data:
            kwargs["data"] = data
        if is_agent_mode() and reasoning is not None:
            kwargs["reasoning"] = reasoning

        obs = self.env.step(action, **kwargs)

        if obs:
            self.step_count += 1
            self.total_steps += 1
            self._update_from_obs(obs)
            self._start_animation(obs)

        return obs

    def reset_level(self) -> FrameDataRaw | None:
        if self.env is None:
            return None

        self.step_count = 0
        self.level_start_time = time.time()
        self._anim_frames = []
        self._anim_index = 0
        obs = self.env.reset()
        if obs:
            self._update_from_obs(obs)
            self._start_animation(obs)
        return obs

    def close_game(self):
        if is_agent_mode() and self._scorecard_id:
            try:
                self.arc.close_scorecard(self._scorecard_id)
            except Exception:
                pass
            self._scorecard_id = None
        self.env = None
        self.game_id = None

    def get_available_action_ids(self) -> list[int]:
        if self.env is None:
            return []
        available = self.env.action_space
        from human_player.official_recording import ACTION_ID_MAP
        return [ACTION_ID_MAP[a] for a in available if a in ACTION_ID_MAP]

    def get_frame_as_2d_list(self) -> list:
        obs = self.env.observation_space if self.env else None
        if obs is None or obs.frame is None:
            return []
        frame = obs.frame
        if isinstance(frame, list):
            if frame and isinstance(frame[-1], list) and isinstance(frame[-1][0], list):
                return frame[-1]
            if frame:
                return frame[-1] if isinstance(frame[-1], list) else frame
            return []
        if isinstance(frame, np.ndarray):
            return frame.tolist()
        return []

    def get_current_frame(self) -> np.ndarray | None:
        if self.is_animating():
            return self._anim_frames[self._anim_index]

        obs = self.env.observation_space if self.env else None
        if obs is None or obs.frame is None:
            return None
        frame = obs.frame
        if isinstance(frame, list):
            if not frame:
                return None
            return np.array(frame[-1])
        return np.array(frame)

    def is_animating(self) -> bool:
        return len(self._anim_frames) > 0 and self._anim_index < len(self._anim_frames)

    def advance_animation(self) -> bool:
        if not self.is_animating():
            return False

        now = time.time()
        elapsed = now - self._anim_start_time
        target_index = int(elapsed / self._anim_frame_duration)

        if target_index > self._anim_index:
            self._anim_index = min(target_index, len(self._anim_frames) - 1)

        if self._anim_index >= len(self._anim_frames) - 1:
            self._anim_frames = []
            self._anim_index = 0
            return False
        return True

    def skip_animation(self):
        self._anim_frames = []
        self._anim_index = 0

    def _start_animation(self, obs: FrameDataRaw):
        if obs is None or obs.frame is None:
            self._anim_frames = []
            self._anim_index = 0
            return

        frame = obs.frame
        if isinstance(frame, list) and len(frame) > 1:
            self._anim_frames = [np.array(f) for f in frame]
            self._anim_index = 0
            self._anim_start_time = time.time()
        else:
            self._anim_frames = []
            self._anim_index = 0

    def get_elapsed_ms(self) -> int:
        if self.level_start_time is None:
            return 0
        return int((time.time() - self.level_start_time) * 1000)

    def get_total_elapsed_ms(self) -> int:
        if self.game_start_time is None:
            return 0
        return int((time.time() - self.game_start_time) * 1000)

    def get_state_summary(self) -> dict:
        return {
            "game_id": self.game_id,
            "step_count": self.step_count,
            "total_steps": self.total_steps,
            "levels_completed": self.levels_completed,
            "max_levels": self.max_levels,
            "elapsed_ms": self.get_elapsed_ms(),
            "total_elapsed_ms": self.get_total_elapsed_ms(),
        }

    def did_level_up(self) -> bool:
        if self.levels_completed > self._prev_levels_completed:
            self._prev_levels_completed = self.levels_completed
            return True
        return False

    def jump_to_level(self, level_index: int) -> bool:
        if self.env is None:
            return False

        game = getattr(self.env, '_game', None)
        if game is None:
            return False

        total = len(game._levels)
        if level_index < 0 or level_index >= total:
            return False

        game.set_level(level_index)
        game._state = GameState.NOT_FINISHED
        game._score = level_index
        game._action_count = 0

        self.levels_completed = level_index
        self._prev_levels_completed = level_index
        self.step_count = 0
        self.level_start_time = time.time()

        action = GameAction.ACTION1
        obs = self.env.step(action)
        if obs:
            self.step_count = 1
            self.total_steps += 1
            self._update_from_obs(obs)
            return True
        return False

    def _update_from_obs(self, obs: FrameDataRaw):
        if hasattr(obs, 'levels_completed') and obs.levels_completed is not None:
            if obs.levels_completed > self.levels_completed:
                self._prev_levels_completed = self.levels_completed
                self.levels_completed = obs.levels_completed
            if obs.levels_completed > self.max_levels:
                self.max_levels = obs.levels_completed

        if hasattr(obs, 'win_levels') and obs.win_levels is not None:
            if obs.win_levels > self.max_levels:
                self.max_levels = obs.win_levels
