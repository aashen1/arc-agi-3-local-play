import os
import sys
import threading
import time

import pygame
from arcengine import GameAction, GameState

from human_player.config import (
    DATA_DIR,
    DESIGN_HEIGHT,
    DESIGN_WIDTH,
    FPS,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    PLAYERS_DIR,
    RECORDINGS_DIR,
    RECORDS_DIR,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    get_keymap,
    get_keymap_scheme,
    set_keymap_scheme,
)
from human_player.game_manager import GameManager
from human_player.game_sync import sync_games
from human_player.level_manager import LevelManager
from human_player.menu import MenuRenderer
from human_player.official_recording import OfficialRecordingManager
from human_player.player_manager import PlayerManager
from human_player.recording import RecordingManager
from human_player.renderer import Renderer
from human_player.stats_manager import StatsManager


class App:
    """Main application class managing the game client state machine."""

    def __init__(self):
        _ensure_dirs()

        pygame.init()
        self.screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT),
            pygame.RESIZABLE,
        )
        pygame.display.set_caption("ARC-AGI-3 Human Player")
        self.clock = pygame.time.Clock()

        self.virtual_surface = pygame.Surface((DESIGN_WIDTH, DESIGN_HEIGHT))

        self.game_manager = GameManager()
        self.renderer = Renderer(self.virtual_surface)
        self.menu_renderer = MenuRenderer(self.virtual_surface)

        self.player_manager = PlayerManager()
        self.level_manager = LevelManager(progress_file=self.player_manager.get_progress_file())
        self.stats_manager = StatsManager(records_dir=self.player_manager.get_records_dir())
        self.recording_manager = RecordingManager()
        self.official_recording = OfficialRecordingManager(self.player_manager)

        self.state = "MAIN_MENU"
        self.keymap_scheme = get_keymap_scheme()
        self.games = self.game_manager.list_games()
        self.show_sync_button = self.game_manager._show_sync_button

        self.sync_progress = None
        self.sync_result = None
        self.sync_thread = None

        self.current_level = 0
        self.game_over_recorded = False
        self.overlay_state = None
        self.session_id = None
        self.player_input_text = ""
        self.player_input_active = False
        self.delete_target = None
        self.delete_confirm_text = ""
        self.delete_confirm_active = False
        self.win_elapsed_ms = 0
        self.win_step_count = 0
        self.total_elapsed_ms = 0
        self.total_steps = 0

        self.window_w = WINDOW_WIDTH
        self.window_h = WINDOW_HEIGHT
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self._recalc_layout()

        if self.game_manager._needs_sync:
            self.state = "SYNCING"

    def _recalc_layout(self):
        self.scale_factor = min(self.window_w / DESIGN_WIDTH, self.window_h / DESIGN_HEIGHT)
        scaled_w = int(DESIGN_WIDTH * self.scale_factor)
        scaled_h = int(DESIGN_HEIGHT * self.scale_factor)
        self.offset_x = (self.window_w - scaled_w) // 2
        self.offset_y = (self.window_h - scaled_h) // 2

    def _window_to_design(self, wx, wy):
        dx = (wx - self.offset_x) / self.scale_factor
        dy = (wy - self.offset_y) / self.scale_factor
        return int(dx), int(dy)

    def _switch_player(self, name):
        self.player_manager.set_player(name)
        self.level_manager.set_progress_file(self.player_manager.get_progress_file())
        self.stats_manager.set_records_dir(self.player_manager.get_records_dir())
        self.games = self.game_manager.list_games()

    def _scale_and_present(self):
        scaled_w = int(DESIGN_WIDTH * self.scale_factor)
        scaled_h = int(DESIGN_HEIGHT * self.scale_factor)
        scaled = pygame.transform.scale(self.virtual_surface, (scaled_w, scaled_h))
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled, (self.offset_x, self.offset_y))
        pygame.display.flip()

    def _refresh_game_manager(self):
        self.game_manager = GameManager()
        self.games = self.game_manager.list_games()
        self.show_sync_button = self.game_manager._show_sync_button

    def run(self):
        try:
            while True:
                raw_mouse_pos = pygame.mouse.get_pos()
                mouse_pos = self._window_to_design(*raw_mouse_pos)

                skip_frame = False
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()

                    if event.type == pygame.VIDEORESIZE:
                        self.window_w = max(event.w, MIN_WINDOW_WIDTH)
                        self.window_h = max(event.h, MIN_WINDOW_HEIGHT)
                        self.screen = pygame.display.set_mode(
                            (self.window_w, self.window_h),
                            pygame.RESIZABLE,
                        )
                        self._recalc_layout()
                        continue

                    if hasattr(event, "pos") and event.type in (
                        pygame.MOUSEBUTTONDOWN,
                        pygame.MOUSEBUTTONUP,
                        pygame.MOUSEMOTION,
                    ):
                        event.pos = self._window_to_design(*event.pos)

                    if self._process_event(event):
                        skip_frame = True

                if skip_frame:
                    continue

                self._render(mouse_pos)
                self._scale_and_present()
                self.clock.tick(FPS)

        except Exception:
            import traceback

            traceback.print_exc()
            pygame.quit()
            sys.exit(1)

    def _process_event(self, event):
        """Dispatch event to the current state handler.

        Returns True if the current frame should be skipped (no rendering).
        """
        if self.state == "MAIN_MENU":
            return self._process_main_menu_event(event)
        elif self.state == "SETTINGS":
            return self._process_settings_event(event)
        elif self.state == "SYNC_COMPLETE":
            return self._process_sync_complete_event(event)
        elif self.state == "STATS":
            return self._process_stats_event(event)
        elif self.state == "PLAYER_SELECT":
            return self._process_player_select_event(event)
        elif self.state == "GAME":
            return self._process_game_event(event)
        return False

    def _process_main_menu_event(self, event):
        result = _handle_menu_event(event, self.menu_renderer, self.games)
        if result is None or result == "quit":
            pygame.quit()
            sys.exit()
        elif result == "toggle_view":
            self.menu_renderer.toggle_view_mode()
        elif result == "scrollbar_thumb":
            self.menu_renderer.start_scroll_drag(event.pos[1])
        elif result == "scrollbar_track":
            self.menu_renderer.handle_scrollbar_track_click(event.pos, self.games)
        elif result == "settings":
            self.state = "SETTINGS"
        elif result == "stats":
            self.state = "STATS"
        elif result == "player":
            self.state = "PLAYER_SELECT"
            self.player_input_text = ""
            self.player_input_active = False
            self.delete_target = None
            self.delete_confirm_text = ""
            self.delete_confirm_active = False
        elif result == "nav_up":
            self.menu_renderer.navigate_up(self.games)
        elif result == "nav_down":
            self.menu_renderer.navigate_down(self.games)
        elif result == "nav_enter":
            idx = self.menu_renderer.hover_index
            if 0 <= idx < len(self.games) and self._try_start_game(idx):
                return True
        elif isinstance(result, str) and result.startswith("game:"):
            idx = int(result.split(":")[1])
            if idx < len(self.games) and self._try_start_game(idx):
                return True

        if self.state == "MAIN_MENU":
            if event.type == pygame.MOUSEWHEEL:
                self.menu_renderer.handle_scroll(event.y, self.games)
            if event.type == pygame.MOUSEMOTION and self.menu_renderer.scroll_dragging:
                self.menu_renderer.update_scroll_drag(event.pos[1], self.games)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.menu_renderer.end_scroll_drag()

        return False

    def _try_start_game(self, idx):
        """Attempt to start a game from the menu. Returns True if frame should be skipped."""
        game_id = self.games[idx].game_id
        resume = _check_resume(
            game_id,
            self.level_manager,
            self.menu_renderer,
            self.virtual_surface,
            self.screen,
            self.clock,
            self.scale_factor,
            self.offset_x,
            self.offset_y,
            self.game_manager._jump_available,
        )
        if resume is None:
            return True
        if _start_game(game_id, resume, self.game_manager, self.level_manager):
            self.state = "GAME"
            self.current_level = self.game_manager.levels_completed
            self.game_over_recorded = False
            self.overlay_state = None
            self.session_id = self.recording_manager.start_session(game_id)
            levels_at_start = self.game_manager.levels_completed
            self.official_recording.start_session(
                game_id,
                self.game_manager.max_levels,
                levels_at_start,
            )
        return False

    def _process_settings_event(self, event):
        result = _handle_settings_event(event, self.menu_renderer, self.keymap_scheme)
        if result == "back":
            self.state = "MAIN_MENU"
        elif result in ("wasd", "arrows"):
            self.keymap_scheme = result
            set_keymap_scheme(result)
        elif result in ("conservative", "auto"):
            from human_player.config import set_sync_mode

            set_sync_mode(result)
            self._refresh_game_manager()
        elif result == "download":
            self.state = "SYNCING"
            self.sync_progress = [0, 0, "", "starting"]
            self.sync_result = None
        return False

    def _process_sync_complete_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.sync_thread = None
            self._refresh_game_manager()
            self.state = "MAIN_MENU"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            btn = self.menu_renderer.handle_button_click(event.pos)
            if btn == "ok":
                self.sync_thread = None
                self._refresh_game_manager()
                self.state = "MAIN_MENU"
        return False

    def _process_stats_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "MAIN_MENU"
        if event.type == pygame.MOUSEBUTTONDOWN:
            btn = self.menu_renderer.handle_button_click(event.pos)
            if btn == "back":
                self.state = "MAIN_MENU"
        return False

    def _process_player_select_event(self, event):
        if self.delete_target:
            result = _handle_delete_confirm_event(
                event,
                self.menu_renderer,
                self.delete_target,
                self.delete_confirm_text,
                self.delete_confirm_active,
            )
            if result == "cancel_delete":
                self.delete_target = None
                self.delete_confirm_text = ""
                self.delete_confirm_active = False
            elif result == "confirm_delete":
                self.player_manager.delete_player(self.delete_target)
                self.delete_target = None
                self.delete_confirm_text = ""
                self.delete_confirm_active = False
            elif isinstance(result, str) and result.startswith("del_input:"):
                self.delete_confirm_text = result.split(":", 1)[1]
                self.delete_confirm_active = True
            elif result == "del_input_focus":
                self.delete_confirm_active = True
            elif result == "del_input_blur":
                self.delete_confirm_active = False
        else:
            result = _handle_player_event(
                event,
                self.menu_renderer,
                self.player_manager,
                self.player_input_text,
            )
            if result == "back":
                self.state = "MAIN_MENU"
            elif result == "create":
                name = self.player_input_text.strip()
                if name:
                    self._switch_player(name)
                    self.player_input_text = ""
                    self.state = "MAIN_MENU"
            elif isinstance(result, str) and result.startswith("select:"):
                name = result.split(":", 1)[1]
                self._switch_player(name)
                self.state = "MAIN_MENU"
            elif isinstance(result, str) and result.startswith("delete:"):
                name = result.split(":", 1)[1]
                self.delete_target = name
                self.delete_confirm_text = ""
                self.delete_confirm_active = True
            elif isinstance(result, str) and result.startswith("input:"):
                self.player_input_text = result.split(":", 1)[1]
                self.player_input_active = True
            elif result == "input_focus":
                self.player_input_active = True
            elif result == "input_blur":
                self.player_input_active = False
        return False

    def _process_game_event(self, event):
        overlay_just_set = False
        action_result = False

        if self.game_manager.is_animating():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game_manager.skip_animation()
                    action_result = "exit"
                else:
                    self.game_manager.skip_animation()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.game_manager.skip_animation()
        else:
            if event.type == pygame.MOUSEMOTION:
                self.renderer.update_bottom_button_hover(event.pos)
            if self.overlay_state:
                pass
            else:
                action_result = _handle_game_event(
                    event,
                    self.game_manager,
                    self.renderer,
                )

        if action_result == "exit":
            final_state = "NOT_FINISHED"
            if self.game_manager.env:
                obs = self.game_manager.env.observation_space
                if obs and hasattr(obs, "state"):
                    final_state = obs.state.name
            self.recording_manager.end_session()
            if self.official_recording.is_recording:
                self.official_recording.end_session(final_state)
            self.game_manager.close_game()
            self.state = "MAIN_MENU"
            self.games = self.game_manager.list_games()
            return True

        if action_result and self.overlay_state is None:
            action, data = action_result
            available = self.game_manager.env.action_space if self.game_manager.env else []
            if action in available or action == GameAction.RESET:
                obs = self.game_manager.execute_action(action, data)
                self.recording_manager.record_step(
                    action,
                    data,
                    obs,
                    self.game_manager.step_count,
                    self.game_manager.get_elapsed_ms(),
                )
                self.official_recording.record_step(
                    action,
                    data,
                    obs,
                    available,
                )

                if self.game_manager.did_level_up():
                    self.current_level = self.game_manager.levels_completed - 1
                    _handle_win(
                        self.game_manager,
                        self.level_manager,
                        self.stats_manager,
                        self.current_level,
                        self.session_id,
                    )
                    self.current_level = self.game_manager.levels_completed
                    self.game_over_recorded = False

                if obs and obs.state == GameState.WIN:
                    self.win_elapsed_ms = self.game_manager.get_elapsed_ms()
                    self.win_step_count = self.game_manager.step_count
                    if (
                        self.game_manager.max_levels > 0
                        and self.game_manager.levels_completed >= self.game_manager.max_levels
                    ):
                        self.total_elapsed_ms = self.game_manager.get_total_elapsed_ms()
                        self.total_steps = self.game_manager.total_steps
                        self.overlay_state = "all_complete"
                    else:
                        self.overlay_state = "win"
                    overlay_just_set = True
                elif obs and obs.state == GameState.GAME_OVER:
                    if not self.game_over_recorded:
                        self.stats_manager.record_attempt(
                            self.game_manager.game_id,
                            self.current_level,
                            self.game_manager.step_count,
                            self.game_manager.get_elapsed_ms(),
                            "GAME_OVER",
                            self.session_id,
                        )
                        self.game_over_recorded = True
                    self.overlay_state = "game_over"
                    overlay_just_set = True

        if self.overlay_state and not overlay_just_set and event.type == pygame.KEYDOWN:
            if self.overlay_state == "win":
                self.overlay_state = None
                self.game_manager.step_count = 0
                self.game_manager.level_start_time = time.time()
                self.game_over_recorded = False
            elif self.overlay_state == "game_over":
                if event.key == pygame.K_r:
                    self.overlay_state = None
                    self.game_manager.reset_level()
                    self.game_over_recorded = False
            elif self.overlay_state == "all_complete":
                self.recording_manager.end_session()
                if self.official_recording.is_recording:
                    self.official_recording.end_session("WIN")
                self.game_manager.close_game()
                self.state = "MAIN_MENU"
                self.games = self.game_manager.list_games()
                self.overlay_state = None
                return True

        if (
            self.overlay_state
            and not overlay_just_set
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            if self.overlay_state == "win":
                self.overlay_state = None
                self.game_manager.step_count = 0
                self.game_manager.level_start_time = time.time()
                self.game_over_recorded = False
            elif self.overlay_state == "game_over":
                btn = self.renderer.check_overlay_button_click(event.pos)
                if btn == "reset":
                    self.overlay_state = None
                    self.game_manager.reset_level()
                    self.game_over_recorded = False
                elif btn == "menu":
                    self.recording_manager.end_session()
                    if self.official_recording.is_recording:
                        self.official_recording.end_session("GAME_OVER")
                    self.game_manager.close_game()
                    self.state = "MAIN_MENU"
                    self.games = self.game_manager.list_games()
                    self.overlay_state = None
                    return True
                else:
                    self.overlay_state = None
                    self.game_manager.reset_level()
                    self.game_over_recorded = False
            elif self.overlay_state == "all_complete":
                self.recording_manager.end_session()
                if self.official_recording.is_recording:
                    self.official_recording.end_session("WIN")
                self.game_manager.close_game()
                self.state = "MAIN_MENU"
                self.games = self.game_manager.list_games()
                self.overlay_state = None
                return True

        return False

    def _render(self, mouse_pos):
        if self.state == "MAIN_MENU":
            self._render_main_menu(mouse_pos)
        elif self.state == "SYNCING":
            self._render_syncing()
        elif self.state == "SYNC_COMPLETE":
            self._render_sync_complete()
        elif self.state == "SETTINGS":
            self._render_settings()
        elif self.state == "STATS":
            self._render_stats()
        elif self.state == "PLAYER_SELECT":
            self._render_player_select()
        elif self.state == "GAME":
            self._render_game(mouse_pos)

    def _render_main_menu(self, mouse_pos):
        self.menu_renderer.handle_main_menu_hover(mouse_pos)
        self.menu_renderer.draw_main_menu(
            self.games,
            self.level_manager,
            self.keymap_scheme,
            self.player_manager.get_current_player(),
        )

    def _render_syncing(self):
        if self.sync_thread is None:
            self.sync_progress = [0, 0, "", "starting"]

            app = self

            def _on_sync_progress(current, total, gid, status):
                app.sync_progress = [current, total, gid, status]

            def _run_sync():
                app.sync_result = sync_games(progress_callback=_on_sync_progress)

            self.sync_thread = threading.Thread(target=_run_sync, daemon=True)
            self.sync_thread.start()

        if self.sync_thread and not self.sync_thread.is_alive() and self.sync_result is not None:
            self.state = "SYNC_COMPLETE"

        if self.sync_progress:
            self.menu_renderer.draw_sync_progress(
                self.sync_progress[0],
                self.sync_progress[1],
                self.sync_progress[2],
                self.sync_progress[3],
            )

    def _render_sync_complete(self):
        self.menu_renderer.draw_sync_complete(self.sync_result)

    def _render_settings(self):
        from human_player.config import get_sync_mode

        self.menu_renderer.draw_settings(
            self.keymap_scheme, sync_mode=get_sync_mode(), show_sync_button=self.show_sync_button
        )

    def _render_stats(self):
        self.menu_renderer.draw_stats(self.games, self.level_manager, self.stats_manager)

    def _render_player_select(self):
        players = self.player_manager.list_players()
        player_metadata = {}
        for p in players:
            player_metadata[p] = self.player_manager.get_player_metadata(p)
        self.menu_renderer.draw_player_select(
            players,
            self.player_manager.get_current_player(),
            player_metadata,
            self.player_input_text,
            self.player_input_active,
        )
        if self.delete_target:
            meta = player_metadata.get(self.delete_target, {})
            self.menu_renderer.draw_delete_confirm(
                self.delete_target,
                meta,
                self.delete_confirm_text,
                self.delete_confirm_active,
            )

    def _render_game(self, mouse_pos):
        self.game_manager.advance_animation()
        frame = self.game_manager.get_current_frame()
        grid_pos = self.renderer.pixel_to_grid(*mouse_pos)
        available = self.game_manager.env.action_space if self.game_manager.env else []

        self.renderer.draw_frame(
            frame,
            grid_pos,
            self.game_manager.step_count,
            self.game_manager.get_elapsed_ms(),
            self.game_manager.levels_completed,
            self.game_manager.max_levels,
            available,
            self.keymap_scheme,
            self.game_manager.game_id,
        )

        if self.overlay_state == "win":
            best_steps = self.level_manager.get_best_steps(
                self.game_manager.game_id, self.current_level
            )
            best_time = self.level_manager.get_best_time_ms(
                self.game_manager.game_id, self.current_level
            )
            self.renderer.draw_overlay_win(
                self.current_level,
                self.win_step_count,
                self.win_elapsed_ms,
                best_steps,
                best_time,
            )
        elif self.overlay_state == "game_over":
            self.renderer.draw_overlay_game_over(self.game_manager.step_count)
        elif self.overlay_state == "all_complete":
            self.renderer.draw_overlay_all_complete(
                self.game_manager.game_id,
                self.total_steps,
                self.total_elapsed_ms,
            )


def _handle_menu_event(event, menu_renderer, games):
    """Process a single Pygame event while in the MAIN_MENU state."""
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_q:
            return None
        if event.key == pygame.K_s:
            return "settings"
        if event.key == pygame.K_v:
            return "stats"
        if event.key == pygame.K_p:
            return "player"
        if event.key == pygame.K_UP:
            return "nav_up"
        if event.key == pygame.K_DOWN:
            return "nav_down"
        if event.key == pygame.K_RETURN:
            return "nav_enter"
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return menu_renderer.handle_main_menu_click(event.pos)
    return False


def _handle_settings_event(event, menu_renderer, keymap_scheme):
    """Process a single Pygame event while in the SETTINGS state."""
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return "back"
        if event.key == pygame.K_d:
            return "download"
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        btn = menu_renderer.handle_button_click(event.pos)
        if btn in ("wasd", "arrows"):
            return btn
        if btn in ("conservative", "auto"):
            return btn
        if btn == "download":
            return "download"
        if btn == "back":
            return "back"
    return False


def _handle_player_event(event, menu_renderer, player_manager, input_text):
    """Process a single Pygame event while in the PLAYER_SELECT state."""
    players = player_manager.list_players()
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return "back"
        if event.key == pygame.K_RETURN:
            return "create"
        if event.key == pygame.K_BACKSPACE:
            new_text = input_text[:-1]
            return f"input:{new_text}"
        if event.unicode and event.unicode.isprintable() and len(input_text) < 20:
            new_text = input_text + event.unicode
            return f"input:{new_text}"
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if hasattr(menu_renderer, "input_rect") and menu_renderer.input_rect.collidepoint(
            event.pos
        ):
            return "input_focus"
        result = menu_renderer.handle_player_click(event.pos, players)
        if result:
            return result
        return "input_blur"
    return False


def _handle_delete_confirm_event(event, menu_renderer, target_name, confirm_text, confirm_active):
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return "cancel_delete"
        if event.key == pygame.K_RETURN:
            if confirm_text == target_name:
                return "confirm_delete"
            return False
        if event.key == pygame.K_BACKSPACE:
            new_text = confirm_text[:-1]
            return f"del_input:{new_text}"
        if event.unicode and event.unicode.isprintable() and len(confirm_text) < 30:
            new_text = confirm_text + event.unicode
            return f"del_input:{new_text}"
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if hasattr(
            menu_renderer, "delete_input_rect"
        ) and menu_renderer.delete_input_rect.collidepoint(event.pos):
            return "del_input_focus"
        for name, rect in menu_renderer.button_rects.items():
            if rect.collidepoint(event.pos):
                if name == "cancel_delete":
                    return "cancel_delete"
                if name == "confirm_delete" and confirm_text == target_name:
                    return "confirm_delete"
        return "del_input_blur"
    return False


def _handle_game_event(event, game_manager, renderer):
    """Process a single Pygame event while in the GAME state."""
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return "exit"
        keymap = get_keymap()
        if event.key in keymap:
            return (keymap[event.key], None)

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        button_action = renderer.check_bottom_button_click(event.pos)
        if button_action == "menu":
            return "exit"
        elif button_action == "reset":
            return (GameAction.RESET, None)
        elif button_action == "undo":
            return (GameAction.ACTION7, None)

        gx, gy = renderer.pixel_to_grid(*event.pos)
        if gx is not None and gy is not None:
            available = game_manager.env.action_space if game_manager.env else []
            if GameAction.ACTION6 in available:
                return (GameAction.ACTION6, {"x": gx, "y": gy})

    return False


def _check_resume(
    game_id,
    level_manager,
    menu_renderer,
    virtual_surface,
    screen,
    clock,
    scale_factor,
    offset_x,
    offset_y,
    jump_available=True,
):
    """Show a resume prompt if the player has progress in the given game."""
    completed = level_manager.get_completed_count(game_id)
    next_level = level_manager.get_next_uncompleted_level(game_id)
    total = level_manager.get_total_levels(game_id)

    if completed == 0:
        return "new"

    if level_manager.is_fully_completed(game_id):
        current_level = level_manager.get_current_level(game_id)
        has_playthrough = current_level is not None and current_level < total
        return _show_completed_prompt(
            game_id,
            total,
            current_level,
            has_playthrough,
            level_manager,
            menu_renderer,
            virtual_surface,
            screen,
            clock,
            scale_factor,
            offset_x,
            offset_y,
            jump_available,
        )

    def _scale_and_present():
        scaled_w = int(DESIGN_WIDTH * scale_factor)
        scaled_h = int(DESIGN_HEIGHT * scale_factor)
        scaled = pygame.transform.scale(virtual_surface, (scaled_w, scaled_h))
        screen.fill((0, 0, 0))
        screen.blit(scaled, (offset_x, offset_y))
        pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if hasattr(event, "pos") and event.type in (
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
            ):
                dx = (event.pos[0] - offset_x) / scale_factor
                dy = (event.pos[1] - offset_y) / scale_factor
                event.pos = (int(dx), int(dy))
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    return "continue"
                if event.key == pygame.K_n:
                    return "new"
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                btn = menu_renderer.handle_button_click(event.pos)
                if btn == "continue":
                    return "continue"
                if btn == "new":
                    return "new"
                if btn == "back":
                    return None

        menu_renderer.draw_resume_prompt(game_id, completed, total, next_level)
        _scale_and_present()
        clock.tick(FPS)


def _show_completed_prompt(
    game_id,
    total,
    current_level,
    has_playthrough,
    level_manager,
    menu_renderer,
    virtual_surface,
    screen,
    clock,
    scale_factor,
    offset_x,
    offset_y,
    jump_available=True,
):
    def _scale_and_present():
        scaled_w = int(DESIGN_WIDTH * scale_factor)
        scaled_h = int(DESIGN_HEIGHT * scale_factor)
        scaled = pygame.transform.scale(virtual_surface, (scaled_w, scaled_h))
        screen.fill((0, 0, 0))
        screen.blit(scaled, (offset_x, offset_y))
        pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if hasattr(event, "pos") and event.type in (
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
            ):
                dx = (event.pos[0] - offset_x) / scale_factor
                dy = (event.pos[1] - offset_y) / scale_factor
                event.pos = (int(dx), int(dy))
            if event.type == pygame.KEYDOWN:
                if has_playthrough and event.key == pygame.K_c:
                    return "continue"
                if event.key == pygame.K_n:
                    return "new"
                if event.key == pygame.K_l and jump_available:
                    result = _show_level_select(
                        game_id,
                        total,
                        level_manager,
                        menu_renderer,
                        virtual_surface,
                        screen,
                        clock,
                        scale_factor,
                        offset_x,
                        offset_y,
                    )
                    if result is not None:
                        return result
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                btn = menu_renderer.handle_button_click(event.pos)
                if btn == "continue":
                    return "continue"
                if btn == "new":
                    return "new"
                if btn == "select" and jump_available:
                    result = _show_level_select(
                        game_id,
                        total,
                        level_manager,
                        menu_renderer,
                        virtual_surface,
                        screen,
                        clock,
                        scale_factor,
                        offset_x,
                        offset_y,
                    )
                    if result is not None:
                        return result
                if btn == "back":
                    return None

        menu_renderer.draw_completed_prompt(
            game_id,
            total,
            current_level,
            has_playthrough,
            jump_available=jump_available,
        )
        _scale_and_present()
        clock.tick(FPS)


def _show_level_select(
    game_id,
    total_levels,
    level_manager,
    menu_renderer,
    virtual_surface,
    screen,
    clock,
    scale_factor,
    offset_x,
    offset_y,
):
    menu_renderer.level_input_text = ""
    menu_renderer.level_input_active = False

    def _scale_and_present():
        scaled_w = int(DESIGN_WIDTH * scale_factor)
        scaled_h = int(DESIGN_HEIGHT * scale_factor)
        scaled = pygame.transform.scale(virtual_surface, (scaled_w, scaled_h))
        screen.fill((0, 0, 0))
        screen.blit(scaled, (offset_x, offset_y))
        pygame.display.flip()

    def _try_parse_level(text):
        text = text.strip()
        if not text:
            return None
        try:
            num = int(text)
        except ValueError:
            return None
        if 1 <= num <= total_levels:
            return num - 1
        return None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if hasattr(event, "pos") and event.type in (
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
            ):
                dx = (event.pos[0] - offset_x) / scale_factor
                dy = (event.pos[1] - offset_y) / scale_factor
                event.pos = (int(dx), int(dy))
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_RETURN:
                    level_idx = _try_parse_level(menu_renderer.level_input_text)
                    if level_idx is not None:
                        return f"level:{level_idx}"
                if event.key == pygame.K_BACKSPACE:
                    menu_renderer.level_input_text = menu_renderer.level_input_text[:-1]
                    menu_renderer.level_input_active = True
                elif event.unicode and event.unicode.isdigit():
                    if len(menu_renderer.level_input_text) < 3:
                        menu_renderer.level_input_text += event.unicode
                        menu_renderer.level_input_active = True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hasattr(
                    menu_renderer, "level_input_rect"
                ) and menu_renderer.level_input_rect.collidepoint(event.pos):
                    menu_renderer.level_input_active = True
                else:
                    menu_renderer.level_input_active = False
                result = menu_renderer.handle_level_select_click(event.pos)
                if result and result.startswith("level:"):
                    return result
                if result == "go":
                    level_idx = _try_parse_level(menu_renderer.level_input_text)
                    if level_idx is not None:
                        return f"level:{level_idx}"
                if result == "back":
                    return None
            if event.type == pygame.MOUSEMOTION:
                menu_renderer.handle_level_select_hover(event.pos)

        menu_renderer.draw_level_select(game_id, total_levels, level_manager)
        _scale_and_present()
        clock.tick(FPS)


def _start_game(game_id, resume, game_manager, level_manager):
    """Start a game session, optionally resuming from saved progress."""
    if not game_manager.start_game(game_id):
        return False

    if resume == "continue":
        if level_manager.is_fully_completed(game_id):
            current_level = level_manager.get_current_level(game_id)
            if current_level is not None and current_level > 0:
                game_manager.jump_to_level(current_level)
        else:
            next_level = level_manager.get_next_uncompleted_level(game_id)
            if next_level and next_level > 0:
                game_manager.jump_to_level(next_level)
    elif isinstance(resume, str) and resume.startswith("level:"):
        level_index = int(resume.split(":")[1])
        game_manager.jump_to_level(level_index)
        level_manager.set_current_level(game_id, level_index)
    elif resume == "new" and level_manager.is_fully_completed(game_id):
        level_manager.set_current_level(game_id, 0)
    return True


def _handle_win(game_manager, level_manager, stats_manager, level_index, session_id):
    """Handle the level-complete event: save progress, record stats."""
    steps = game_manager.step_count
    time_ms = game_manager.get_elapsed_ms()

    level_manager.update_level_status(
        game_manager.game_id,
        level_index,
        steps,
        time_ms,
    )

    if game_manager.max_levels > 0:
        level_manager.update_total_levels(game_manager.game_id, game_manager.max_levels)

    if level_manager.is_fully_completed(game_manager.game_id):
        level_manager.set_current_level(
            game_manager.game_id,
            game_manager.levels_completed,
        )

    stats_manager.record_attempt(
        game_manager.game_id,
        level_index,
        steps,
        time_ms,
        "WIN",
        session_id,
    )


def _ensure_dirs():
    """Create the data directory structure if it does not exist."""
    for d in [DATA_DIR, RECORDS_DIR, RECORDINGS_DIR, PLAYERS_DIR]:
        os.makedirs(d, exist_ok=True)


def main():
    """Entry point: create and run the application."""
    app = App()
    app.run()


if __name__ == "__main__":
    main()
