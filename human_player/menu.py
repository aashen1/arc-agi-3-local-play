import pygame
from datetime import datetime

from human_player.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    COLOR_BG, COLOR_PANEL, COLOR_TEXT, COLOR_TEXT_DIM,
    COLOR_HIGHLIGHT, COLOR_WIN, COLOR_GAMEOVER, COLOR_ACCENT,
    COLOR_DANGER, COLOR_DANGER_DIM,
    ACTION_LABELS, get_keymap_scheme, get_key_labels, get_view_mode, set_view_mode,
)


class MenuRenderer:
    GRID_COLS = 5
    GRID_CELL_H = 88
    LIST_ITEM_H = 56
    SCROLLBAR_W = 12
    CONTENT_TOP = 90
    CONTENT_BOTTOM = 60

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font_title = pygame.font.SysFont("consolas", 32, bold=True)
        self.font_large = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_medium = pygame.font.SysFont("consolas", 16)
        self.font_small = pygame.font.SysFont("consolas", 13)
        self.font_cell_id = pygame.font.SysFont("consolas", 18, bold=True)
        self.hover_index = -1
        self.button_hover = None
        self.game_rects = []
        self.button_rects = {}
        self.player_rects = []
        self.input_rect = pygame.Rect(0, 0, 0, 0)
        self.level_input_rect = pygame.Rect(0, 0, 0, 0)
        self.delete_rects = []
        self.delete_input_rect = pygame.Rect(0, 0, 0, 0)
        self.view_mode = get_view_mode()
        self.scroll_offset = 0
        self.scroll_dragging = False
        self.scroll_drag_start_y = 0
        self.scroll_drag_start_offset = 0
        self.scrollbar_track_rect = None
        self.scrollbar_thumb_rect = None
        self.toggle_rect = pygame.Rect(0, 0, 0, 0)
        self.level_rects = []
        self.level_hover = -1
        self.level_input_text = ""
        self.level_input_active = False

    def _content_height(self) -> int:
        return WINDOW_HEIGHT - self.CONTENT_TOP - self.CONTENT_BOTTOM

    def _max_scroll(self, games) -> int:
        if self.view_mode == "grid":
            rows = (len(games) + self.GRID_COLS - 1) // self.GRID_COLS
            total_h = rows * self.GRID_CELL_H
        else:
            total_h = len(games) * self.LIST_ITEM_H
        return max(0, total_h - self._content_height())

    def clamp_scroll(self, games):
        self.scroll_offset = max(0, min(self.scroll_offset, self._max_scroll(games)))

    def toggle_view_mode(self):
        if self.view_mode == "grid":
            self.view_mode = "list"
        else:
            self.view_mode = "grid"
        set_view_mode(self.view_mode)
        self.scroll_offset = 0

    def draw_main_menu(self, games, level_manager, keymap_scheme, current_player="default"):
        self.screen.fill(COLOR_BG)
        self.game_rects = []
        self.button_rects = {}
        self.scrollbar_track_rect = None
        self.scrollbar_thumb_rect = None

        title = self.font_title.render("ARC-AGI-3", True, COLOR_ACCENT)
        subtitle = self.font_medium.render("Human Player Console", True, COLOR_TEXT_DIM)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 20))
        self.screen.blit(subtitle, (WINDOW_WIDTH // 2 - subtitle.get_width() // 2, 58))

        player_text = self.font_small.render(f"Player: {current_player}", True, COLOR_HIGHLIGHT)
        self.screen.blit(player_text, (WINDOW_WIDTH - player_text.get_width() - 90, 10))

        toggle_label = "List" if self.view_mode == "grid" else "Grid"
        toggle_icon = "=" if self.view_mode == "grid" else "#"
        toggle_surf = self.font_small.render(f"[{toggle_icon}] {toggle_label}", True, COLOR_TEXT)
        tw = toggle_surf.get_width() + 16
        self.toggle_rect = pygame.Rect(WINDOW_WIDTH - tw - 8, 8, tw, 24)
        is_toggle_hover = self.button_hover == "toggle"
        toggle_bg = (60, 60, 80) if is_toggle_hover else COLOR_PANEL
        pygame.draw.rect(self.screen, toggle_bg, self.toggle_rect, border_radius=3)
        pygame.draw.rect(self.screen, COLOR_ACCENT, self.toggle_rect, 1, border_radius=3)
        self.screen.blit(toggle_surf, (self.toggle_rect.x + 8, self.toggle_rect.y + 4))

        last_played_id = level_manager.get_last_played_game_id()

        content_rect = pygame.Rect(
            0, self.CONTENT_TOP, WINDOW_WIDTH - self.SCROLLBAR_W, self._content_height()
        )
        clip_prev = self.screen.get_clip()
        self.screen.set_clip(content_rect)

        if self.view_mode == "grid":
            self._draw_grid_menu(games, level_manager, last_played_id)
        else:
            self._draw_list_menu(games, level_manager, last_played_id)

        self.screen.set_clip(clip_prev)

        max_scroll = self._max_scroll(games)
        if max_scroll > 0:
            self._draw_scrollbar(max_scroll)

        self._draw_bottom_buttons()

        if len(games) == 0:
            hint = self.font_small.render(
                "No local games found — go to Settings to sync", True, COLOR_GAMEOVER,
            )
        else:
            hint = self.font_small.render(
                "Click a game or press number key to start", True, COLOR_TEXT_DIM,
            )
        self.screen.blit(hint, (WINDOW_WIDTH // 2 - hint.get_width() // 2, WINDOW_HEIGHT - 85))

    def _draw_grid_menu(self, games, level_manager, last_played_id):
        cols = self.GRID_COLS
        margin_x = 20
        margin_y = 6
        available_w = WINDOW_WIDTH - self.SCROLLBAR_W - margin_x * 2
        cell_w = (available_w - (cols - 1) * margin_x) // cols
        cell_h = self.GRID_CELL_H
        base_y = self.CONTENT_TOP - self.scroll_offset

        for i, game in enumerate(games):
            col = i % cols
            row = i // cols
            x = margin_x + col * (cell_w + margin_x)
            y = base_y + row * (cell_h + margin_y)

            if y + cell_h < self.CONTENT_TOP or y > self.CONTENT_TOP + self._content_height():
                self.game_rects.append(pygame.Rect(x, y, cell_w, cell_h))
                continue

            gid = game.game_id
            completed = level_manager.get_completed_count(gid)
            total = level_manager.get_total_levels(gid)
            is_last_played = (gid == last_played_id)
            is_fully_completed = (total > 0 and completed >= total)

            rect = pygame.Rect(x, y, cell_w, cell_h)
            self.game_rects.append(rect)

            bg_color = (50, 50, 70) if i == self.hover_index else COLOR_PANEL
            pygame.draw.rect(self.screen, bg_color, rect, border_radius=6)

            if is_last_played:
                pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, (rect.x, rect.y + 4, 3, rect.h - 8), border_radius=1)
                pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, rect, 1, border_radius=6)
            else:
                pygame.draw.rect(self.screen, COLOR_ACCENT, rect, 1, border_radius=6)

            display_id = gid.split('-')[0]
            id_text = self.font_cell_id.render(display_id, True, COLOR_TEXT)
            self.screen.blit(id_text, (rect.x + rect.w // 2 - id_text.get_width() // 2,
                                       rect.y + 10))

            if total > 0:
                prog = f"{completed}/{total}"
            elif completed > 0:
                prog = f"{completed} done"
            else:
                prog = "--"
            prog_text = self.font_small.render(prog, True, COLOR_TEXT_DIM)
            self.screen.blit(prog_text, (rect.x + rect.w // 2 - prog_text.get_width() // 2,
                                         rect.y + 34))

            bar_x = rect.x + 10
            bar_y = rect.y + 52
            bar_w = rect.w - 20
            self._draw_progress_bar(bar_x, bar_y, bar_w, completed, total)

            if is_fully_completed:
                self._draw_checkmark(rect.right - 18, rect.y + 6, 12)
                cur_lv = level_manager.get_current_level(gid)
                if cur_lv is not None and cur_lv < total:
                    pt_text = self.font_small.render(f"L{cur_lv + 1}", True, COLOR_HIGHLIGHT)
                    self.screen.blit(pt_text, (rect.x + 4, rect.y + 4))

    def _draw_list_menu(self, games, level_manager, last_played_id):
        margin_x = 20
        item_w = WINDOW_WIDTH - self.SCROLLBAR_W - margin_x * 2
        item_h = self.LIST_ITEM_H
        base_y = self.CONTENT_TOP - self.scroll_offset

        for i, game in enumerate(games):
            y = base_y + i * item_h

            if y + item_h < self.CONTENT_TOP or y > self.CONTENT_TOP + self._content_height():
                self.game_rects.append(pygame.Rect(margin_x, y, item_w, item_h))
                continue

            gid = game.game_id
            title_str = getattr(game, 'title', gid)
            tags = ", ".join(getattr(game, 'tags', []))
            completed = level_manager.get_completed_count(gid)
            total = level_manager.get_total_levels(gid)
            is_last_played = (gid == last_played_id)
            is_fully_completed = (total > 0 and completed >= total)

            rect = pygame.Rect(margin_x, y, item_w, item_h)
            self.game_rects.append(rect)

            bg_color = (50, 50, 70) if i == self.hover_index else COLOR_PANEL
            pygame.draw.rect(self.screen, bg_color, rect, border_radius=6)

            if is_last_played:
                pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, (rect.x, rect.y + 4, 3, rect.h - 8), border_radius=1)
                pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, rect, 1, border_radius=6)
            else:
                pygame.draw.rect(self.screen, COLOR_ACCENT, rect, 1, border_radius=6)

            idx_text = self.font_large.render(f"{i + 1}", True, COLOR_HIGHLIGHT)
            self.screen.blit(idx_text, (rect.x + 10, rect.y + 6))

            name_text = self.font_medium.render(f"{gid} - {title_str}", True, COLOR_TEXT)
            self.screen.blit(name_text, (rect.x + 44, rect.y + 6))

            if total > 0:
                prog = f"{completed}/{total}"
            elif completed > 0:
                prog = f"{completed} done"
            else:
                prog = "--"
            prog_text = self.font_small.render(prog, True, COLOR_TEXT_DIM)
            self.screen.blit(prog_text, (rect.x + 44, rect.y + 28))

            if total > 0:
                bar_x = rect.x + 44 + prog_text.get_width() + 8
                bar_y = rect.y + 32
                bar_w = min(120, rect.right - bar_x - (40 if is_fully_completed else 12))
                if bar_w > 20:
                    self._draw_progress_bar(bar_x, bar_y, bar_w, completed, total)

            if tags:
                tag_text = self.font_small.render(tags, True, COLOR_TEXT_DIM)
                self.screen.blit(tag_text, (rect.right - tag_text.get_width() - 12, rect.y + 8))

            if is_fully_completed:
                self._draw_checkmark(rect.right - 22, rect.y + 28, 14)
                cur_lv = level_manager.get_current_level(gid)
                if cur_lv is not None and cur_lv < total:
                    pt_text = self.font_small.render(f"L{cur_lv + 1}", True, COLOR_HIGHLIGHT)
                    self.screen.blit(pt_text, (rect.x + 44, rect.y + 42))

    def _draw_scrollbar(self, max_scroll):
        track_x = WINDOW_WIDTH - self.SCROLLBAR_W
        track_y = self.CONTENT_TOP
        track_h = self._content_height()
        self.scrollbar_track_rect = pygame.Rect(track_x, track_y, self.SCROLLBAR_W, track_h)

        pygame.draw.rect(self.screen, (25, 25, 35), self.scrollbar_track_rect)

        content_h = self._content_height()
        if self.view_mode == "grid":
            rows = (len(self.game_rects) + self.GRID_COLS - 1) // self.GRID_COLS
            total_h = rows * self.GRID_CELL_H
        else:
            total_h = len(self.game_rects) * self.LIST_ITEM_H

        if total_h <= 0:
            return

        thumb_h = max(20, int(content_h * content_h / total_h))
        thumb_y = track_y + int((content_h - thumb_h) * (self.scroll_offset / max_scroll)) if max_scroll > 0 else track_y
        self.scrollbar_thumb_rect = pygame.Rect(track_x + 2, thumb_y, self.SCROLLBAR_W - 4, thumb_h)

        thumb_color = COLOR_HIGHLIGHT if self.scroll_dragging else COLOR_ACCENT
        pygame.draw.rect(self.screen, thumb_color, self.scrollbar_thumb_rect, border_radius=4)

    def _draw_bottom_buttons(self):
        btn_y = WINDOW_HEIGHT - 50
        player_rect = pygame.Rect(40, btn_y, 140, 36)
        settings_rect = pygame.Rect(200, btn_y, 120, 36)
        stats_rect = pygame.Rect(340, btn_y, 120, 36)
        quit_rect = pygame.Rect(WINDOW_WIDTH - 160, btn_y, 120, 36)
        self.button_rects = {
            "player": player_rect,
            "settings": settings_rect,
            "stats": stats_rect,
            "quit": quit_rect,
        }

        for name, rect in self.button_rects.items():
            is_hovered = (self.button_hover == name)
            bg = (60, 60, 80) if is_hovered else COLOR_PANEL
            border = COLOR_HIGHLIGHT if is_hovered else COLOR_ACCENT
            pygame.draw.rect(self.screen, bg, rect, border_radius=4)
            pygame.draw.rect(self.screen, border, rect, 1, border_radius=4)
            labels = {
                "player": "[P] Player",
                "settings": "[S] Settings",
                "stats": "[V] Stats",
                "quit": "[Q] Quit",
            }
            lbl = self.font_small.render(labels[name], True, COLOR_TEXT)
            self.screen.blit(lbl, (rect.x + rect.w // 2 - lbl.get_width() // 2,
                                   rect.y + rect.h // 2 - lbl.get_height() // 2))

    def handle_main_menu_click(self, pos) -> str | None:
        if self.toggle_rect.collidepoint(pos):
            return "toggle_view"
        content_top = self.CONTENT_TOP
        content_bottom = self.CONTENT_TOP + self._content_height()
        for i, rect in enumerate(self.game_rects):
            if rect.collidepoint(pos) and rect.bottom > content_top and rect.top < content_bottom:
                return f"game:{i}"
        for name, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                return name
        if self.scrollbar_thumb_rect and self.scrollbar_thumb_rect.collidepoint(pos):
            return "scrollbar_thumb"
        if self.scrollbar_track_rect and self.scrollbar_track_rect.collidepoint(pos):
            return "scrollbar_track"
        return False

    def handle_main_menu_hover(self, pos):
        self.hover_index = -1
        self.button_hover = None
        content_top = self.CONTENT_TOP
        content_bottom = self.CONTENT_TOP + self._content_height()
        for i, rect in enumerate(self.game_rects):
            if rect.collidepoint(pos) and rect.bottom > content_top and rect.top < content_bottom:
                self.hover_index = i
                break
        for name, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                self.button_hover = name
                break
        if self.toggle_rect.collidepoint(pos):
            self.button_hover = "toggle"

    def handle_scroll(self, y_scroll, games):
        step = self.GRID_CELL_H if self.view_mode == "grid" else self.LIST_ITEM_H
        self.scroll_offset -= y_scroll * step
        self.clamp_scroll(games)

    def start_scroll_drag(self, mouse_y):
        self.scroll_dragging = True
        self.scroll_drag_start_y = mouse_y
        self.scroll_drag_start_offset = self.scroll_offset

    def update_scroll_drag(self, mouse_y, games):
        if not self.scroll_dragging:
            return
        delta_y = mouse_y - self.scroll_drag_start_y
        content_h = self._content_height()
        if self.view_mode == "grid":
            rows = (len(games) + self.GRID_COLS - 1) // self.GRID_COLS
            total_h = rows * self.GRID_CELL_H
        else:
            total_h = len(games) * self.LIST_ITEM_H
        if total_h <= content_h:
            return
        ratio = total_h / content_h
        self.scroll_offset = self.scroll_drag_start_offset + int(delta_y * ratio)
        self.clamp_scroll(games)

    def end_scroll_drag(self):
        self.scroll_dragging = False

    def handle_scrollbar_track_click(self, pos, games):
        if not self.scrollbar_track_rect:
            return
        max_scroll = self._max_scroll(games)
        if max_scroll <= 0:
            return
        track_h = self.scrollbar_track_rect.h
        click_ratio = (pos[1] - self.scrollbar_track_rect.y) / track_h
        self.scroll_offset = int(click_ratio * max_scroll)
        self.clamp_scroll(games)

    def draw_player_select(self, players, current_player, player_metadata,
                           input_text="", input_active=False):
        self.screen.fill(COLOR_BG)
        self.button_rects = {}
        self.player_rects = []
        self.delete_rects = []

        title = self.font_large.render("Select Player", True, COLOR_ACCENT)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 20))

        current_text = self.font_medium.render(f"Current: {current_player}", True, COLOR_HIGHLIGHT)
        self.screen.blit(current_text, (60, 65))

        y = 100
        for i, player in enumerate(players):
            is_current = player == current_player
            rect = pygame.Rect(60, y, WINDOW_WIDTH - 120, 56)
            self.player_rects.append(rect)

            bg = COLOR_ACCENT if is_current else COLOR_PANEL
            border = COLOR_HIGHLIGHT if is_current else COLOR_ACCENT
            pygame.draw.rect(self.screen, bg, rect, border_radius=4)
            pygame.draw.rect(self.screen, border, rect, 1, border_radius=4)

            color = COLOR_BG if is_current else COLOR_TEXT
            name = self.font_medium.render(player, True, color)
            self.screen.blit(name, (rect.x + 16, rect.y + 6))

            if is_current:
                check = self.font_small.render("active", True, COLOR_HIGHLIGHT)
                self.screen.blit(check, (rect.x + 16 + name.get_width() + 8, rect.y + 9))

            meta = player_metadata.get(player, {})
            levels = meta.get("total_levels_completed", 0)
            games = meta.get("total_games_played", 0)
            time_ms = meta.get("total_time_ms", 0)
            last_played = meta.get("last_played")

            time_s = time_ms // 1000
            time_str = f"{time_s // 3600}h{time_s % 3600 // 60}m" if time_s >= 3600 else f"{time_s // 60}m{time_s % 60}s" if time_s >= 60 else f"{time_s}s"

            meta_parts = [f"{levels} levels", f"{games} games", time_str]
            if last_played:
                try:
                    dt = datetime.fromisoformat(last_played)
                    meta_parts.append(dt.strftime("%Y-%m-%d %H:%M"))
                except (ValueError, TypeError):
                    pass

            meta_text = "  |  ".join(meta_parts)
            meta_color = COLOR_BG if is_current else COLOR_TEXT_DIM
            meta_render = self.font_small.render(meta_text, True, meta_color)
            self.screen.blit(meta_render, (rect.x + 16, rect.y + 30))

            if not is_current:
                del_rect = pygame.Rect(rect.right - 36, rect.y + 12, 24, 24)
                self.delete_rects.append(del_rect)
                self._draw_trash_icon(del_rect)
            else:
                self.delete_rects.append(None)

            y += 66

        y += 20
        pygame.draw.line(self.screen, COLOR_TEXT_DIM, (60, y), (WINDOW_WIDTH - 60, y))
        y += 15

        new_label = self.font_medium.render("New Player Name:", True, COLOR_TEXT)
        self.screen.blit(new_label, (60, y))
        y += 25

        input_rect = pygame.Rect(60, y, WINDOW_WIDTH - 180, 36)
        self.input_rect = input_rect
        border_color = COLOR_HIGHLIGHT if input_active else COLOR_ACCENT
        pygame.draw.rect(self.screen, COLOR_PANEL, input_rect, border_radius=4)
        pygame.draw.rect(self.screen, border_color, input_rect, 2, border_radius=4)

        cursor_visible = input_active and (pygame.time.get_ticks() // 500) % 2 == 0
        display_text = input_text + ("|" if cursor_visible else "")
        input_render = self.font_medium.render(display_text, True, COLOR_TEXT)
        self.screen.blit(input_render, (input_rect.x + 10, input_rect.y + 8))

        create_rect = pygame.Rect(WINDOW_WIDTH - 110, y, 90, 36)
        pygame.draw.rect(self.screen, COLOR_ACCENT, create_rect, border_radius=4)
        create_lbl = self.font_small.render("Create", True, COLOR_BG)
        self.screen.blit(create_lbl, (create_rect.x + create_rect.w // 2 - create_lbl.get_width() // 2,
                                       create_rect.y + create_rect.h // 2 - create_lbl.get_height() // 2))
        self.button_rects["create"] = create_rect

        back_rect = pygame.Rect(WINDOW_WIDTH // 2 - 60, WINDOW_HEIGHT - 50, 120, 36)
        self.button_rects["back"] = back_rect
        pygame.draw.rect(self.screen, COLOR_PANEL, back_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_ACCENT, back_rect, 1, border_radius=4)
        lbl = self.font_small.render("[ESC] Back", True, COLOR_TEXT)
        self.screen.blit(lbl, (back_rect.x + back_rect.w // 2 - lbl.get_width() // 2,
                               back_rect.y + back_rect.h // 2 - lbl.get_height() // 2))

    def _draw_trash_icon(self, rect):
        cx, cy = rect.centerx, rect.centery
        s = 5
        pygame.draw.rect(self.screen, COLOR_TEXT_DIM, (cx - s, cy - s + 2, s * 2, s * 2 + 1), 1)
        pygame.draw.line(self.screen, COLOR_TEXT_DIM, (cx - s - 1, cy - s + 2), (cx + s + 1, cy - s + 2))
        pygame.draw.line(self.screen, COLOR_TEXT_DIM, (cx - 2, cy - s), (cx - 2, cy - s + 2))
        pygame.draw.line(self.screen, COLOR_TEXT_DIM, (cx + 2, cy - s), (cx + 2, cy - s + 2))
        pygame.draw.line(self.screen, COLOR_TEXT_DIM, (cx - 3, cy - s + 1), (cx + 3, cy - s + 1))

    def draw_delete_confirm(self, player_name, player_metadata, confirm_text="", confirm_active=False):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        box_w, box_h = 440, 280
        box_x = (WINDOW_WIDTH - box_w) // 2
        box_y = (WINDOW_HEIGHT - box_h) // 2
        pygame.draw.rect(self.screen, (40, 25, 25), (box_x, box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_DANGER, (box_x, box_y, box_w, box_h), 2, border_radius=8)

        title = self.font_large.render("Delete Player", True, COLOR_DANGER)
        self.screen.blit(title, (box_x + 20, box_y + 16))

        warn = self.font_medium.render("This action cannot be undone!", True, COLOR_GAMEOVER)
        self.screen.blit(warn, (box_x + 20, box_y + 48))

        meta = player_metadata
        levels = meta.get("total_levels_completed", 0)
        games = meta.get("total_games_played", 0)
        time_ms = meta.get("total_time_ms", 0)
        time_s = time_ms // 1000
        time_str = f"{time_s // 3600}h{time_s % 3600 // 60}m" if time_s >= 3600 else f"{time_s // 60}m{time_s % 60}s" if time_s >= 60 else f"{time_s}s"

        info_lines = [
            f"Player: {player_name}",
            f"Levels completed: {levels}  |  Games played: {games}  |  Time: {time_str}",
        ]
        last_played = meta.get("last_played")
        if last_played:
            try:
                dt = datetime.fromisoformat(last_played)
                info_lines.append(f"Last played: {dt.strftime('%Y-%m-%d %H:%M')}")
            except (ValueError, TypeError):
                pass

        iy = box_y + 78
        for line in info_lines:
            info_render = self.font_small.render(line, True, COLOR_TEXT)
            self.screen.blit(info_render, (box_x + 20, iy))
            iy += 20

        iy += 10
        prompt = self.font_medium.render(f'Type "{player_name}" to confirm:', True, COLOR_TEXT)
        self.screen.blit(prompt, (box_x + 20, iy))
        iy += 24

        input_rect = pygame.Rect(box_x + 20, iy, box_w - 40, 30)
        self.delete_input_rect = input_rect
        border_color = COLOR_HIGHLIGHT if confirm_active else COLOR_ACCENT
        pygame.draw.rect(self.screen, COLOR_PANEL, input_rect, border_radius=4)
        pygame.draw.rect(self.screen, border_color, input_rect, 2, border_radius=4)

        cursor_visible = confirm_active and (pygame.time.get_ticks() // 500) % 2 == 0
        display_text = confirm_text + ("|" if cursor_visible else "")
        input_render = self.font_medium.render(display_text, True, COLOR_TEXT)
        self.screen.blit(input_render, (input_rect.x + 8, input_rect.y + 6))

        iy += 40
        cancel_rect = pygame.Rect(box_x + 20, iy, 100, 30)
        pygame.draw.rect(self.screen, COLOR_PANEL, cancel_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_ACCENT, cancel_rect, 1, border_radius=4)
        cancel_lbl = self.font_small.render("Cancel", True, COLOR_TEXT)
        self.screen.blit(cancel_lbl, (cancel_rect.x + cancel_rect.w // 2 - cancel_lbl.get_width() // 2,
                                       cancel_rect.y + cancel_rect.h // 2 - cancel_lbl.get_height() // 2))
        self.button_rects["cancel_delete"] = cancel_rect

        confirm_enabled = confirm_text == player_name
        confirm_rect = pygame.Rect(box_x + box_w - 130, iy, 110, 30)
        btn_color = COLOR_DANGER if confirm_enabled else COLOR_DANGER_DIM
        pygame.draw.rect(self.screen, btn_color, confirm_rect, border_radius=4)
        confirm_lbl = self.font_small.render("Delete", True, COLOR_BG if confirm_enabled else COLOR_TEXT_DIM)
        self.screen.blit(confirm_lbl, (confirm_rect.x + confirm_rect.w // 2 - confirm_lbl.get_width() // 2,
                                        confirm_rect.y + confirm_rect.h // 2 - confirm_lbl.get_height() // 2))
        self.button_rects["confirm_delete"] = confirm_rect

    def handle_player_click(self, pos, players) -> str | None:
        if hasattr(self, 'delete_rects'):
            for i, rect in enumerate(self.delete_rects):
                if rect and rect.collidepoint(pos) and i < len(players):
                    return f"delete:{players[i]}"
        for i, rect in enumerate(self.player_rects):
            if rect.collidepoint(pos) and i < len(players):
                return f"select:{players[i]}"
        for name, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                return name
        return None

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

    def draw_settings(self, keymap_scheme, sync_mode="conservative", show_sync_button=False):
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

        sync_label = self.font_medium.render("Game Sync Mode:", True, COLOR_TEXT)
        self.screen.blit(sync_label, (60, y))
        sync_display = "Manual sync only" if sync_mode == "conservative" else "Auto sync on startup"
        sync_value = self.font_large.render(sync_display, True, COLOR_HIGHLIGHT)
        self.screen.blit(sync_value, (60, y + 28))

        conservative_rect = pygame.Rect(60, y + 70, 310, 40)
        auto_rect = pygame.Rect(390, y + 70, 310, 40)
        self.button_rects["conservative"] = conservative_rect
        self.button_rects["auto"] = auto_rect

        for name, rect in [("conservative", conservative_rect), ("auto", auto_rect)]:
            is_selected = (name == sync_mode)
            bg = COLOR_ACCENT if is_selected else COLOR_PANEL
            border = COLOR_HIGHLIGHT if is_selected else COLOR_ACCENT
            pygame.draw.rect(self.screen, bg, rect, border_radius=4)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=4)
            sync_labels = {"conservative": "Manual [D] Sync", "auto": "Auto on Startup"}
            color = COLOR_BG if is_selected else COLOR_TEXT
            lbl = self.font_medium.render(sync_labels[name], True, color)
            self.screen.blit(lbl, (rect.x + rect.w // 2 - lbl.get_width() // 2,
                                   rect.y + rect.h // 2 - lbl.get_height() // 2))

        sync_now_rect = pygame.Rect(WINDOW_WIDTH - 170, y + 70, 140, 40)
        if show_sync_button:
            self.button_rects["download"] = sync_now_rect
            is_sync_hover = (self.button_hover == "download")
            sync_bg = (60, 60, 80) if is_sync_hover else COLOR_PANEL
            sync_border = COLOR_HIGHLIGHT if is_sync_hover else COLOR_ACCENT
            pygame.draw.rect(self.screen, sync_bg, sync_now_rect, border_radius=4)
            pygame.draw.rect(self.screen, sync_border, sync_now_rect, 1, border_radius=4)
            sync_lbl = self.font_medium.render("[D] Sync Now", True, COLOR_TEXT)
            self.screen.blit(sync_lbl, (sync_now_rect.x + sync_now_rect.w // 2 - sync_lbl.get_width() // 2,
                                        sync_now_rect.y + sync_now_rect.h // 2 - sync_lbl.get_height() // 2))

        y += 140
        pygame.draw.line(self.screen, COLOR_TEXT_DIM, (60, y), (WINDOW_WIDTH - 60, y))
        y += 20

        key_labels = get_key_labels()
        header = self.font_medium.render("Key Bindings:", True, COLOR_ACCENT)
        self.screen.blit(header, (60, y))
        y += 28

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

    def draw_completed_prompt(self, game_id, total, current_level, has_playthrough):
        self.screen.fill(COLOR_BG)
        self.button_rects = {}

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))

        box_w = 460
        box_h = 260 if has_playthrough else 220
        box_x = (WINDOW_WIDTH - box_w) // 2
        box_y = (WINDOW_HEIGHT - box_h) // 2
        pygame.draw.rect(self.screen, COLOR_PANEL, (box_x, box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_WIN, (box_x, box_y, box_w, box_h), 2, border_radius=8)

        title = self.font_large.render("All Levels Completed!", True, COLOR_WIN)
        self.screen.blit(title, (box_x + 20, box_y + 15))

        self._draw_checkmark(box_x + box_w - 35, box_y + 14, 18)

        info = self.font_medium.render(
            f"{game_id}: {total}/{total}", True, COLOR_TEXT,
        )
        self.screen.blit(info, (box_x + 20, box_y + 50))

        if has_playthrough and current_level is not None:
            pt_info = self.font_medium.render(
                f"New playthrough: Level {current_level + 1}", True, COLOR_HIGHLIGHT,
            )
            self.screen.blit(pt_info, (box_x + 20, box_y + 72))

        btn_y_start = box_y + (100 if has_playthrough else 90)

        if has_playthrough:
            cont_rect = pygame.Rect(box_x + 20, btn_y_start, 130, 36)
            new_rect = pygame.Rect(box_x + 160, btn_y_start, 130, 36)
            sel_rect = pygame.Rect(box_x + 300, btn_y_start, 140, 36)
            back_rect = pygame.Rect(box_x + 140, btn_y_start + 50, 180, 36)
            self.button_rects = {
                "continue": cont_rect,
                "new": new_rect,
                "select": sel_rect,
                "back": back_rect,
            }
        else:
            new_rect = pygame.Rect(box_x + 40, btn_y_start, 170, 36)
            sel_rect = pygame.Rect(box_x + 240, btn_y_start, 180, 36)
            back_rect = pygame.Rect(box_x + 140, btn_y_start + 50, 180, 36)
            self.button_rects = {
                "new": new_rect,
                "select": sel_rect,
                "back": back_rect,
            }

        for name, rect in self.button_rects.items():
            pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=4)
            border_color = COLOR_WIN if name == "continue" else COLOR_ACCENT
            pygame.draw.rect(self.screen, border_color, rect, 1, border_radius=4)
            labels = {
                "continue": "[C] Continue",
                "new": "[N] New Game",
                "select": "[L] Select Level",
                "back": "[Q] Back",
            }
            lbl = self.font_small.render(labels[name], True, COLOR_TEXT)
            self.screen.blit(lbl, (rect.x + rect.w // 2 - lbl.get_width() // 2,
                                   rect.y + rect.h // 2 - lbl.get_height() // 2))

    def draw_level_select(self, game_id, total_levels, level_manager):
        self.screen.fill(COLOR_BG)
        self.button_rects = {}
        self.level_rects = []

        title = self.font_large.render(f"Select Level - {game_id}", True, COLOR_ACCENT)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 15))

        current_level = level_manager.get_current_level(game_id)

        cols = 5
        margin_x = 16
        margin_y = 10
        grid_top = 55
        available_w = WINDOW_WIDTH - margin_x * 2
        cell_w = (available_w - (cols - 1) * margin_x) // cols
        cell_h = 64

        for i in range(total_levels):
            col = i % cols
            row = i // cols
            x = margin_x + col * (cell_w + margin_x)
            y = grid_top + row * (cell_h + margin_y)

            rect = pygame.Rect(x, y, cell_w, cell_h)
            self.level_rects.append(rect)

            info = level_manager.get_level_info(game_id, i)
            is_completed = info["completed"]
            is_current = (current_level is not None and i == current_level)
            is_hover = (i == self.level_hover)

            if is_current:
                bg = (50, 55, 30)
            elif is_hover:
                bg = (50, 50, 70)
            else:
                bg = COLOR_PANEL

            pygame.draw.rect(self.screen, bg, rect, border_radius=6)

            border = COLOR_HIGHLIGHT if is_current else (COLOR_WIN if is_completed else COLOR_ACCENT)
            pygame.draw.rect(self.screen, border, rect, 1, border_radius=6)

            num_text = self.font_cell_id.render(f"{i + 1}", True, COLOR_TEXT)
            self.screen.blit(num_text, (rect.x + rect.w // 2 - num_text.get_width() // 2,
                                        rect.y + 8))

            if is_completed:
                self._draw_checkmark(rect.right - 16, rect.y + 4, 10)
                if info.get("best_steps") is not None:
                    bs_text = self.font_small.render(
                        f"{info['best_steps']}s", True, COLOR_TEXT_DIM,
                    )
                    self.screen.blit(bs_text, (rect.x + rect.w // 2 - bs_text.get_width() // 2,
                                               rect.y + 34))
            else:
                dash = self.font_small.render("--", True, COLOR_TEXT_DIM)
                self.screen.blit(dash, (rect.x + rect.w // 2 - dash.get_width() // 2,
                                        rect.y + 34))

        input_y = WINDOW_HEIGHT - 90
        input_label = self.font_medium.render("Go to level:", True, COLOR_TEXT)
        self.screen.blit(input_label, (60, input_y))

        input_rect = pygame.Rect(180, input_y - 2, 120, 30)
        self.level_input_rect = input_rect
        border_color = COLOR_HIGHLIGHT if self.level_input_active else COLOR_ACCENT
        pygame.draw.rect(self.screen, COLOR_PANEL, input_rect, border_radius=4)
        pygame.draw.rect(self.screen, border_color, input_rect, 2, border_radius=4)

        cursor_visible = self.level_input_active and (pygame.time.get_ticks() // 500) % 2 == 0
        display_text = self.level_input_text + ("|" if cursor_visible else "")
        input_render = self.font_medium.render(display_text, True, COLOR_TEXT)
        self.screen.blit(input_render, (input_rect.x + 8, input_rect.y + 5))

        go_rect = pygame.Rect(310, input_y - 2, 60, 30)
        pygame.draw.rect(self.screen, COLOR_ACCENT, go_rect, border_radius=4)
        go_lbl = self.font_small.render("Go", True, COLOR_BG)
        self.screen.blit(go_lbl, (go_rect.x + go_rect.w // 2 - go_lbl.get_width() // 2,
                                  go_rect.y + go_rect.h // 2 - go_lbl.get_height() // 2))
        self.button_rects["go"] = go_rect

        back_rect = pygame.Rect(WINDOW_WIDTH // 2 - 60, WINDOW_HEIGHT - 45, 120, 36)
        self.button_rects["back"] = back_rect
        pygame.draw.rect(self.screen, COLOR_PANEL, back_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_ACCENT, back_rect, 1, border_radius=4)
        lbl = self.font_small.render("[ESC] Back", True, COLOR_TEXT)
        self.screen.blit(lbl, (back_rect.x + back_rect.w // 2 - lbl.get_width() // 2,
                               back_rect.y + back_rect.h // 2 - lbl.get_height() // 2))

    def handle_level_select_click(self, pos) -> str | None:
        for i, rect in enumerate(self.level_rects):
            if rect.collidepoint(pos):
                return f"level:{i}"
        for name, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                return name
        return None

    def handle_level_select_hover(self, pos):
        self.level_hover = -1
        for i, rect in enumerate(self.level_rects):
            if rect.collidepoint(pos):
                self.level_hover = i
                break

    def _draw_progress_bar(self, x, y, w, completed, total):
        h = 6
        pygame.draw.rect(self.screen, (60, 60, 60), (x, y, w, h), border_radius=3)
        if total > 0 and completed > 0:
            fill_w = max(3, int(w * completed / total))
            pygame.draw.rect(self.screen, COLOR_WIN, (x, y, fill_w, h), border_radius=3)

    def _draw_checkmark(self, x, y, size):
        s = size
        pts = [
            (x + s * 0.1, y + s * 0.5),
            (x + s * 0.35, y + s * 0.8),
            (x + s * 0.9, y + s * 0.15),
        ]
        pygame.draw.lines(self.screen, COLOR_WIN, False, pts, 2)

    def draw_sync_progress(self, current, total, game_id, status):
        self.screen.fill(COLOR_BG)

        title = self.font_large.render("Downloading Games...", True, COLOR_ACCENT)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 60))

        progress_text = self.font_medium.render(
            f"{current}/{total}  {game_id}  {status}", True, COLOR_TEXT,
        )
        self.screen.blit(progress_text, (WINDOW_WIDTH // 2 - progress_text.get_width() // 2, 120))

        bar_x = 100
        bar_y = 170
        bar_w = WINDOW_WIDTH - 200
        bar_h = 20
        pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        if total > 0:
            fill_w = max(3, int(bar_w * current / total))
            pygame.draw.rect(self.screen, COLOR_WIN, (bar_x, bar_y, fill_w, bar_h), border_radius=6)

        pct = self.font_medium.render(
            f"{int(current / total * 100)}%" if total > 0 else "0%", True, COLOR_TEXT,
        )
        self.screen.blit(pct, (WINDOW_WIDTH // 2 - pct.get_width() // 2, 200))

        hint = self.font_small.render("Please wait, this only needs to be done once.", True, COLOR_TEXT_DIM)
        self.screen.blit(hint, (WINDOW_WIDTH // 2 - hint.get_width() // 2, 260))

    def draw_sync_complete(self, result):
        self.screen.fill(COLOR_BG)
        self.button_rects = {}

        title = self.font_large.render("Download Complete!", True, COLOR_WIN)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 60))

        y = 120
        info_lines = [
            f"Total games: {result.total}",
            f"Downloaded: {result.downloaded}",
            f"Already cached: {result.skipped}",
        ]
        if result.failed:
            info_lines.append(f"Failed: {len(result.failed)}")
        for line in info_lines:
            text = self.font_medium.render(line, True, COLOR_TEXT)
            self.screen.blit(text, (WINDOW_WIDTH // 2 - text.get_width() // 2, y))
            y += 28

        y += 20
        safety_text = self.font_medium.render(
            "Games are now cached locally.", True, COLOR_HIGHLIGHT,
        )
        self.screen.blit(safety_text, (WINDOW_WIDTH // 2 - safety_text.get_width() // 2, y))
        y += 28

        hint1 = self.font_small.render(
            "You can safely delete ARC_API_KEY from .env if you", True, COLOR_TEXT_DIM,
        )
        self.screen.blit(hint1, (WINDOW_WIDTH // 2 - hint1.get_width() // 2, y))
        y += 20
        hint2 = self.font_small.render(
            "only play as human — this prevents any data upload.", True, COLOR_TEXT_DIM,
        )
        self.screen.blit(hint2, (WINDOW_WIDTH // 2 - hint2.get_width() // 2, y))

        ok_rect = pygame.Rect(WINDOW_WIDTH // 2 - 60, WINDOW_HEIGHT - 60, 120, 36)
        self.button_rects["ok"] = ok_rect
        pygame.draw.rect(self.screen, COLOR_ACCENT, ok_rect, border_radius=4)
        lbl = self.font_small.render("OK", True, COLOR_BG)
        self.screen.blit(lbl, (ok_rect.x + ok_rect.w // 2 - lbl.get_width() // 2,
                               ok_rect.y + ok_rect.h // 2 - lbl.get_height() // 2))

    def handle_button_click(self, pos) -> str | None:
        for name, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                return name
        return None
