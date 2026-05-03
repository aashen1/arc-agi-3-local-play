# Pygame 全链路迁移计划

## 目标

将 human_player 从「rich 终端菜单 + arc_agi 内置终端渲染 + msvcrt 键盘输入」的混合架构，迁移为**纯 Pygame 单窗口应用**。用户启动后直接进入 Pygame 窗口，所有交互（菜单选择、游戏游玩、鼠标点击、设置）均在 Pygame 内完成，终端窗口可最小化或忽略。

## 架构变更

### 现有架构（废弃）

```
终端窗口
├── rich 菜单（游戏选择、设置、统计）
├── arc_agi 内置终端渲染（64×64 网格）
├── msvcrt 键盘输入
└── VT 鼠标追踪（Git Bash 下不可用）
```

### 新架构

```
Pygame 窗口（唯一交互界面）
├── 主菜单画面（游戏列表、设置、统计）
├── 游戏画面（自定义渲染 64×64 网格 + HUD）
├── Pygame 键盘事件（WASD / 方向键 均原生支持）
├── Pygame 鼠标事件（像素精确 → 网格坐标）
└── 状态覆盖层（关卡完成、游戏结束、全部通关）
```

### 模块变更一览

| 模块 | 变更 | 说明 |
|------|------|------|
| `__main__.py` | **重写** | Pygame 主循环 + 状态机 |
| `config.py` | **重写** | Pygame 常量（窗口尺寸、调色板、键位） |
| `renderer.py` | **新建** | 网格渲染 + HUD + 鼠标悬停高亮 |
| `menu.py` | **重写** | Pygame 菜单画面（替代 rich） |
| `game_manager.py` | **修改** | 去掉 render_mode，手动读取帧数据 |
| `level_manager.py` | **不变** | 纯数据层 |
| `stats_manager.py` | **不变** | 纯数据层 |
| `recording.py` | **不变** | 纯数据层 |
| `mouse.py` | **删除** | Pygame 原生鼠标支持，不再需要 |

## 详细设计

### 1. 窗口布局

```
┌─────────────────────────────────────────────────────┐
│  ARC-AGI-3 人类玩家控制台          WASD │ 关卡 3/5  │  ← 顶部 HUD 栏 (40px)
├────────────────────────────────┬────────────────────┤
│                                │  步数: 12          │
│                                │  ⏱ 00:23          │
│     64×64 网格渲染区域          │                    │
│     (576×576 像素)             │  可用动作:          │
│     cell_size = 9              │  ↑↓←→ Space Z R   │
│                                │                    │
│                                │  鼠标: (32, 15)    │  ← 悬停时显示坐标
│                                │                    │
│                                │  [ESC] 返回菜单     │
├────────────────────────────────┴────────────────────┤
│  点击网格执行 ACTION6 │ 按 C 输入坐标               │  ← 底部提示栏 (30px)
└─────────────────────────────────────────────────────┘
```

- 窗口总尺寸：800×640（网格 576 + 右侧面板 224，顶部 40 + 底部 30）
- cell_size = 9 像素（64×9 = 576）
- 右侧面板：步数、计时、可用动作、鼠标坐标、操作提示

### 2. 画面状态机

```
                    ┌──────────┐
                    │  主菜单   │
                    └────┬─────┘
              ┌──────────┼──────────┐
              │          │          │
        ┌─────▼──┐ ┌────▼────┐ ┌──▼──────┐
        │ 游戏画面 │ │ 统计画面 │ │ 设置画面 │
        └─────┬──┘ └────┬────┘ └──┬──────┘
              │          │         │
              │    ESC 返回主菜单   │
              │                     │
        ┌─────▼──────────┐         │
        │ 覆盖层（完成/结束）│        │
        └────────────────┘         │
              │                     │
              └─────────────────────┘
```

状态枚举：`MAIN_MENU` / `GAME` / `STATS` / `SETTINGS` / `RESUME_PROMPT`

### 3. config.py 重写

