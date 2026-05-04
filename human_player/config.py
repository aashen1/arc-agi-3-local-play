import json
import os

import pygame
from arcengine import GameAction

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PLAYERS_DIR = os.path.join(DATA_DIR, "players")
RECORDS_DIR = os.path.join(DATA_DIR, "records")
RECORDINGS_DIR = os.path.join(DATA_DIR, "recordings")
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")
USER_CONFIG_FILE = os.path.join(DATA_DIR, "user_config.json")

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 640
DESIGN_WIDTH = 800
DESIGN_HEIGHT = 640
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 640
FPS = 30

CELL_SIZE = 9
GRID_SIZE = 64
GRID_PIXEL = GRID_SIZE * CELL_SIZE
GRID_OFFSET_X = 0
GRID_OFFSET_Y = 40

HUD_TOP_H = 40
HUD_BOTTOM_H = 30
PANEL_WIDTH = WINDOW_WIDTH - GRID_PIXEL

ARC_PALETTE = [
    (255, 255, 255),
    (204, 204, 204),
    (153, 153, 153),
    (102, 102, 102),
    (51, 51, 51),
    (0, 0, 0),
    (229, 58, 163),
    (255, 123, 204),
    (249, 60, 49),
    (30, 147, 255),
    (136, 216, 241),
    (255, 220, 0),
    (255, 133, 27),
    (146, 18, 49),
    (79, 204, 48),
    (163, 86, 214),
]

COLOR_BG = (30, 30, 30)
COLOR_PANEL = (40, 40, 50)
COLOR_TEXT = (220, 220, 220)
COLOR_TEXT_DIM = (140, 140, 140)
COLOR_HIGHLIGHT = (255, 220, 0)
COLOR_WIN = (79, 204, 48)
COLOR_GAMEOVER = (249, 60, 49)
COLOR_DANGER = (220, 50, 50)
COLOR_DANGER_DIM = (120, 40, 40)
COLOR_ACCENT = (30, 147, 255)
COLOR_HOVER = (255, 255, 255, 80)
COLOR_BUTTON_BG = (60, 60, 70)
COLOR_BUTTON_HOVER = (80, 80, 90)
COLOR_BUTTON_BORDER = (100, 100, 110)

KEYMAP_WASD = {
    pygame.K_w: GameAction.ACTION1,
    pygame.K_s: GameAction.ACTION2,
    pygame.K_a: GameAction.ACTION3,
    pygame.K_d: GameAction.ACTION4,
    pygame.K_SPACE: GameAction.ACTION5,
    pygame.K_z: GameAction.ACTION7,
    pygame.K_r: GameAction.RESET,
}

KEYMAP_ARROWS = {
    pygame.K_UP: GameAction.ACTION1,
    pygame.K_DOWN: GameAction.ACTION2,
    pygame.K_LEFT: GameAction.ACTION3,
    pygame.K_RIGHT: GameAction.ACTION4,
    pygame.K_f: GameAction.ACTION5,
    pygame.K_z: GameAction.ACTION7,
    pygame.K_r: GameAction.RESET,
}

ACTION_LABELS = {
    GameAction.ACTION1: "Up",
    GameAction.ACTION2: "Down",
    GameAction.ACTION3: "Left",
    GameAction.ACTION4: "Right",
    GameAction.ACTION5: "Interact",
    GameAction.ACTION6: "Click",
    GameAction.ACTION7: "Undo",
    GameAction.RESET: "Reset",
}

WASD_KEY_LABELS = {
    GameAction.ACTION1: "W",
    GameAction.ACTION2: "S",
    GameAction.ACTION3: "A",
    GameAction.ACTION4: "D",
    GameAction.ACTION5: "Space",
    GameAction.ACTION6: "Mouse",
    GameAction.ACTION7: "Z",
    GameAction.RESET: "R",
}

ARROW_KEY_LABELS = {
    GameAction.ACTION1: "Up",
    GameAction.ACTION2: "Down",
    GameAction.ACTION3: "Left",
    GameAction.ACTION4: "Right",
    GameAction.ACTION5: "F",
    GameAction.ACTION6: "Mouse",
    GameAction.ACTION7: "Z",
    GameAction.RESET: "R",
}


def _load_user_config() -> dict:
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JsonDecodeError, OSError):
            pass
    return {}


def _save_user_config(cfg: dict):
    os.makedirs(os.path.dirname(USER_CONFIG_FILE), exist_ok=True)
    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_keymap_scheme() -> str:
    """Return the current keymap scheme name, either "wasd" or "arrows"."""
    return _load_user_config().get("keymap", "wasd")


def set_keymap_scheme(scheme: str):
    """Persist the keymap scheme choice.

    Args:
        scheme: Either "wasd" or "arrows".
    """
    cfg = _load_user_config()
    cfg["keymap"] = scheme
    _save_user_config(cfg)


def get_keymap() -> dict:
    """Return the pygame key-to-GameAction mapping for the current scheme."""
    return KEYMAP_WASD if get_keymap_scheme() == "wasd" else KEYMAP_ARROWS


def get_key_labels() -> dict:
    """Return the GameAction-to-display-label mapping for the current scheme."""
    return WASD_KEY_LABELS if get_keymap_scheme() == "wasd" else ARROW_KEY_LABELS


def get_view_mode() -> str:
    """Return the current grid view mode, either "grid" or "list"."""
    return _load_user_config().get("view_mode", "grid")


def set_view_mode(mode: str):
    """Persist the grid view mode choice.

    Args:
        mode: Either "grid" or "list".
    """
    cfg = _load_user_config()
    cfg["view_mode"] = mode
    _save_user_config(cfg)


SYNC_MODE_CONSERVATIVE = "conservative"
SYNC_MODE_AUTO = "auto"


def get_sync_mode() -> str:
    """Return the current sync mode, defaulting to conservative."""
    mode = _load_user_config().get("sync_mode", SYNC_MODE_CONSERVATIVE)
    if mode not in (SYNC_MODE_CONSERVATIVE, SYNC_MODE_AUTO):
        mode = SYNC_MODE_CONSERVATIVE
    return mode


def set_sync_mode(mode: str):
    """Persist the sync mode choice.

    Args:
        mode: Either "conservative" or "auto".
    """
    cfg = _load_user_config()
    cfg["sync_mode"] = mode
    _save_user_config(cfg)
