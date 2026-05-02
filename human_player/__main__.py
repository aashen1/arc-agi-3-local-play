import msvcrt
import os
import sys
import time

from arcengine import GameAction, GameState

from human_player.config import (
    KEYMAP_WASD, KEYMAP_ARROWS, DATA_DIR, RECORDS_DIR, RECORDINGS_DIR,
)
from human_player.game_manager import GameManager
from human_player.level_manager import LevelManager
from human_player.stats_manager import StatsManager
from human_player.recording import RecordingManager
from human_player import menu


class GameExitException(Exception):
    pass


def main():
    _ensure_dirs()

    keymap_scheme = "wasd"
    game_manager = GameManager()
    level_manager = LevelManager()
    stats_manager = StatsManager()
    recording_manager = RecordingManager()

    while True:
        menu.show_banner()
        games = game_manager.list_games()

        choice = menu.show_game_list(games, level_manager)

        if choice is None:
            menu.console.print("[dim]再见！[/dim]")
            break
        elif choice == "SETTINGS":
            result = menu.show_settings(keymap_scheme)
            if "keymap" in result:
                keymap_scheme = result["keymap"]
            continue
        elif choice == "STATS":
            menu.show_stats(games, level_manager, stats_manager)
            continue

        game_id = choice

        completed = level_manager.get_completed_count(game_id)
        next_level = level_manager.get_next_uncompleted_level(game_id)
        total = level_manager.get_total_levels(game_id)

        resume_choice = None
        if completed > 0 and next_level is not None:
            has_recording = recording_manager.find_best_recording(game_id) is not None
            resume_choice = menu.show_resume_prompt(
                game_id, completed, total, next_level, has_recording,
            )

        if resume_choice is None and completed > 0 and next_level is not None:
            continue

        menu.console.print(f"\n[cyan]正在启动 {game_id}...[/cyan]")

        if not game_manager.start_game(game_id):
            menu.console.print(f"[red]启动游戏 {game_id} 失败[/red]")
            continue

        session_id = recording_manager.start_session(game_id)

        if resume_choice == "continue" and next_level is not None and next_level > 0:
            _try_auto_advance(
                game_manager, level_manager, recording_manager,
                session_id, game_id, next_level,
            )

        try:
            _game_loop(
                game_manager, level_manager, stats_manager,
                recording_manager, keymap_scheme, session_id,
            )
        except GameExitException:
            pass
        except KeyboardInterrupt:
            menu.console.print("\n[yellow]中断，正在保存...[/yellow]")
        finally:
            recording_manager.end_session()
            game_manager.close_game()
            menu.console.print("[dim]已返回主菜单[/dim]\n")


def _try_auto_advance(game_manager: GameManager, level_manager: LevelManager,
                       recording_manager: RecordingManager, session_id: str,
                       game_id: str, target_level: int):
    level_actions = recording_manager.extract_winning_sequences(game_id)
    if not level_actions:
        menu.console.print("[yellow]未找到可回放的录像，将从第 1 关开始[/yellow]")
        return

    needed = {k: v for k, v in level_actions.items() if k < target_level}
    if not needed:
        menu.console.print("[yellow]录像中无已通关关卡数据，将从第 1 关开始[/yellow]")
        return

    menu.console.print(f"[cyan]正在回放 {len(needed)} 个已通关关卡...[/cyan]")

    advanced = game_manager.auto_advance(
        needed,
        on_level_start=menu.show_auto_advance_progress,
        on_level_done=menu.show_auto_advance_done,
        on_fail=menu.show_auto_advance_fail,
    )

    if advanced > 0:
        menu.console.print(
            f"[green]已自动推进 {advanced} 关，当前: 第 {game_manager.levels_completed + 1} 关[/green]"
        )
    else:
        menu.console.print("[yellow]自动推进失败，将从第 1 关开始手动游玩[/yellow]")


