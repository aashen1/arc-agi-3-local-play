import time
from arcengine import GameAction, GameState, FrameDataRaw
import arc_agi

from human_player.config import DEFAULT_RENDER_MODE


class GameManager:
    def __init__(self, render_mode=DEFAULT_RENDER_MODE):
        self.arc = arc_agi.Arcade()
        self.env = None
        self.game_id = None
        self.render_mode = render_mode
        self.step_count = 0
        self.total_steps = 0
        self.level_start_time = None
        self.game_start_time = None
        self.levels_completed = 0
        self.max_levels = 0
        self._prev_levels_completed = 0

    ACTION_MAP = {
        "ACTION1": GameAction.ACTION1,
        "ACTION2": GameAction.ACTION2,
        "ACTION3": GameAction.ACTION3,
        "ACTION4": GameAction.ACTION4,
        "ACTION5": GameAction.ACTION5,
        "ACTION6": GameAction.ACTION6,
        "ACTION7": GameAction.ACTION7,
        "RESET": GameAction.RESET,
    }

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

        self.env = self.arc.make(game_id, render_mode=self.render_mode)
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

    def auto_advance(self, level_actions: dict[int, list[dict]],
                     on_level_start=None, on_level_done=None,
                     on_fail=None) -> int:
        advanced = 0
        for level_idx in sorted(level_actions.keys()):
            actions = level_actions[level_idx]
            if on_level_start:
                on_level_start(level_idx, len(actions))

            prev_lc = self.levels_completed
            success = False

            for i, act_info in enumerate(actions):
                action_name = act_info.get("action", "")
                action = self.ACTION_MAP.get(action_name)
                if action is None:
                    continue

                data = act_info.get("action_data") or None
                obs = self.execute_action(action, data=data)
                if obs is None:
                    if on_fail:
                        on_fail(level_idx, i, "env returned None")
                    return advanced

                if obs.state == GameState.GAME_OVER:
                    if on_fail:
                        on_fail(level_idx, i, "GAME_OVER during replay")
                    return advanced

                if self.levels_completed > prev_lc:
                    success = True
                    break

            if success:
                advanced += 1
                if on_level_done:
                    on_level_done(level_idx)
                obs = self.env.reset()
                if obs:
                    self._update_from_obs(obs)
                self.step_count = 0
                self.level_start_time = time.time()
            else:
                if on_fail:
                    on_fail(level_idx, len(actions),
                            "replay did not trigger level completion")
                return advanced

        return advanced

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