```python
import pygame
from arcengine import GameAction

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 640
FPS = 30

CELL_SIZE = 9
GRID_WIDTH = 64
GRID_HEIGHT = 64
GRID_PIXEL_W = GRID_WIDTH * CELL_SIZE   # 576
GRID_PIXEL_H = GRID_HEIGHT * CELL_SIZE  # 576
GRID_OFFSET_X = 0
GRID_OFFSET_Y = 40

HUD_TOP_HEIGHT = 40
HUD_BOTTOM_HEIGHT = 30
PANEL_WIDTH = WINDOW_WIDTH - GRID_PIXEL_W  # 224

ARC_PALETTE = [
    (255, 255, 255),  # 0  White
    (204, 204, 204),  # 1  Off-white
    (153, 153, 153),  # 2  Neutral Light
    (102, 102, 102),  # 3  Neutral
    (51, 51, 51),     # 4  Off Black
    (0, 0, 0),        # 5  Black
    (229, 58, 163),   # 6  Magenta
    (255, 123, 204),  # 7  Magenta Light
    (249, 60, 49),    # 8  Red
    (30, 147, 255),   # 9  Blue
    (136, 216, 241),  # 10 Blue Light
    (255, 220, 0),    # 11 Yellow
    (255, 133, 27),   # 12 Orange
    (146, 18, 49),    # 13 Maroon
    (79, 204, 48),    # 14 Green
    (163, 86, 214),   # 15 Purple
]

COLOR_BG = (30, 30, 30)
COLOR_PANEL = (40, 40, 50)
COLOR_TEXT = (220, 220, 220)
COLOR_HIGHLIGHT = (255, 220, 0)
COLOR_WIN = (79, 204, 48)
COLOR_GAMEOVER = (249, 60, 49)
COLOR_ACCENT = (30, 147, 255)

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
```

### 4. renderer.py — 网格渲染器

核心职责：
- 将 `FrameDataRaw.frame`（64×64 numpy 数组）渲染到 Pygame Surface
- 绘制 HUD 信息（步数、时间、关卡、可用动作）
- 绘制鼠标悬停高亮
- 绘制状态覆盖层（WIN / GAME_OVER）
- 绘制鼠标光标坐标提示

关键方法：
```python
class Renderer:
    def __init__(self, screen: pygame.Surface)
    def draw_frame(self, frame, mouse_grid_pos, step_count, elapsed_ms,
                   levels_completed, max_levels, available_actions, keymap_scheme, game_id)
    def draw_grid(self, frame, mouse_grid_pos)
    def draw_hud_top(self, game_id, levels_completed, max_levels, keymap_scheme)
    def draw_hud_bottom(self, available_actions, mouse_grid_pos)
    def draw_panel(self, step_count, elapsed_ms, available_actions, keymap_scheme, mouse_grid_pos)
    def draw_overlay_win(self, level_index, steps, time_ms, best_steps, best_time_ms)
    def draw_overlay_game_over(self, step_count)
    def draw_overlay_all_complete(self, game_id, total_steps, total_time_ms)
    def pixel_to_grid(self, pixel_x, pixel_y) -> tuple[int, int]
```

**鼠标坐标转换**（确定性，无偏移问题）：
```python
def pixel_to_grid(self, px, py):
    gx = (px - GRID_OFFSET_X) // CELL_SIZE
    gy = (py - GRID_OFFSET_Y) // CELL_SIZE
    if 0 <= gx < 64 and 0 <= gy < 64:
        return gx, gy
    return None, None
```

### 5. menu.py 重写 — Pygame 菜单

用 Pygame 绘制所有菜单画面，不再依赖 rich：

| 画面 | 内容 | 交互 |
|------|------|------|
| 主菜单 | 标题 + 游戏列表（卡片式） | 鼠标点击/数字键选择 |
| 统计画面 | 按游戏分组的成绩表格 | ESC 返回 |
| 设置画面 | 键位方案选择 | 鼠标点击/快捷键 |
| 续关提示 | 继续上次/从头开始 | 鼠标点击/C/N 键 |

菜单项用 Pygame Rect 做碰撞检测，支持鼠标点击选择。

### 6. game_manager.py 修改

关键变更：
- `start_game()` 不再传 `render_mode`，改为 `arc.make(game_id)` 不带渲染参数
- 从 `env.observation_space.frame` 手动读取帧数据
- 去掉 `render_mode` 属性和相关配置

```python
def start_game(self, game_id: str) -> bool:
    self.env = self.arc.make(game_id)  # 不带 render_mode
    obs = self.env.reset()
    ...
```

### 7. __main__.py 重写 — Pygame 主循环

