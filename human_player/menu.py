import os

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.text import Text
from rich.columns import Columns
from rich import box

from human_player.config import WASD_HELP, ARROW_HELP

console = Console()


def show_banner():
    banner = Text()
    banner.append("ARC-AGI-3", style="bold cyan")
    banner.append(" 人类玩家控制台", style="bold white")
    console.print(Panel(banner, box=box.HEAVY, border_style="cyan", padding=(1, 2)))
    console.print()


def show_game_list(games, level_manager) -> str | None:
    if not games:
        console.print("[red]没有找到可用游戏[/red]")
        return None

    table = Table(
        title="可用游戏",
        box=box.ROUNDED,
        show_lines=False,
        border_style="blue",
        title_style="bold blue",
        row_styles=["", "dim"],
    )
    table.add_column("#", style="bold yellow", justify="center", width=4)
    table.add_column("游戏 ID", style="bold cyan", no_wrap=True)
    table.add_column("标题", style="white", width=10)
    table.add_column("标签", style="dim", width=16)
    table.add_column("进度", width=16)

    for i, game in enumerate(games, 1):
        gid = game.game_id
        short_id = gid.split("-")[0] if "-" in gid else gid
        title = getattr(game, 'title', "")
        tags = ", ".join(getattr(game, 'tags', []))

        completed = level_manager.get_completed_count(gid)
        total = level_manager.get_total_levels(gid)

        if total > 0:
            bar = _progress_bar(completed, total, width=8)
            progress_text = f"{bar} {completed}/{total}"
        elif completed > 0:
            progress_text = f"✓ {completed} 关"
        else:
            progress_text = "[dim]—[/dim]"

        table.add_row(str(i), short_id, title, tags, progress_text)

    console.print(table)
    console.print(f"  [dim]共 {len(games)} 个游戏[/dim]")
    console.print()

    choices = [str(i) for i in range(1, len(games) + 1)] + ["s", "v", "q"]
    choice = Prompt.ask(
        "[bold]选择序号[/bold] | [yellow]S[/yellow]设置 | [yellow]V[/yellow]成绩 | [yellow]Q[/yellow]退出",
        choices=choices,
        default="q",
    )

    if choice == "q":
        return None
    elif choice == "s":
        return "SETTINGS"
    elif choice == "v":
        return "STATS"
    else:
        idx = int(choice) - 1
        return games[idx].game_id


def show_stats(games, level_manager, stats_manager):
    console.print()
    console.rule("[bold blue]成绩统计", style="blue")

    for game in games:
        gid = game.game_id
        title = getattr(game, 'title', gid)
        summary = stats_manager.get_game_summary(gid)
        completed = level_manager.get_completed_count(gid)
        total = level_manager.get_total_levels(gid)

        panel_content = Text()
        panel_content.append(f"总尝试: {summary['total_attempts']}  ", style="white")
        panel_content.append(f"胜利: {summary['total_wins']}  ", style="green")
        panel_content.append(f"完成关卡: {completed}", style="cyan")
        if total > 0:
            panel_content.append(f"/{total}", style="dim")
        if summary.get("best_steps"):
            panel_content.append(f"  最佳步数: {summary['best_steps']}", style="yellow")

        console.print(Panel(panel_content, title=f"[bold]{gid}[/bold] - {title}",
                            border_style="green", padding=(0, 2)))

        level_details = _get_level_details(gid, level_manager, stats_manager)
        if level_details:
            lt = Table(box=box.SIMPLE, show_header=True, padding=(0, 2))
            lt.add_column("关卡", style="dim", width=6)
            lt.add_column("状态", width=8)
            lt.add_column("最佳步数", justify="right", width=10)
            lt.add_column("最佳时间", justify="right", width=12)
            lt.add_column("尝试次数", justify="right", width=8)
            for row in level_details:
                lt.add_row(*row)
            console.print(lt)

    console.print()
    Prompt.ask("[dim]按回车返回[/dim]", default="")


