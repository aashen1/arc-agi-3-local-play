import numpy as np
import pygame
from arcengine import GameAction

from human_player.config import (
    ACTION_LABELS,
    ARC_PALETTE,
    CELL_SIZE,
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_BUTTON_BG,
    COLOR_BUTTON_BORDER,
    COLOR_BUTTON_HOVER,
    COLOR_GAMEOVER,
    COLOR_HIGHLIGHT,
    COLOR_PANEL,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_WIN,
    GRID_OFFSET_X,
    GRID_OFFSET_Y,
    GRID_PIXEL,
    GRID_SIZE,
    HUD_BOTTOM_H,
    HUD_TOP_H,
    PANEL_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    get_key_labels,
)


class Renderer:
    """Render the game grid, HUD, and action buttons onto a Pygame surface."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font_large = pygame.font.SysFont("consolas,monospace", 22, bold=True)
        self.font_medium = pygame.font.SysFont("consolas,monospace", 16)
        self.font_small = pygame.font.SysFont("consolas,monospace", 13)
        self._grid_surface = pygame.Surface((GRID_PIXEL, GRID_PIXEL))
        self._hover_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        self._hover_surface.fill((255, 255, 255, 60))
        self._bottom_buttons = []
        self._hovered_button = None
        self._overlay_buttons = []

    def pixel_to_grid(self, px: int, py: int) -> tuple[int, int] | tuple[None, None]:
        """Convert pixel coordinates to grid (col, row), or (None, None) if outside."""
        gx = (px - GRID_OFFSET_X) // CELL_SIZE
        gy = (py - GRID_OFFSET_Y) // CELL_SIZE
        if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
            return gx, gy
        return None, None

    def check_bottom_button_click(self, pos) -> str | None:
        """Return the action ID of a bottom button at pos, or None."""
        for rect, action_id in self._bottom_buttons:
            if rect.collidepoint(pos):
                return action_id
        return None

    def update_bottom_button_hover(self, pos):
        """Update the hovered button state based on mouse position."""
        self._hovered_button = None
        for rect, action_id in self._bottom_buttons:
            if rect.collidepoint(pos):
                self._hovered_button = action_id
                break
        for rect, action_id in self._overlay_buttons:
            if rect.collidepoint(pos):
                self._hovered_button = action_id
                break

    def check_overlay_button_click(self, pos) -> str | None:
        """Return the action ID of an overlay button at pos, or None."""
        for rect, action_id in self._overlay_buttons:
            if rect.collidepoint(pos):
                return action_id
        return None

    def draw_frame(
        self,
        frame,
        mouse_grid_pos,
        step_count,
        elapsed_ms,
        levels_completed,
        max_levels,
        available_actions,
        keymap_scheme,
        game_id,
    ):
        """Draw the complete game frame: grid, HUD, panel, and action buttons."""
        self.screen.fill(COLOR_BG)
        self._draw_grid(frame, mouse_grid_pos)
        self._draw_hud_top(game_id, levels_completed, max_levels, keymap_scheme)
        self._draw_panel(step_count, elapsed_ms, available_actions, keymap_scheme, mouse_grid_pos)
        self._draw_hud_bottom(available_actions, mouse_grid_pos)

    def _draw_grid(self, frame, mouse_grid_pos):
        if isinstance(frame, list):
            grid = np.array(frame[-1]) if frame else None
        else:
            grid = np.array(frame)

        if grid is None:
            return

        self._grid_surface.fill(COLOR_BG)
        for y in range(min(grid.shape[0], GRID_SIZE)):
            for x in range(min(grid.shape[1], GRID_SIZE)):
                color_idx = int(grid[y, x])
                if 0 <= color_idx < len(ARC_PALETTE):
                    color = ARC_PALETTE[color_idx]
                else:
                    color = (255, 0, 255)
                pygame.draw.rect(
                    self._grid_surface,
                    color,
                    (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE),
                )

        if mouse_grid_pos and mouse_grid_pos[0] is not None:
            gx, gy = mouse_grid_pos
            self._grid_surface.blit(
                self._hover_surface,
                (gx * CELL_SIZE, gy * CELL_SIZE),
            )
            pygame.draw.rect(
                self._grid_surface,
                COLOR_HIGHLIGHT,
                (gx * CELL_SIZE, gy * CELL_SIZE, CELL_SIZE, CELL_SIZE),
                1,
            )

        self.screen.blit(self._grid_surface, (GRID_OFFSET_X, GRID_OFFSET_Y))

    def _draw_hud_top(self, game_id, levels_completed, max_levels, keymap_scheme):
        bar_rect = pygame.Rect(0, 0, WINDOW_WIDTH, HUD_TOP_H)
        pygame.draw.rect(self.screen, COLOR_PANEL, bar_rect)
        pygame.draw.line(self.screen, COLOR_ACCENT, (0, HUD_TOP_H), (WINDOW_WIDTH, HUD_TOP_H))

        title = self.font_large.render("ARC-AGI-3", True, COLOR_ACCENT)
        self.screen.blit(title, (10, 8))

        scheme_name = "WASD" if keymap_scheme == "wasd" else "Arrows"
        level_text = f"Lv {levels_completed + 1}"
        if max_levels > 0:
            level_text += f"/{max_levels}"
        info = self.font_medium.render(
            f"{game_id}  |  {level_text}  |  {scheme_name}",
            True,
            COLOR_TEXT,
        )
        self.screen.blit(info, (160, 12))

    def _draw_panel(
        self, step_count, elapsed_ms, available_actions, keymap_scheme, mouse_grid_pos
    ):
        panel_x = GRID_PIXEL
        panel_rect = pygame.Rect(panel_x, HUD_TOP_H, PANEL_WIDTH, GRID_PIXEL)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel_rect)
        pygame.draw.line(self.screen, COLOR_ACCENT, (panel_x, HUD_TOP_H), (panel_x, WINDOW_HEIGHT))

        y = HUD_TOP_H + 15
        x = panel_x + 12

        elapsed_s = elapsed_ms // 1000
        minutes = elapsed_s // 60
        seconds = elapsed_s % 60

        self._draw_label_value(x, y, "Steps", str(step_count))
        y += 28
        self._draw_label_value(x, y, "Time", f"{minutes:02d}:{seconds:02d}")
        y += 40

        pygame.draw.line(self.screen, COLOR_TEXT_DIM, (x, y), (x + PANEL_WIDTH - 24, y))
        y += 12

        label = self.font_medium.render("Actions", True, COLOR_ACCENT)
        self.screen.blit(label, (x, y))
        y += 24

        key_labels = get_key_labels()
        for action in [
            GameAction.ACTION1,
            GameAction.ACTION2,
            GameAction.ACTION3,
            GameAction.ACTION4,
            GameAction.ACTION5,
            GameAction.ACTION6,
            GameAction.ACTION7,
            GameAction.RESET,
        ]:
            is_available = action in available_actions
            key_str = key_labels.get(action, "?")
            action_str = ACTION_LABELS.get(action, action.name)
            color = COLOR_TEXT if is_available else COLOR_TEXT_DIM
            text = self.font_small.render(f"[{key_str}] {action_str}", True, color)
            self.screen.blit(text, (x, y))
            y += 18

        y += 12
        pygame.draw.line(self.screen, COLOR_TEXT_DIM, (x, y), (x + PANEL_WIDTH - 24, y))
        y += 12

        if mouse_grid_pos and mouse_grid_pos[0] is not None:
            gx, gy = mouse_grid_pos
            coord_text = self.font_medium.render(f"Cursor: ({gx}, {gy})", True, COLOR_HIGHLIGHT)
            self.screen.blit(coord_text, (x, y))
            y += 24
            if GameAction.ACTION6 in available_actions:
                hint = self.font_small.render("Click to ACTION6", True, COLOR_TEXT_DIM)
                self.screen.blit(hint, (x, y))
        else:
            coord_text = self.font_medium.render("Cursor: --", True, COLOR_TEXT_DIM)
            self.screen.blit(coord_text, (x, y))

    def _draw_hud_bottom(self, available_actions, mouse_grid_pos):
        bar_y = WINDOW_HEIGHT - HUD_BOTTOM_H
        bar_rect = pygame.Rect(0, bar_y, WINDOW_WIDTH, HUD_BOTTOM_H)
        pygame.draw.rect(self.screen, COLOR_PANEL, bar_rect)
        pygame.draw.line(self.screen, COLOR_ACCENT, (0, bar_y), (WINDOW_WIDTH, bar_y))

        self._bottom_buttons = []
        button_y = bar_y + 5
        button_h = 20
        button_padding = 8

        buttons_data = [
            ("[Esc] Menu", "menu", True),
            ("[R] Reset", "reset", True),
            ("[Z] Undo", "undo", GameAction.ACTION7 in available_actions),
        ]

        x = 10
        for label, action_id, enabled in buttons_data:
            text_width = self.font_small.size(label)[0]
            button_w = text_width + button_padding * 2
            button_rect = pygame.Rect(x, button_y, button_w, button_h)

            is_hovered = self._hovered_button == action_id and enabled
            color = COLOR_BUTTON_HOVER if is_hovered else COLOR_BUTTON_BG
            if not enabled:
                color = (50, 50, 55)

            pygame.draw.rect(self.screen, color, button_rect, border_radius=4)
            border_color = COLOR_HIGHLIGHT if is_hovered else COLOR_BUTTON_BORDER
            if not enabled:
                border_color = (70, 70, 75)
            pygame.draw.rect(self.screen, border_color, button_rect, 1, border_radius=4)

            text_color = COLOR_TEXT if enabled else COLOR_TEXT_DIM
            text = self.font_small.render(label, True, text_color)
            text_x = x + button_padding
            text_y = button_y + (button_h - text.get_height()) // 2
            self.screen.blit(text, (text_x, text_y))

            if enabled:
                self._bottom_buttons.append((button_rect, action_id))

            x += button_w + 12

        hints_x = x + 10
        if GameAction.ACTION6 in available_actions:
            hints = "[Mouse] Click grid"
            text = self.font_small.render(hints, True, COLOR_TEXT_DIM)
            self.screen.blit(text, (hints_x, bar_y + 8))

    def _draw_label_value(self, x, y, label, value):
        lbl = self.font_small.render(label, True, COLOR_TEXT_DIM)
        val = self.font_large.render(value, True, COLOR_TEXT)
        self.screen.blit(lbl, (x, y))
        self.screen.blit(val, (x + 70, y - 3))

    def draw_overlay_win(self, level_index, steps, time_ms, best_steps, best_time_ms):
        """Draw the level-complete overlay with stats and a Continue button."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        box_w, box_h = 360, 180
        box_x = (WINDOW_WIDTH - box_w) // 2
        box_y = (WINDOW_HEIGHT - box_h) // 2
        pygame.draw.rect(self.screen, (30, 50, 30), (box_x, box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_WIN, (box_x, box_y, box_w, box_h), 2, border_radius=8)

        title = self.font_large.render(f"Level {level_index + 1} Complete!", True, COLOR_WIN)
        self.screen.blit(title, (box_x + 20, box_y + 20))

        elapsed_s = time_ms // 1000
        info = self.font_medium.render(
            f"Steps: {steps}  Time: {elapsed_s // 60:02d}:{elapsed_s % 60:02d}", True, COLOR_TEXT
        )
        self.screen.blit(info, (box_x + 20, box_y + 60))

        if best_steps and steps <= best_steps:
            record = self.font_medium.render("New Record!", True, COLOR_HIGHLIGHT)
            self.screen.blit(record, (box_x + 20, box_y + 90))
        elif best_steps:
            best = self.font_small.render(f"Best: {best_steps} steps", True, COLOR_TEXT_DIM)
            self.screen.blit(best, (box_x + 20, box_y + 92))

        hint = self.font_small.render(
            "Press any key or click to continue...", True, COLOR_TEXT_DIM
        )
        self.screen.blit(hint, (box_x + 20, box_y + box_h - 30))

    def draw_overlay_game_over(self, step_count):
        """Draw the game-over overlay with a Try Again button."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        box_w, box_h = 320, 160
        box_x = (WINDOW_WIDTH - box_w) // 2
        box_y = (WINDOW_HEIGHT - box_h) // 2
        pygame.draw.rect(self.screen, (50, 30, 30), (box_x, box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(
            self.screen, COLOR_GAMEOVER, (box_x, box_y, box_w, box_h), 2, border_radius=8
        )

        title = self.font_large.render("GAME OVER", True, COLOR_GAMEOVER)
        self.screen.blit(title, (box_x + 20, box_y + 20))

        info = self.font_medium.render(f"Steps: {step_count}", True, COLOR_TEXT)
        self.screen.blit(info, (box_x + 20, box_y + 55))

        self._overlay_buttons = []
        button_y = box_y + box_h - 45
        button_h = 24
        button_padding = 12

        buttons_data = [("[R] Reset", "reset"), ("[Esc] Menu", "menu")]
        x = box_x + 20
        for label, action_id in buttons_data:
            text_width = self.font_small.size(label)[0]
            button_w = text_width + button_padding * 2
            button_rect = pygame.Rect(x, button_y, button_w, button_h)

            is_hovered = self._hovered_button == action_id
            color = COLOR_BUTTON_HOVER if is_hovered else COLOR_BUTTON_BG
            pygame.draw.rect(self.screen, color, button_rect, border_radius=4)
            border_color = COLOR_HIGHLIGHT if is_hovered else COLOR_BUTTON_BORDER
            pygame.draw.rect(self.screen, border_color, button_rect, 1, border_radius=4)

            text = self.font_small.render(label, True, COLOR_TEXT)
            text_x = x + (button_w - text.get_width()) // 2
            text_y = button_y + (button_h - text.get_height()) // 2
            self.screen.blit(text, (text_x, text_y))

            self._overlay_buttons.append((button_rect, action_id))
            x += button_w + 15

    def draw_overlay_all_complete(self, game_id, total_steps, total_time_ms):
        """Draw the all-levels-complete overlay with a Back to Menu button."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        box_w, box_h = 400, 200
        box_x = (WINDOW_WIDTH - box_w) // 2
        box_y = (WINDOW_HEIGHT - box_h) // 2
        pygame.draw.rect(self.screen, (30, 50, 30), (box_x, box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(
            self.screen, COLOR_HIGHLIGHT, (box_x, box_y, box_w, box_h), 2, border_radius=8
        )

        title = self.font_large.render("ALL LEVELS COMPLETE!", True, COLOR_HIGHLIGHT)
        title_x = box_x + (box_w - title.get_width()) // 2
        self.screen.blit(title, (title_x, box_y + 20))

        game_text = self.font_medium.render(f"Game: {game_id}", True, COLOR_TEXT)
        game_x = box_x + (box_w - game_text.get_width()) // 2
        self.screen.blit(game_text, (game_x, box_y + 60))

        elapsed_s = total_time_ms // 1000
        stats_text = self.font_medium.render(
            f"Steps: {total_steps}   Time: {elapsed_s // 60:02d}:{elapsed_s % 60:02d}",
            True,
            COLOR_TEXT,
        )
        stats_x = box_x + (box_w - stats_text.get_width()) // 2
        self.screen.blit(stats_text, (stats_x, box_y + 88))

        hint = self.font_small.render(
            "Press any key or click to return to menu...", True, COLOR_TEXT_DIM
        )
        hint_x = box_x + (box_w - hint.get_width()) // 2
        self.screen.blit(hint, (hint_x, box_y + box_h - 30))
