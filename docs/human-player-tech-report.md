# ARC-AGI-3 人类玩家控制台 — 技术报告

## 1. 项目概述

为 ARC-AGI-3 基准测试平台开发了一套图形化人类游玩系统，基于 Pygame 构建，实现键盘/鼠标控制、关卡管理、成绩统计、多玩家支持和操作录像功能。系统自行渲染 64×64 网格，提供完整的图形界面体验。

## 2. 技术选型与决策

### 2.1 渲染：Pygame 自定义渲染

**最终选择**：Pygame-ce（Community Edition）

**选择理由**：
- 跨平台支持（Windows/Linux/macOS）
- 原生支持键盘和鼠标事件
- 像素级精确的鼠标坐标映射
- 简单高效的 2D 渲染 API
- pygame-ce 是活跃维护的社区版本

**架构决策**：不使用 ARC-AGI-3 内置的 `render_mode="terminal"`，而是手动从 `env.observation_space.frame` 读取帧数据，在 Pygame 中自行渲染。这样做的好处：
- 完全控制渲染样式和布局
- 可以叠加 HUD 信息
- 鼠标坐标可以精确映射到网格
- 单一窗口，用户体验更好

### 2.2 输入：Pygame 事件系统

**键盘输入**：
- Pygame 的 `pygame.KEYDOWN` 事件直接提供 `event.key`（如 `pygame.K_w`）
- WASD 和方向键都原生支持，无需处理终端转义序列
- 键位映射使用 `pygame.K_*` 常量作为 key

**鼠标输入**：
- `pygame.MOUSEBUTTONDOWN` 事件提供精确的像素坐标
- 通过简单公式转换为网格坐标：
  ```python
  gx = (px - GRID_OFFSET_X) // CELL_SIZE
  gy = (py - GRID_OFFSET_Y) // CELL_SIZE
  ```
- 鼠标悬停时高亮当前格子，提供视觉反馈

### 2.3 状态机：单窗口多画面

主循环使用状态机管理不同画面：

```
MAIN_MENU → GAME → MAIN_MENU
    ↓         ↓
SETTINGS   STATS
    ↓         ↓
MAIN_MENU  MAIN_MENU
```

状态枚举：`MAIN_MENU` / `GAME` / `STATS` / `SETTINGS` / `PLAYER_SELECT` / `RESUME_PROMPT`

## 3. 模块架构

```
human_player/
├── __init__.py            # 空文件，包标记
├── __main__.py            # 入口 + Pygame 主循环 + 状态机
├── config.py              # 常量：窗口尺寸、调色板、键位映射
├── game_manager.py        # Arcade/Environment 交互封装
├── renderer.py            # Pygame 网格渲染 + HUD
├── menu.py                # Pygame 菜单画面
├── level_manager.py       # 关卡进度 JSON 读写
├── stats_manager.py       # 成绩记录 JSON 读写
├── player_manager.py      # 多玩家管理
├── recording.py           # 轻量级操作录像（JSONL）
└── official_recording.py  # 官方格式录像
```

### 3.1 __main__.py — 主循环

核心流程：

```
main() → pygame.init() → while True:
    for event in pygame.event.get():
        if state == "MAIN_MENU":
            handle_menu_event() → game_id / "settings" / "stats" / "player" / None(quit)
        elif state == "GAME":
            handle_game_event() → GameAction / "exit"
        elif state == "SETTINGS":
            handle_settings_event() → keymap change / "back"
        ...

    if state == "MAIN_MENU":
        menu_renderer.draw_main_menu()
    elif state == "GAME":
        renderer.draw_frame()
        if overlay_state:
            renderer.draw_overlay_*()
    ...

    pygame.display.flip()
    clock.tick(FPS)
```

**事件处理分离**：每个状态有独立的事件处理函数，返回值驱动状态转换。

**覆盖层机制**：游戏内使用 `overlay_state` 变量管理 WIN / GAME_OVER / ALL_COMPLETE 覆盖层，不影响底层游戏状态。

### 3.2 renderer.py — Pygame 渲染器

核心职责：
- 将 `FrameDataRaw.frame`（64×64 numpy 数组）渲染到 Pygame Surface
- 绘制 HUD 信息（步数、时间、关卡、可用动作）
- 绘制鼠标悬停高亮
- 绘制状态覆盖层（WIN / GAME_OVER / ALL_COMPLETE）

**网格渲染**：