def show_settings(current_keymap: str) -> dict:
    console.print()
    console.rule("[bold blue]设置", style="blue")

    table = Table(box=box.ROUNDED, border_style="yellow", show_lines=True)
    table.add_column("选项", style="bold", width=12)
    table.add_column("当前值", width=20)
    table.add_column("说明", style="dim", width=40)

    keymap_display = "WASD + Space" if current_keymap == "wasd" else "方向键 + F"
    table.add_row("键位方案", keymap_display, "WASD 或 方向键")
    table.add_row("渲染模式", "terminal", "内置终端渲染")

    console.print(table)
    console.print()

    console.print("[bold]WASD 方案:[/bold]")
    for k, v in WASD_HELP.items():
        console.print(f"  [cyan]{k:8s}[/cyan] → {v}")

    console.print()
    console.print("[bold]方向键方案:[/bold]")
    for k, v in ARROW_HELP.items():
        console.print(f"  [cyan]{k:8s}[/cyan] → {v}")

    console.print()
    choice = Prompt.ask(
        "切换键位方案",
        choices=["w", "a", "q"],
        default="q",
    )

    if choice == "w":
        return {"keymap": "wasd"}
    elif choice == "a":
        return {"keymap": "arrows"}
    return {}


def show_game_hud(game_id: str, step_count: int, levels_completed: int,
                  max_levels: int, elapsed_ms: int, available_actions: list,
                  keymap_scheme: str):
    elapsed_s = elapsed_ms // 1000
    minutes = elapsed_s // 60
    seconds = elapsed_s % 60

    level_info = f"关卡 {levels_completed + 1}"
    if max_levels > 0:
        level_info += f"/{max_levels}"

    action_names = []
    for a in available_actions:
        label = _action_short_label(a, keymap_scheme)
        action_names.append(label)

    scheme_name = "WASD" if keymap_scheme == "wasd" else "方向键"

    hud = Text()
    hud.append(f" {game_id} ", style="bold cyan on black")
    hud.append(f" │ {level_info} ", style="bold white")
    hud.append(f" │ 步数: {step_count} ", style="yellow")
    hud.append(f" │ ⏱ {minutes:02d}:{seconds:02d} ", style="green")
    hud.append(f" │ {scheme_name} ", style="dim")

    console.print(Panel(hud, box=box.SQUARE, border_style="dim", padding=(0, 1)))

    actions_text = "  ".join(f"[{n}]" for n in action_names)
    console.print(f"  可用: {actions_text}  [q]退出  [c]输入坐标", style="dim")


def show_level_complete(level_index: int, steps: int, time_ms: int,
                        best_steps: int | None, best_time: int | None):
    elapsed_s = time_ms // 1000
    minutes = elapsed_s // 60
    seconds = elapsed_s % 60

    content = Text()
    content.append(f"关卡 {level_index + 1} 通过！\n", style="bold green")
    content.append(f"  步数: {steps}  ", style="yellow")
    content.append(f"  用时: {minutes:02d}:{seconds:02d}\n", style="cyan")

    if best_steps and steps <= best_steps:
        content.append("  ★ 新纪录！\n", style="bold yellow")
    elif best_steps:
        content.append(f"  最佳: {best_steps}步\n", style="dim")

    console.print(Panel(content, border_style="green", title="✓ 关卡完成", padding=(0, 2)))


def show_game_over(step_count: int):
    content = Text()
    content.append("游戏结束\n", style="bold red")
    content.append(f"  总步数: {step_count}\n", style="yellow")
    content.append("  按 [R] 重置  [Q] 退出", style="dim")
    console.print(Panel(content, border_style="red", title="✗ GAME OVER", padding=(0, 2)))


def show_all_complete(game_id: str, total_steps: int, total_time_ms: int):
    elapsed_s = total_time_ms // 1000
    minutes = elapsed_s // 60
    seconds = elapsed_s % 60

    content = Text()
    content.append(f"游戏 {game_id} 全部通关！\n\n", style="bold green")
    content.append(f"  总步数: {total_steps}\n", style="yellow")
    content.append(f"  总用时: {minutes:02d}:{seconds:02d}\n", style="cyan")
    console.print(Panel(content, border_style="green", title="🎉 恭喜通关", padding=(0, 2)))


