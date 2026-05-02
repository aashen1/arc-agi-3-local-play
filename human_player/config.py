import json
import os
from arcengine import GameAction

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RECORDS_DIR = os.path.join(DATA_DIR, "records")
RECORDINGS_DIR = os.path.join(DATA_DIR, "recordings")
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")
USER_CONFIG_FILE = os.path.join(DATA_DIR, "user_config.json")

KEYMAP_WASD = {
    'w': GameAction.ACTION1,
    's': GameAction.ACTION2,
    'a': GameAction.ACTION3,
    'd': GameAction.ACTION4,
    ' ': GameAction.ACTION5,
    'z': GameAction.ACTION7,
    'r': GameAction.RESET,
}

KEYMAP_ARROWS = {
    '\x00H': GameAction.ACTION1,
    '\x00P': GameAction.ACTION2,
    '\x00K': GameAction.ACTION3,
    '\x00M': GameAction.ACTION4,
    'f': GameAction.ACTION5,
    'z': GameAction.ACTION7,
    'r': GameAction.RESET,
}

ACTION_LABELS = {
    GameAction.ACTION1: "↑ 上",
    GameAction.ACTION2: "↓ 下",
    GameAction.ACTION3: "← 左",
    GameAction.ACTION4: "→ 右",
    GameAction.ACTION5: "交互",
    GameAction.ACTION6: "点击",
    GameAction.ACTION7: "撤销",
    GameAction.RESET: "重置",
}

WASD_HELP = {
    'w': "↑", 's': "↓", 'a': "←", 'd': "→",
    'Space': "交互", 'z': "撤销", 'r': "重置",
    'c': "输入坐标", 'q': "退出",
}

ARROW_HELP = {
    '↑': "↑", '↓': "↓", '←': "←", '→': "→",
    'f': "交互", 'z': "撤销", 'r': "重置",
    'c': "输入坐标", 'q': "退出",
}

RENDER_MODE_FAST = "terminal-fast"
RENDER_MODE_NORMAL = "terminal"


def _load_user_config() -> dict:
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_user_config(cfg: dict):
    os.makedirs(os.path.dirname(USER_CONFIG_FILE), exist_ok=True)
    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_fast_render() -> bool:
    return _load_user_config().get("fast_render", True)


def set_fast_render(enabled: bool):
    cfg = _load_user_config()
    cfg["fast_render"] = enabled
    _save_user_config(cfg)


def get_render_mode() -> str:
    return RENDER_MODE_FAST if get_fast_render() else RENDER_MODE_NORMAL