```python
def _draw_grid(self, frame, mouse_grid_pos):
    self._grid_surface.fill(COLOR_BG)
    for y in range(grid.shape[0]):
        for x in range(grid.shape[1]):
            color_idx = int(grid[y, x])
            color = ARC_PALETTE[color_idx]
            pygame.draw.rect(
                self._grid_surface, color,
                (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE),
            )
    # 鼠标悬停高亮
    if mouse_grid_pos[0] is not None:
        gx, gy = mouse_grid_pos
        self._grid_surface.blit(self._hover_surface, (gx * CELL_SIZE, gy * CELL_SIZE))
```

**像素到网格坐标转换**：

```python
def pixel_to_grid(self, px, py):
    gx = (px - GRID_OFFSET_X) // CELL_SIZE
    gy = (py - GRID_OFFSET_Y) // CELL_SIZE
    if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
        return gx, gy
    return None, None
```

### 3.3 menu.py — Pygame 菜单

用 Pygame 绘制所有菜单画面，替代原来的 rich 终端菜单：

| 画面 | 内容 | 交互 |
|------|------|------|
| 主菜单 | 标题 + 游戏列表（卡片式） | 鼠标点击/数字键选择 |
| 玩家选择 | 玩家列表 + 新建输入框 | 鼠标点击/键盘输入 |
| 统计画面 | 按游戏分组的成绩表格 | ESC 返回 |
| 设置画面 | 键位方案选择 | 鼠标点击 |
| 续关提示 | 继续/从头开始/返回 | 鼠标点击/快捷键 |

**碰撞检测**：使用 `pygame.Rect.collidepoint(pos)` 检测鼠标点击位置。

### 3.4 config.py — 配置常量

窗口布局：

```python
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 640
CELL_SIZE = 9
GRID_SIZE = 64
GRID_PIXEL = 576  # 64 * 9
GRID_OFFSET_X = 0
GRID_OFFSET_Y = 40
HUD_TOP_H = 40
HUD_BOTTOM_H = 30
PANEL_WIDTH = 224  # 800 - 576
```

ARC 调色板（16 色）：

```python
ARC_PALETTE = [
    (255, 255, 255),  # 0  White
    (204, 204, 204),  # 1  Off-white
    ...
    (163, 86, 214),   # 15 Purple
]
```

键位映射：

```python
KEYMAP_WASD = {
    pygame.K_w: GameAction.ACTION1,
    pygame.K_s: GameAction.ACTION2,
    pygame.K_a: GameAction.ACTION3,
    pygame.K_d: GameAction.ACTION4,
    pygame.K_SPACE: GameAction.ACTION5,
    pygame.K_z: GameAction.ACTION7,
    pygame.K_r: GameAction.RESET,
}
```

### 3.5 game_manager.py — 游戏交互封装

封装了 `arc_agi.Arcade` 和 `EnvironmentWrapper` 的交互：

| 方法 | 功能 |
|------|------|
| `list_games()` | 调用 `arc.get_environments()` |
| `start_game(game_id)` | 调用 `arc.make(game_id)` + `env.reset()` |
| `execute_action(action, data)` | 调用 `env.step()`，维护步数和时间 |
| `reset_level()` | 调用 `env.reset()`，重置步数和计时 |
| `get_current_frame()` | 从 `env.observation_space.frame` 获取帧数据 |
| `did_level_up()` | 检测 `levels_completed` 是否递增 |
| `jump_to_level(level_index)` | 跳转到指定关卡（继续游戏功能） |

**关键点**：不传 `render_mode` 参数，让 ARC-AGI-3 不执行内置渲染。

### 3.6 player_manager.py — 多玩家管理

每个玩家有独立的数据目录：

```python
class PlayerManager:
    def get_current_player() -> str
    def set_player(name: str) -> None
    def list_players() -> list[str]
    def get_player_data_dir(name: str = None) -> str  # data/players/{name}/
    def get_recordings_dir(game_id: str) -> str       # data/players/{name}/recordings/{game_id}/
    def get_records_dir() -> str                      # data/players/{name}/records/
    def get_progress_file() -> str                    # data/players/{name}/progress.json
```

当前玩家存储在 `data/user_config.json` 的 `current_player` 字段。

### 3.7 official_recording.py — 官方格式录像

生成与 ARC-AGI-3 官方格式兼容的 JSONL 录像文件：

**每步记录**：

```json
{
  "timestamp": "2026-05-03T14:30:22.123456+00:00",
  "data": {
    "game_id": "ls20-9607627b",
    "frame": [[...], ...],
    "state": "NOT_FINISHED",
    "levels_completed": 2,
    "win_levels": 5,
    "action_input": {"id": 1, "data": {...}, "reasoning": null},
    "guid": "a1b2c3d4-...",
    "full_reset": false,
    "available_actions": [1, 2, 3, 4]
  }
}
```

**录像索引**：`index.json` 记录所有会话，标记 `phase: "learning"` 或 `"practice"`。

### 3.8 level_manager.py — 关卡进度

