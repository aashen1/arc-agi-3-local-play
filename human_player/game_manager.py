import time

import numpy as np
from arcengine import GameAction, GameState, FrameDataRaw
import arc_agi


class GameManager:
    def __init__(self):
        self.arc = arc_agi.Arcade()
        self.env = None
        self.game_id = None
        self.step_count = 0
        self.total_steps = 0
        self.level_start_time = None
        self.game_start_time = None
        self.levels_completed = 0
        self.max_levels = 0
        self._prev_levels_completed = 0

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

        self.env = self.arc.make(game_id)
        if self.env is None:
            return False

        obs = self.env.reset()
        if obs:
            self._update_from_obs(obs)
        return True

    def execute_action(self, action: GameAction, data: dict = None) -> FrameDataRaw | None:
        if self.env is None:
            return None

        if action == GameAction.RESET:
            return self.reset_level()

        if data:
            obs = self.env.step(action, data=data)
        else:
            obs = self.env.step(action)

        if obs:
            self.step_count += 1
            self.total_steps += 1
            self._update_from_obs(obs)

        return obs

    def reset_level(self) -> FrameDataRaw | None:
        if self.env is None:
            return None

        self.step_count = 0
        self.level_start_time = time.time()
        obs = self.env.reset()
        if obs:
            self._update_from_obs(obs)
        return obs

    def close_game(self):
        self.env = None
        self.game_id = None

    def get_current_frame(self) -> np.ndarray | None:
        obs = self.env.observation_space if self.env else None
        if obs is None or obs.frame is None:
            return None
        frame = obs.frame
        if isinstance(frame, list):
            return np.array(frame[0]) if frame else None
        return np.array(frame)

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