def show_resume_prompt(game_id: str, completed: int, total: int,
                       next_level: int, has_recording: bool) -> str | None:
    content = Text()
    content.append(f"检测到已有进度: ", style="white")
    bar = _progress_bar(completed, total, width=8) if total > 0 else ""
    if total > 0:
        content.append(f"{bar} {completed}/{total}\n", style="cyan")
    else:
        content.append(f"✓ {completed} 关\n", style="cyan")
    content.append(f"上次完成到第 {completed} 关，下一关为第 {next_level + 1} 关\n\n", style="white")

    if has_recording:
        content.append("[C] ", style="bold green")
        content.append("继续上次 — 自动回放已通关关卡，跳到第 ", style="green")
        content.append(f"{next_level + 1}", style="bold green")
        content.append(" 关\n", style="green")
    else:
        content.append("[C] ", style="bold yellow")
        content.append("继续 — 从第 1 关开始（无录像，无法自动跳关）\n", style="yellow")

    content.append("[N] ", style="bold cyan")
    content.append("从头开始 — 从第 1 关重新打（进度记录保留）\n", style="cyan")
    content.append("[Q] ", style="bold dim")
    content.append("返回\n", style="dim")

    console.print(Panel(content, border_style="yellow",
                        title="📋 发现存档进度", padding=(0, 2)))

    choices = ["c", "n", "q"]
    choice = Prompt.ask(
        "选择",
        choices=choices,
        default="c" if has_recording else "n",
    )

    if choice == "c":
        return "continue"
    elif choice == "n":
        return "new"
    return None


def show_auto_advance_progress(level_idx: int, total_actions: int):
    console.print(f"  [dim]回放关卡 {level_idx + 1}（{total_actions} 步）...[/dim]", end="")


def show_auto_advance_done(level_idx: int):
    console.print(" [green]✓[/green]")


def show_auto_advance_fail(level_idx: int, step: int, reason: str):
    console.print(f" [red]✗[/red]")
    console.print(f"  [yellow]回放失败（关卡 {level_idx + 1}，第 {step + 1} 步: {reason}）[/yellow]")
    console.print(f"  [dim]将从当前关卡开始手动游玩[/dim]")


def _progress_bar(completed: int, total: int, width: int = 10) -> str:
    if total == 0:
        return "░" * width
    filled = int(width * completed / total)
    return "█" * filled + "░" * (width - filled)


def _get_overall_best(level_manager, game_id: str) -> int | None:
    game = level_manager.get_game_progress(game_id)
    best = None
    for level_data in game.get("levels", {}).values():
        if level_data.get("completed") and level_data.get("best_steps"):
            if best is None or level_data["best_steps"] < best:
                best = level_data["best_steps"]
    return best


def _get_level_details(game_id: str, level_manager, stats_manager) -> list[list[str]]:
    game = level_manager.get_game_progress(game_id)
    rows = []
    for level_key, level_data in sorted(game.get("levels", {}).items(), key=lambda x: int(x[0])):
        idx = int(level_key)
        stats = stats_manager.get_level_stats(game_id, idx)

        if level_data.get("completed"):
            status = "[green]✓ 通过[/green]"
        else:
            status = "[dim]未通过[/dim]"

        best_steps = str(level_data.get("best_steps", "-"))
        best_time_ms = level_data.get("best_time_ms")
        if best_time_ms is not None:
            t = best_time_ms // 1000
            best_time = f"{t // 60:02d}:{t % 60:02d}"
        else:
            best_time = "-"

        attempts = str(stats.get("attempts", 0))
        rows.append([f"L{idx + 1}", status, best_steps, best_time, attempts])

    return rows


def _action_short_label(action, keymap_scheme: str) -> str:
    from arcengine import GameAction
    from human_player.config import KEYMAP_WASD, KEYMAP_ARROWS

    keymap = KEYMAP_WASD if keymap_scheme == "wasd" else KEYMAP_ARROWS

    for key, act in keymap.items():
        if act == action:
            display = key if key.strip() else "Space"
            return f"{display}={action.name.replace('ACTION', 'A')}"

    for key, act in KEYMAP_WASD.items():
        if act == action:
            return f"{key}={action.name.replace('ACTION', 'A')}"

    return action.name
