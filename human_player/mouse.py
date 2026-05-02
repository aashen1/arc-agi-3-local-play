import ctypes
import re
import sys
import atexit

kernel32 = ctypes.windll.kernel32

STD_OUTPUT_HANDLE = -11
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

SGR_MOUSE_RE = re.compile(r'\x1b\[<(\d+);(\d+);(\d+)([Mm])')

GRID_HEADER_ROWS = 2
GRID_CELL_WIDTH = 2

_mouse_enabled = False
_vt_enabled = False


def _enable_vt_processing() -> bool:
    global _vt_enabled
    try:
        h_out = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(h_out, ctypes.byref(mode))
        if mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING:
            _vt_enabled = True
            return True
        result = kernel32.SetConsoleMode(
            h_out, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
        )
        _vt_enabled = result != 0
        return _vt_enabled
    except Exception:
        return False


def enable_mouse_tracking() -> bool:
    global _mouse_enabled
    if not _enable_vt_processing():
        return False
    try:
        sys.stdout.write('\x1b[?1000h\x1b[?1006h')
        sys.stdout.flush()
        _mouse_enabled = True
        atexit.register(disable_mouse_tracking)
        return True
    except Exception:
        return False


def disable_mouse_tracking():
    global _mouse_enabled
    if _mouse_enabled:
        try:
            sys.stdout.write('\x1b[?1006l\x1b[?1000l')
            sys.stdout.flush()
        except Exception:
            pass
        _mouse_enabled = False


def parse_mouse_event(buf: str) -> dict | None:
    m = SGR_MOUSE_RE.search(buf)
    if not m:
        return None
    button = int(m.group(1))
    col = int(m.group(2))
    row = int(m.group(3))
    is_press = m.group(4) == 'M'
    if button == 0 and is_press:
        return {
            'col': col - 1,
            'row': row - 1,
            'button': button,
            'is_press': is_press,
            'raw': buf[m.start():m.end()],
        }
    return {
        'col': col - 1,
        'row': row - 1,
        'button': button,
        'is_press': is_press,
        'raw': buf[m.start():m.end()],
        '_skip': True,
    }


def terminal_to_grid(col: int, row: int) -> tuple[int, int]:
    gx = col // GRID_CELL_WIDTH
    gy = row - GRID_HEADER_ROWS
    return gx, gy
