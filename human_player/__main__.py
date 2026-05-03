import os
import sys
import time

import pygame
from arcengine import GameAction, GameState

from human_player.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS,
    get_keymap, get_keymap_scheme, set_keymap_scheme,
    DATA_DIR, RECORDS_DIR, RECORDINGS_DIR, PLAYERS_DIR,
)
from human_player.game_manager import GameManager
from human_player.level_manager import LevelManager
from human_player.stats_manager import StatsManager
from human_player.recording import RecordingManager
from human_player.official_recording import OfficialRecordingManager
from human_player.player_manager import PlayerManager
from human_player.renderer import Renderer
from human_player.menu import MenuRenderer


def main():
    _ensure_dirs()

    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("ARC-AGI-3 Human Player")
    clock = pygame.time.Clock()

    game_manager = GameManager()
    renderer = Renderer(screen)
    menu_renderer = MenuRenderer(screen)

    player_manager = PlayerManager()
    level_manager = LevelManager(progress_file=player_manager.get_progress_file())
    stats_manager = StatsManager(records_dir=player_manager.get_records_dir())
    recording_manager = RecordingManager()
    official_recording = OfficialRecordingManager(player_manager)

    state = "MAIN_MENU"
    keymap_scheme = get_keymap_scheme()
    games = game_manager.list_games()

    current_level = 0
    game_over_recorded = False
    overlay_state = None
    session_id = None
    player_input_text = ""
    player_input_active = False

    def _switch_player(name):
        nonlocal level_manager, stats_manager, games
        player_manager.set_player(name)
        level_manager.set_progress_file(player_manager.get_progress_file())
        stats_manager.set_records_dir(player_manager.get_records_dir())
        games = game_manager.list_games()

    try:
        while True:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if state == "MAIN_MENU":
                    result = _handle_menu_event(event, menu_renderer, games)
                    if result is None:
                        pygame.quit()
                        sys.exit()
                    elif result == "settings":
                        state = "SETTINGS"
                    elif result == "stats":
                        state = "STATS"
                    elif result == "player":
                        state = "PLAYER_SELECT"
                        player_input_text = ""
                        player_input_active = False
                    elif isinstance(result, str) and result.startswith("game:"):
                        idx = int(result.split(":")[1])
                        if idx < len(games):
                            game_id = games[idx].game_id
                            resume = _check_resume(
                                game_id, level_manager, menu_renderer, screen, clock,
                            )
                            if resume is None:
                                continue
                            if _start_game(
                                game_id, resume, game_manager, level_manager,
                            ):
                                state = "GAME"
                                current_level = game_manager.levels_completed
                                game_over_recorded = False
                                overlay_state = None
                                session_id = recording_manager.start_session(game_id)
                                levels_at_start = game_manager.levels_completed
                                official_recording.start_session(
                                    game_id,
                                    game_manager.max_levels,
                                    levels_at_start,
                                )

                elif state == "SETTINGS":
                    result = _handle_settings_event(event, menu_renderer, keymap_scheme)
                    if result == "back":
                        state = "MAIN_MENU"
                    elif result in ("wasd", "arrows"):
                        keymap_scheme = result
                        set_keymap_scheme(result)

                elif state == "STATS":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        state = "MAIN_MENU"
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        btn = menu_renderer.handle_button_click(event.pos)
                        if btn == "back":
                            state = "MAIN_MENU"

                elif state == "PLAYER_SELECT":
                    result = _handle_player_event(
                        event, menu_renderer, player_manager, player_input_text,
                    )
                    if result == "back":
                        state = "MAIN_MENU"
                    elif result == "create":
                        name = player_input_text.strip()
                        if name:
                            _switch_player(name)
                            player_input_text = ""
                            state = "MAIN_MENU"
                    elif isinstance(result, str) and result.startswith("select:"):
                        name = result.split(":", 1)[1]
                        _switch_player(name)
                        state = "MAIN_MENU"
                    elif isinstance(result, str) and result.startswith("input:"):
                        player_input_text = result.split(":", 1)[1]
                        player_input_active = True

                elif state == "GAME":
                    action_result = _handle_game_event(
                        event, game_manager, renderer,
                    )
                    if action_result == "exit":
                        final_state = "NOT_FINISHED"
                        if game_manager.env:
                            obs = game_manager.env.observation_space
                            if obs and hasattr(obs, 'state'):
                                final_state = obs.state.name
                        recording_manager.end_session()
                        if official_recording.is_recording:
                            official_recording.end_session(final_state)
                        game_manager.close_game()
                        state = "MAIN_MENU"
                        games = game_manager.list_games()
                        continue

                    if action_result and overlay_state is None:
                        action, data = action_result
                        available = game_manager.env.action_space if game_manager.env else []
                        if action in available or action == GameAction.RESET:
                            obs = game_manager.execute_action(action, data)
                            recording_manager.record_step(
                                action, data, obs,
                                game_manager.step_count, game_manager.get_elapsed_ms(),
                            )
                            official_recording.record_step(
                                action, data, obs, available,
                            )

                            if game_manager.did_level_up():
                                current_level = game_manager.levels_completed - 1
                                _handle_win(
                                    game_manager, level_manager, stats_manager,
                                    session_id, current_level,
                                )
                                current_level = game_manager.levels_completed
                                game_over_recorded = False

                            if obs and obs.state == GameState.WIN:
                                overlay_state = "win"
                            elif obs and obs.state == GameState.GAME_OVER:
                                if not game_over_recorded:
                                    stats_manager.record_attempt(
                                        game_manager.game_id, current_level,
                                        game_manager.step_count, game_manager.get_elapsed_ms(),
                                        "GAME_OVER", session_id,
                                    )
                                    game_over_recorded = True
                                overlay_state = "game_over"

                    if overlay_state and event.type == pygame.KEYDOWN:
                        if overlay_state == "win":
                            if (game_manager.max_levels > 0
                                    and game_manager.levels_completed >= game_manager.max_levels):
                                overlay_state = "all_complete"
                            else:
                                overlay_state = None
                                game_manager.env.reset()
                                game_manager.step_count = 0
                                game_manager.level_start_time = time.time()
                                game_over_recorded = False
                        elif overlay_state == "game_over":
                            if event.key == pygame.K_r:
                                overlay_state = None
                                game_manager.reset_level()
                                game_over_recorded = False
                        elif overlay_state == "all_complete":
                            recording_manager.end_session()
                            if official_recording.is_recording:
                                official_recording.end_session("WIN")
                            game_manager.close_game()
                            state = "MAIN_MENU"
                            games = game_manager.list_games()
                            overlay_state = None
                            continue

            if state == "MAIN_MENU":
                menu_renderer.handle_main_menu_hover(mouse_pos)
                menu_renderer.draw_main_menu(
                    games, level_manager, keymap_scheme,
                    player_manager.get_current_player(),
                )

            elif state == "SETTINGS":
                menu_renderer.draw_settings(keymap_scheme)

            elif state == "STATS":
                menu_renderer.draw_stats(games, level_manager, stats_manager)

            elif state == "PLAYER_SELECT":
                players = player_manager.list_players()
                menu_renderer.draw_player_select(
                    players, player_manager.get_current_player(),
                    player_input_text, player_input_active,
                )

            elif state == "GAME":
                frame = game_manager.get_current_frame()
                grid_pos = renderer.pixel_to_grid(*mouse_pos)
                available = game_manager.env.action_space if game_manager.env else []

                renderer.draw_frame(
                    frame, grid_pos,
                    game_manager.step_count, game_manager.get_elapsed_ms(),
                    game_manager.levels_completed, game_manager.max_levels,
                    available, keymap_scheme, game_manager.game_id,
                )

                if overlay_state == "win":
                    best_steps = level_manager.get_best_steps(game_manager.game_id, current_level)
                    best_time = level_manager.get_best_time_ms(game_manager.game_id, current_level)
                    renderer.draw_overlay_win(
                        current_level, game_manager.step_count, game_manager.get_elapsed_ms(),
                        best_steps, best_time,
                    )
                elif overlay_state == "game_over":
                    renderer.draw_overlay_game_over(game_manager.step_count)
                elif overlay_state == "all_complete":
                    renderer.draw_overlay_all_complete(
                        game_manager.game_id, game_manager.total_steps,
                        game_manager.get_total_elapsed_ms(),
                    )

            pygame.display.flip()
            clock.tick(FPS)

    except Exception as e:
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)


