import pygame

from human_player.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    COLOR_BG, COLOR_PANEL, COLOR_TEXT, COLOR_TEXT_DIM,
    COLOR_HIGHLIGHT, COLOR_WIN, COLOR_GAMEOVER, COLOR_ACCENT,
    ACTION_LABELS, get_keymap_scheme, get_key_labels,
)


class MenuRenderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font_title = pygame.font.SysFont("consolas", 32, bold=True)
        self.font_large = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_medium = pygame.font.SysFont("consolas", 16)
        self.font_small = pygame.font.SysFont("consolas", 13)
        self.hover_index = -1
        self.game_rects = []
        self.button_rects = {}

    def draw_main_menu(self, games, level_manager, keymap_scheme):
        self.screen.fill(COLOR_BG)
        self.game_rects = []
        self.button_rects = {}

        title = self.font_title.render("ARC-AGI-3", True, COLOR_ACCENT)
        subtitle = self.font_medium.render("Human Player Console", True, COLOR_TEXT_DIM)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 20))
        self.screen.blit(subtitle, (WINDOW_WIDTH // 2 - subtitle.get_width() // 2, 58))

        y = 100
        for i, game in enumerate(games):
            gid = game.game_id
            title_str = getattr(game, 'title', gid)
            tags = ", ".join(getattr(game, 'tags', []))
            completed = level_manager.get_completed_count(gid)
            total = level_manager.get_total_levels(gid)

            rect = pygame.Rect(40, y, WINDOW_WIDTH - 80, 52)
            self.game_rects.append(rect)

            bg_color = (50, 50, 70) if i == self.hover_index else COLOR_PANEL
            pygame.draw.rect(self.screen, bg_color, rect, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_ACCENT, rect, 1, border_radius=6)

            idx_text = self.font_large.render(f"{i + 1}", True, COLOR_HIGHLIGHT)
            self.screen.blit(idx_text, (rect.x + 12, rect.y + 14))

            name_text = self.font_medium.render(f"{gid} - {title_str}", True, COLOR_TEXT)
            self.screen.blit(name_text, (rect.x + 50, rect.y + 8))

            if total > 0:
                prog = f"{completed}/{total}"
            elif completed > 0:
                prog = f"{completed} done"
            else:
                prog = "--"
            prog_text = self.font_small.render(prog, True, COLOR_TEXT_DIM)
            self.screen.blit(prog_text, (rect.x + 50, rect.y + 30))

            if tags:
                tag_text = self.font_small.render(tags, True, COLOR_TEXT_DIM)
                self.screen.blit(tag_text, (rect.right - tag_text.get_width() - 12, rect.y + 18))

            y += 60

        btn_y = WINDOW_HEIGHT - 50
        settings_rect = pygame.Rect(40, btn_y, 120, 36)
        stats_rect = pygame.Rect(180, btn_y, 120, 36)
        quit_rect = pygame.Rect(WINDOW_WIDTH - 160, btn_y, 120, 36)
        self.button_rects = {
            "settings": settings_rect,
            "stats": stats_rect,
            "quit": quit_rect,
        }

        for name, rect in self.button_rects.items():
            pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_ACCENT, rect, 1, border_radius=4)
            labels = {"settings": "[S] Settings", "stats": "[V] Stats", "quit": "[Q] Quit"}
            lbl = self.font_small.render(labels[name], True, COLOR_TEXT)
            self.screen.blit(lbl, (rect.x + rect.w // 2 - lbl.get_width() // 2,
                                   rect.y + rect.h // 2 - lbl.get_height() // 2))

        hint = self.font_small.render(
            "Click a game or press number key to start", True, COLOR_TEXT_DIM,
        )
        self.screen.blit(hint, (WINDOW_WIDTH // 2 - hint.get_width() // 2, WINDOW_HEIGHT - 85))

    def handle_main_menu_click(self, pos) -> str | None:
        for i, rect in enumerate(self.game_rects):
            if rect.collidepoint(pos):
                return f"game:{i}"
        for name, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                return name
        return None

    def handle_main_menu_hover(self, pos):
        self.hover_index = -1
        for i, rect in enumerate(self.game_rects):
            if rect.collidepoint(pos):
                self.hover_index = i
                break

    def draw_stats(self, games, level_manager, stats_manager):
        self.screen.fill(COLOR_BG)
        self.button_rects = {}

        title = self.font_large.render("Statistics", True, COLOR_ACCENT)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 20))

        y = 70
        for game in games:
            gid = game.game_id
            title_str = getattr(game, 'title', gid)
            summary = stats_manager.get_game_summary(gid)
            completed = level_manager.get_completed_count(gid)
            total = level_manager.get_total_levels(gid)

            panel_rect = pygame.Rect(30, y, WINDOW_WIDTH - 60, 70)
            pygame.draw.rect(self.screen, COLOR_PANEL, panel_rect, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_WIN, panel_rect, 1, border_radius=6)

            name = self.font_medium.render(f"{gid} - {title_str}", True, COLOR_TEXT)
            self.screen.blit(name, (panel_rect.x + 12, panel_rect.y + 8))

            info_parts = [f"Attempts: {summary['total_attempts']}",
                          f"Wins: {summary['total_wins']}",
                          f"Levels: {completed}"]
            if total > 0:
                info_parts[-1] += f"/{total}"
            if summary.get("best_steps"):
                info_parts.append(f"Best: {summary['best_steps']} steps")
            info = self.font_small.render("  ".join(info_parts), True, COLOR_TEXT_DIM)
            self.screen.blit(info, (panel_rect.x + 12, panel_rect.y + 35))

            y += 80

        back_rect = pygame.Rect(WINDOW_WIDTH // 2 - 60, WINDOW_HEIGHT - 50, 120, 36)
        self.button_rects = {"back": back_rect}
        pygame.draw.rect(self.screen, COLOR_PANEL, back_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_ACCENT, back_rect, 1, border_radius=4)
        lbl = self.font_small.render("[ESC] Back", True, COLOR_TEXT)
        self.screen.blit(lbl, (back_rect.x + back_rect.w // 2 - lbl.get_width() // 2,
                               back_rect.y + back_rect.h // 2 - lbl.get_height() // 2))

    def draw_settings(self, keymap_scheme):
        self.screen.fill(COLOR_BG)
        self.button_rects = {}

        title = self.font_large.render("Settings", True, COLOR_ACCENT)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 20))

        y = 80
        keymap_display = "WASD + Space" if keymap_scheme == "wasd" else "Arrows + F"
        label = self.font_medium.render("Keymap Scheme:", True, COLOR_TEXT)
        self.screen.blit(label, (60, y))
        value = self.font_large.render(keymap_display, True, COLOR_HIGHLIGHT)
        self.screen.blit(value, (60, y + 28))

        wasd_rect = pygame.Rect(60, y + 70, 200, 40)
        arrow_rect = pygame.Rect(280, y + 70, 200, 40)
        self.button_rects = {"wasd": wasd_rect, "arrows": arrow_rect}

        for name, rect in self.button_rects.items():
            is_selected = (name == keymap_scheme)
            bg = COLOR_ACCENT if is_selected else COLOR_PANEL
            border = COLOR_HIGHLIGHT if is_selected else COLOR_ACCENT
            pygame.draw.rect(self.screen, bg, rect, border_radius=4)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=4)
            labels = {"wasd": "WASD + Space", "arrows": "Arrows + F"}
            color = COLOR_BG if is_selected else COLOR_TEXT
            lbl = self.font_medium.render(labels[name], True, color)
            self.screen.blit(lbl, (rect.x + rect.w // 2 - lbl.get_width() // 2,
                                   rect.y + rect.h // 2 - lbl.get_height() // 2))

        y += 140
        pygame.draw.line(self.screen, COLOR_TEXT_DIM, (60, y), (WINDOW_WIDTH - 60, y))
        y += 20

        key_labels = get_key_labels()
        header = self.font_medium.render("Key Bindings:", True, COLOR_ACCENT)
        self.screen.blit(header, (60, y))
        y += 28

        for action in [key_labels[k] for k in key_labels]:
            pass

        from arcengine import GameAction
        for action in [GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3,
                       GameAction.ACTION4, GameAction.ACTION5, GameAction.ACTION6,
                       GameAction.ACTION7, GameAction.RESET]:
            key_str = key_labels.get(action, "?")
            action_str = ACTION_LABELS.get(action, action.name)
            line = self.font_small.render(f"  [{key_str}]  {action_str}", True, COLOR_TEXT)
            self.screen.blit(line, (60, y))
            y += 20

        back_rect = pygame.Rect(WINDOW_WIDTH // 2 - 60, WINDOW_HEIGHT - 50, 120, 36)
        self.button_rects["back"] = back_rect
        pygame.draw.rect(self.screen, COLOR_PANEL, back_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_ACCENT, back_rect, 1, border_radius=4)
        lbl = self.font_small.render("[ESC] Back", True, COLOR_TEXT)
        self.screen.blit(lbl, (back_rect.x + back_rect.w // 2 - lbl.get_width() // 2,
                               back_rect.y + back_rect.h // 2 - lbl.get_height() // 2))

    def draw_resume_prompt(self, game_id, completed, total, next_level):
        self.screen.fill(COLOR_BG)
        self.button_rects = {}

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))

        box_w, box_h = 420, 220
        box_x = (WINDOW_WIDTH - box_w) // 2
        box_y = (WINDOW_HEIGHT - box_h) // 2
        pygame.draw.rect(self.screen, COLOR_PANEL, (box_x, box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, (box_x, box_y, box_w, box_h), 2, border_radius=8)

        title = self.font_large.render("Save Data Found", True, COLOR_HIGHLIGHT)
        self.screen.blit(title, (box_x + 20, box_y + 15))

        prog = f"{completed}/{total}" if total > 0 else f"{completed} done"
        info = self.font_medium.render(
            f"{game_id}: {prog}  Next: Level {next_level + 1}", True, COLOR_TEXT,
        )
        self.screen.blit(info, (box_x + 20, box_y + 55))

        cont_rect = pygame.Rect(box_x + 20, box_y + 100, 180, 40)
        new_rect = pygame.Rect(box_x + 220, box_y + 100, 180, 40)
        back_rect = pygame.Rect(box_x + 120, box_y + 160, 180, 36)
        self.button_rects = {"continue": cont_rect, "new": new_rect, "back": back_rect}

        for name, rect in self.button_rects.items():
            pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=4)
            border_color = COLOR_WIN if name == "continue" else COLOR_ACCENT
            pygame.draw.rect(self.screen, border_color, rect, 1, border_radius=4)
            labels = {"continue": "[C] Continue", "new": "[N] New Game", "back": "[Q] Back"}
            lbl = self.font_small.render(labels[name], True, COLOR_TEXT)
            self.screen.blit(lbl, (rect.x + rect.w // 2 - lbl.get_width() // 2,
                                   rect.y + rect.h // 2 - lbl.get_height() // 2))

    def handle_button_click(self, pos) -> str | None:
        for name, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                return name
        return None