```python
def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("ARC-AGI-3 人类玩家控制台")
    clock = pygame.time.Clock()

    game_manager = GameManager()
    renderer = Renderer(screen)
    level_manager = LevelManager()
    stats_manager = StatsManager()
    recording_manager = RecordingManager()

    state = "MAIN_MENU"
    keymap_scheme = "wasd"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _cleanup_and_exit(game_manager, recording_manager)
                return

            if state == "MAIN_MENU":
                result = menu.handle_event(event, ...)
                # result → game_id / "SETTINGS" / "STATS" / None(quit)
            elif state == "GAME":
                action, data = _handle_game_event(event, keymap_scheme, renderer, game_manager)
                if action:
                    obs = game_manager.execute_action(action, data)
                    ...

        # 渲染
        if state == "MAIN_MENU":
            menu.draw(screen, ...)
        elif state == "GAME":
            frame = _get_current_frame(game_manager)
            renderer.draw_frame(frame, mouse_pos, ...)
        elif state == "STATS":
            menu.draw_stats(screen, ...)
        elif state == "SETTINGS":
            menu.draw_settings(screen, ...)

        pygame.display.flip()
        clock.tick(FPS)
```

### 8. CLI 模式保留

- 现有的终端模式代码保留在 `__main__.py` 中作为 `--cli` 参数的分支
- 默认启动 Pygame 模式
- `pixi run human-play` → Pygame 模式
- `pixi run human-play --cli` → 终端模式（仅键盘，无鼠标）

## 实施步骤

### 步骤 1：安装 pygame-ce 依赖

- 在 `pixi.toml` 的 `[pypi-dependencies]` 中添加 `pygame-ce = ">=2.5.7"`
- 运行 `pixi install` 验证安装成功
- 运行 `pixi run python -c "import pygame; print(pygame.ver)"` 验证

### 步骤 2：重写 config.py

- 替换所有终端相关常量为 Pygame 常量
- 键位映射从字符串键改为 `pygame.K_*` 常量
- 添加窗口尺寸、调色板、颜色主题等配置
- 保留数据路径常量（DATA_DIR 等）

### 步骤 3：新建 renderer.py

- 实现 `Renderer` 类
- `draw_grid()` — 遍历 64×64 数组，用 `pygame.draw.rect` 绘制
- `draw_hud_top/bottom()` — 绘制信息栏
- `draw_panel()` — 绘制右侧面板
- `draw_overlay_*()` — 绘制状态覆盖层
- `pixel_to_grid()` — 像素坐标转网格坐标
- 鼠标悬停高亮：在鼠标所在格子画半透明边框

### 步骤 4：重写 menu.py

- 用 Pygame 绘制所有菜单画面
- 主菜单：游戏列表 + 鼠标点击选择
- 统计画面：成绩表格
- 设置画面：键位方案切换
- 续关提示：继续/从头/返回

### 步骤 5：修改 game_manager.py

- `start_game()` 不传 render_mode
- 去掉 render_mode 相关属性和方法
- 保留其他所有逻辑不变

### 步骤 6：重写 __main__.py

- Pygame 初始化 + 主循环 + 状态机
- 事件分发：根据当前状态处理键盘/鼠标事件
- 游戏内事件处理：
  - 键盘 → 查 keymap → GameAction
  - 鼠标点击 → pixel_to_grid → ACTION6
  - ESC → 返回主菜单
- CLI 模式作为 `--cli` 参数分支保留

### 步骤 7：删除 mouse.py

- Pygame 原生鼠标支持，不再需要 VT 鼠标追踪模块

### 步骤 8：更新 pixi task

- `human-play` 默认启动 Pygame 模式
- 可选添加 `human-play-cli` task 用于终端模式

### 步骤 9：测试验证

- 启动 Pygame 窗口，验证主菜单显示
- 选择游戏，验证网格渲染正确
- 测试 WASD / 方向键控制
- 测试鼠标点击 → ACTION6
- 测试鼠标悬停高亮
- 测试关卡完成/游戏结束覆盖层
- 测试 ESC 返回菜单
- 测试 CLI 模式仍可用

## 依赖变更

```toml
# pixi.toml [pypi-dependencies]
arc-agi = ">=0.9.8, <0.10"
rich = ">=13.0"          # CLI 模式仍需要
pygame-ce = ">=2.5.7"    # 新增
```

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| pygame-ce 在 Python 3.14.4 上安装失败 | 已确认 2.5.7 支持 3.10-3.14；若失败可降级 Python |
| 帧数据格式不确定 | 先写小脚本测试 `env.observation_space.frame` 的数据结构 |
| Pygame 字体渲染中文乱码 | 使用 pygame.freetype 或系统字体，中文文本用英文替代 |
| 网格渲染性能 | 64×64 = 4096 个 rect，Pygame 轻松处理；可用 Surface.blit 优化 |