def _handle_menu_event(event, menu_renderer, games):
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_q:
            return None
        if event.key == pygame.K_s:
            return "settings"
        if event.key == pygame.K_v:
            return "stats"
        if event.key == pygame.K_p:
            return "player"
        if pygame.K_1 <= event.key <= pygame.K_9:
            idx = event.key - pygame.K_1
            if idx < len(games):
                return f"game:{idx}"
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return menu_renderer.handle_main_menu_click(event.pos)
    return False


def _handle_settings_event(event, menu_renderer, keymap_scheme):
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return "back"
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        btn = menu_renderer.handle_button_click(event.pos)
        if btn in ("wasd", "arrows"):
            return btn
        if btn == "back":
            return "back"
    return False


def _handle_player_event(event, menu_renderer, player_manager, input_text):
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
        result = menu_renderer.handle_player_click(event.pos, players)
        if result:
            return result
    return False


def _handle_game_event(event, game_manager, renderer):
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return "exit"
        keymap = get_keymap()
        if event.key in keymap:
            return (keymap[event.key], None)

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        gx, gy = renderer.pixel_to_grid(*event.pos)
        if gx is not None and gy is not None:
            available = game_manager.env.action_space if game_manager.env else []
            if GameAction.ACTION6 in available:
                return (GameAction.ACTION6, {"x": gx, "y": gy})

    return False


def _check_resume(game_id, level_manager, menu_renderer, screen, clock):
    completed = level_manager.get_completed_count(game_id)
    next_level = level_manager.get_next_uncompleted_level(game_id)
    total = level_manager.get_total_levels(game_id)

    if completed == 0 or next_level is None:
        return "new"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
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
        pygame.display.flip()
        clock.tick(FPS)


def _start_game(game_id, resume, game_manager, level_manager):
    if not game_manager.start_game(game_id):
        return False

    if resume == "continue":
        next_level = level_manager.get_next_uncompleted_level(game_id)
        if next_level and next_level > 0:
            game_manager.jump_to_level(next_level)
    return True


def _handle_win(game_manager, level_manager, stats_manager,
                session_id, level_index):
    steps = game_manager.step_count
    time_ms = game_manager.get_elapsed_ms()

    level_manager.update_level_status(
        game_manager.game_id, level_index, steps, time_ms,
    )

    if game_manager.max_levels > 0:
        level_manager.update_total_levels(game_manager.game_id, game_manager.max_levels)

    stats_manager.record_attempt(
        game_manager.game_id, level_index, steps, time_ms, "WIN", session_id,
    )


def _ensure_dirs():
    for d in [DATA_DIR, RECORDS_DIR, RECORDINGS_DIR, PLAYERS_DIR]:
        os.makedirs(d, exist_ok=True)


if __name__ == "__main__":
    main()