def _game_loop(game_manager: GameManager, level_manager: LevelManager,
               stats_manager: StatsManager, recording_manager: RecordingManager,
               keymap_scheme: str, session_id: str):

    keymap = KEYMAP_WASD if keymap_scheme == "wasd" else KEYMAP_ARROWS
    current_level = game_manager.levels_completed
    game_over_recorded = False

    _print_keymap_hint(keymap_scheme)

    while True:
        obs = game_manager.env.observation_space if game_manager.env else None
        if obs is None:
            time.sleep(0.05)
            continue

        if obs.state == GameState.WIN:
            _handle_win(
                game_manager, level_manager, stats_manager,
                recording_manager, session_id, current_level,
            )
            current_level = game_manager.levels_completed

            if game_manager.max_levels > 0 and current_level >= game_manager.max_levels:
                menu.show_all_complete(
                    game_manager.game_id,
                    game_manager.total_steps,
                    game_manager.get_total_elapsed_ms(),
                )
                time.sleep(2)
                raise GameExitException()

            menu.console.print("[dim]进入下一关...[/dim]")
            time.sleep(0.5)
            obs = game_manager.env.reset()
            game_manager.step_count = 0
            game_manager.level_start_time = time.time()
            game_over_recorded = False
            continue

        if obs.state == GameState.GAME_OVER:
            if not game_over_recorded:
                menu.show_game_over(game_manager.step_count)
                stats_manager.record_attempt(
                    game_manager.game_id, current_level,
                    game_manager.step_count, game_manager.get_elapsed_ms(),
                    "GAME_OVER", session_id,
                )
                game_over_recorded = True

        key = _read_key()
        if key is None:
            time.sleep(0.02)
            continue

        if key in ('q', 'Q'):
            raise GameExitException()

        if key in ('c', 'C'):
            _handle_coordinate_input(game_manager, recording_manager, session_id)
            continue

        if key in ('h', 'H'):
            _print_keymap_hint(keymap_scheme)
            continue

        action = None
        if key in keymap:
            action = keymap[key]
        elif key == '\x00' or key == '\xe0':
            ext = msvcrt.getwch()
            ext_key = '\x00' + ext
            if ext_key in keymap:
                action = keymap[ext_key]

        if action is None:
            continue

        available = game_manager.env.action_space if game_manager.env else []
        if action not in available and action != GameAction.RESET:
            continue

        obs = game_manager.execute_action(action)

        recording_manager.record_step(
            action, None, obs,
            game_manager.step_count, game_manager.get_elapsed_ms(),
        )

        if game_manager.did_level_up():
            current_level = game_manager.levels_completed - 1
            _handle_win(
                game_manager, level_manager, stats_manager,
                recording_manager, session_id, current_level,
            )
            current_level = game_manager.levels_completed
            game_over_recorded = False


def _handle_win(game_manager: GameManager, level_manager: LevelManager,
                stats_manager: StatsManager, recording_manager: RecordingManager,
                session_id: str, level_index: int):
    steps = game_manager.step_count
    time_ms = game_manager.get_elapsed_ms()

    best_steps = level_manager.get_best_steps(game_manager.game_id, level_index)
    best_time = level_manager.get_best_time_ms(game_manager.game_id, level_index)

    menu.show_level_complete(level_index, steps, time_ms, best_steps, best_time)

    level_manager.update_level_status(
        game_manager.game_id, level_index, steps, time_ms,
    )

    if game_manager.max_levels > 0:
        level_manager.update_total_levels(game_manager.game_id, game_manager.max_levels)

    stats_manager.record_attempt(
        game_manager.game_id, level_index, steps, time_ms, "WIN", session_id,
    )


def _handle_coordinate_input(game_manager: GameManager,
                              recording_manager: RecordingManager,
                              session_id: str):
    available = game_manager.env.action_space if game_manager.env else []
    if GameAction.ACTION6 not in available:
        menu.console.print("[dim]ACTION6 当前不可用[/dim]")
        return

    menu.console.print("[cyan]输入坐标 (格式: x,y 或 x y):[/cyan] ", end="")

    try:
        line = input().strip()
        parts = line.replace(",", " ").split()
        if len(parts) != 2:
            menu.console.print("[red]格式错误，需要 x,y[/red]")
            return

        x, y = int(parts[0]), int(parts[1])
        if not (0 <= x < 64 and 0 <= y < 64):
            menu.console.print("[red]坐标超出范围 (0-63)[/red]")
            return

        obs = game_manager.execute_action(GameAction.ACTION6, data={"x": x, "y": y})
        recording_manager.record_step(
            GameAction.ACTION6, {"x": x, "y": y}, obs,
            game_manager.step_count, game_manager.get_elapsed_ms(),
        )
    except (ValueError, IndexError):
        menu.console.print("[red]无效输入[/red]")
    except EOFError:
        pass


def _print_keymap_hint(keymap_scheme: str):
    from human_player.config import WASD_HELP, ARROW_HELP
    help_map = WASD_HELP if keymap_scheme == "wasd" else ARROW_HELP
    menu.console.print("\n[bold]操作提示:[/bold]")
    for k, v in help_map.items():
        menu.console.print(f"  [cyan]{k:8s}[/cyan] → {v}")
    menu.console.print()


def _read_key() -> str | None:
    try:
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch == '\x03':
                raise KeyboardInterrupt()
            return ch
    except KeyboardInterrupt:
        raise
    return None


def _ensure_dirs():
    for d in [DATA_DIR, RECORDS_DIR, RECORDINGS_DIR]:
        os.makedirs(d, exist_ok=True)


if __name__ == "__main__":
    main()