JSON 文件存储，每次更新立即写盘：

```json
{
  "version": "1.0",
  "games": {
    "ls20": {
      "levels": {
        "0": {
          "completed": true,
          "best_steps": 42,
          "best_time_ms": 83000,
          "completed_at": "2026-05-03T14:30:00+00:00",
          "attempts": 3
        }
      },
      "total_levels": 5
    }
  }
}
```

### 3.9 stats_manager.py — 成绩统计

每个游戏一个 JSON 文件，记录所有尝试：

```json
[
  {
    "level_index": 0,
    "session_id": "ls20_20260503_143022",
    "timestamp": "2026-05-03T14:30:22+08:00",
    "steps": 42,
    "time_ms": 83000,
    "result": "WIN"
  }
]
```

## 4. 数据目录结构

```
data/
├── players/
│   ├── default/
│   │   ├── progress.json          # 关卡进度
│   │   ├── records/               # 成绩记录
│   │   │   ├── ls20.json
│   │   │   └── tu93.json
│   │   └── recordings/            # 官方格式录像
│   │       └── ls20-9607627b/
│   │           ├── index.json
│   │           └── ls20-9607627b.*.recording.jsonl
│   └── alice/
│       └── ...
└── user_config.json              # 用户配置
```

## 5. 依赖清单

| 依赖 | 版本 | 用途 |
|------|------|------|
| `arc-agi` | >=0.9.8, <0.10 | ARC-AGI-3 核心 SDK |
| `pygame-ce` | >=2.5.7, <3 | 图形渲染、输入处理 |
| `rich` | >=13.0 | 保留（未来可能用于 CLI 模式） |
| `numpy` | — | 帧数据处理（arc-agi 依赖） |

## 6. 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `human_player/__init__.py` | 0 | 包标记 |
| `human_player/__main__.py` | ~410 | 入口、Pygame 主循环、状态机 |
| `human_player/config.py` | ~140 | 窗口尺寸、调色板、键位映射 |
| `human_player/game_manager.py` | ~175 | Arcade/Environment 交互封装 |
| `human_player/renderer.py` | ~240 | Pygame 网格渲染 + HUD |
| `human_player/menu.py` | ~330 | Pygame 菜单画面 |
| `human_player/level_manager.py` | ~107 | 关卡进度 JSON 读写 |
| `human_player/stats_manager.py` | ~70 | 成绩记录 JSON 读写 |
| `human_player/player_manager.py` | ~60 | 多玩家管理 |
| `human_player/recording.py` | ~90 | 轻量级录像 JSONL 读写 |
| `human_player/official_recording.py` | ~200 | 官方格式录像 |
| **合计** | **~1820** | |

## 7. 演进历史

### v1：终端版本（已废弃）

- rich 菜单 + ARC-AGI-3 内置终端渲染
- msvcrt 键盘输入（仅 Windows）
- 方向键在 Git Bash 中不工作（VT 转义序列问题）
- ACTION6 只能手动输入坐标

### v2：Pygame 版本（当前）

- 纯 Pygame 单窗口应用
- 跨平台支持
- 精确的鼠标点击支持
- 多玩家系统
- 官方格式录像

## 8. 踩坑记录

### 8.1 FrameDataRaw.frame 的数据结构

`env.observation_space.frame` 返回的数据可能是：
- 3D 列表 `[[[...]]]`（需要取 `[0]`）
- 2D 列表 `[[...]]`
- numpy 数组

需要统一处理：

```python
def get_current_frame(self):
    frame = obs.frame
    if isinstance(frame, list):
        return np.array(frame[0]) if frame else None
    return np.array(frame)
```

### 8.2 关卡总数获取

ARC-AGI-3 API 不直接暴露关卡总数。通过两种方式推断：
1. `FrameDataRaw.win_levels` — 达到 WIN 所需的关卡数
2. 游玩过程中 `levels_completed` 的最大值

### 8.3 WIN 后的关卡推进

当 `obs.state == GameState.WIN` 时，需要调用 `env.reset()` 进入下一关。`reset()` 返回的 `FrameDataRaw` 中 `levels_completed` 已经是递增后的值。

### 8.4 Pygame 字体

使用 `pygame.font.SysFont("consolas", ...)` 加载系统字体。Consolas 在 Windows 上预装，等宽字体适合显示游戏信息。

## 9. 未来改进方向

1. **录像回放**：读取 JSONL 文件，逐步重放动作序列
2. **RHAE 评分对比**：加载官方人类基线数据，计算 RHAE 分数
3. **自定义键位**：允许用户自定义键位映射
4. **窗口缩放**：支持调整窗口大小
5. **关卡编辑器**：可视化编辑关卡
