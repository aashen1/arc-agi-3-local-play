# 游戏控制映射与关卡管理系统开发计划（修订版）

## 一、核心设计理念变更

### 1.1 原方案问题

原方案完全从零构建 Pygame GUI，忽略了 ARC-AGI-3 已提供的终端渲染能力：

`render_mode="terminal"` 已能将 64x64 网格以彩色文本渲染到终端

* `render_mode="human"` 已能通过 Matplotlib 弹窗渲染图形
* 自定义 `renderer` 回调可完全控制渲染逻辑
* 重新造轮子构建渲染系统是冗余的

### 1.2 修订方案：终端优先 + 渐进增强

**核心思路**：复用 ARC-AGI-3 内置渲染，只补充缺失的输入层和管理功能。

| 层次  | 功能                 | 来源                              |
| --- | ------------------ | ------------------------------- |
| 显示层 | 网格渲染               | **复用** `render_mode="terminal"` |
| 输入层 | 键盘/鼠标 → GameAction | **新建** `pynput` 监听              |
| 菜单层 | 游戏选择、进度展示          | **新建** 终端文本菜单                   |
| 数据层 | 进度/成绩/录像           | **新建** JSON/JSONL 存储            |

**渐进增强路径**：

* **阶段 A**：终端模式（`render_mode="terminal"` + `pynput` 键盘监听）

* **阶段 B**：Matplotlib 模式（`render_mode="human"` + `pynput` 键盘/鼠标监听）

* **阶段 C**（可选）：Pygame 自定义渲染器（如需更丰富的交互体验）

***

## 二、技术选型（修订）

### 2.1 输入捕获：pynput

**选择理由：**

* 跨平台键盘/鼠标监听，Windows 10 兼容

* 无需管理员权限

* 支持非阻塞监听（后台线程）

* 可同时监听键盘和鼠标事件

* 轻量级，无 GUI 依赖

**与 Pygame 方案的对比：**

| 特性   | pynput（终端方案） | Pygame（GUI 方案） |
| ---- | ------------ | -------------- |
| 依赖量  | 1 个库         | 1 个库 + 自建渲染    |
| 渲染   | 复用内置         | 从零构建           |
| 键盘捕获 | ✅            | ✅              |
| 鼠标捕获 | ✅（屏幕坐标）      | ✅（窗口坐标）        |
| 开发量  | 小            | 大              |
| 游戏体验 | 终端文本         | 图形化            |

### 2.2 显示方案：复用 ARC-AGI-3 内置渲染

| 模式              | 命令                                              | 特点              |
| --------------- | ----------------------------------------------- | --------------- |
| `terminal`      | `arc.make("ls20", render_mode="terminal")`      | 终端彩色文本，有帧率限制    |
| `terminal-fast` | `arc.make("ls20", render_mode="terminal-fast")` | 终端彩色文本，无帧率限制    |
| `human`         | `arc.make("ls20", render_mode="human")`         | Matplotlib 弹窗图形 |
| 自定义             | `arc.make("ls20", renderer=my_func)`            | 完全自定义渲染逻辑       |

### 2.3 数据存储：JSON 文件（不变）

### 2.4 录像格式：JSONL（不变，与官方兼容）

***

## 三、系统架构设计（修订）

### 3.1 模块划分

```
human_player/
├── __init__.py
├── __main__.py            # python -m human_player 入口
├── config.py              # 配置常量（键位映射、路径、调色板）
├── input_handler.py       # 输入映射模块（pynput 键盘/鼠标 → GameAction）
├── game_manager.py        # 游戏管理模块（Arcade 交互封装）
├── level_manager.py       # 关卡管理模块（列表、选择、进度）
├── stats_manager.py       # 成绩统计模块（记录、查询、展示）
├── recording.py           # 录像模块（动作记录、JSONL 写入）
└── menu.py                # 终端菜单系统（游戏选择、进度展示、设置）
```

**与原方案的关键差异：**

* ❌ 删除 `renderer.py`（复用内置渲染）

* ❌ 删除 `ui/` 目录（用终端菜单替代）

* ✅ 新增 `menu.py`（终端文本菜单）

* ✅ 新增 `__main__.py`（标准入口）

* ✅ `input_handler.py` 改用 `pynput` 而非 Pygame 事件

### 3.2 核心流程

```
┌──────────────────────────────────────────────────────────┐
│                    程序启动                                │
│                                                          │
│  1. 显示终端菜单（游戏列表 + 进度 + 设置）                 │
│  2. 玩家选择游戏                                          │
│  3. arc.make(game_id, render_mode="terminal")            │
│  4. 启动 pynput 键盘/鼠标监听                             │
│  5. 游戏主循环：                                          │
│     ├─ 键盘事件 → InputHandler → GameAction              │
│     ├─ 鼠标事件 → InputHandler → ACTION6 + (x,y)        │
│     ├─ env.step(action) → 内置渲染自动刷新终端            │
│     ├─ RecordingManager 记录每步                          │
│     └─ 检测 WIN/GAME_OVER → 更新进度和成绩               │
│  6. 玩家按 ESC/Q 退出 → 保存数据 → 返回菜单              │
└──────────────────────────────────────────────────────────┘
```

### 3.3 终端菜单系统

```
╔══════════════════════════════════════════════╗
║        ARC-AGI-3 人类玩家控制台              ║
╠══════════════════════════════════════════════╣
║                                              ║
║  可用游戏：                                   ║
║                                              ║
║  [1] ls20 - Agent Reasoning                  ║
║      进度: ██░░░ 2/5 关卡  最佳: 15步        ║
║                                              ║
║  [2] ft09 - Elementary Logic                 ║
║      进度: ░░░░░ 0/3 关卡                    ║
║                                              ║
║  [3] vc33 - Orchestration                    ║
║      进度: ████░ 4/5 关卡  最佳: 22步        ║
║                                              ║
║  [S] 设置  [V] 查看成绩  [Q] 退出            ║
║                                              ║
║  选择 > _                                    ║
╚══════════════════════════════════════════════╝
```

### 3.4 游戏中 HUD 信息

利用自定义 `renderer` 回调，在终端渲染网格后追加 HUD 信息：

```
[终端网格渲染区域 - 由内置渲染器输出]

─────────────────────────────────────────
🎮 ls20 | 关卡 2/5 | 步数: 12 | ⏱ 00:23
可用动作: ↑↓←→ [Space]交互 [Z]撤销 [R]重置
方案: WASD | [ESC]返回菜单
─────────────────────────────────────────
```

***

## 四、详细实现步骤

### 阶段 1：核心交互层（优先级：最高）

#### 步骤 1.1：项目结构初始化

* 创建 `human_player/` 包目录

* 创建 `human_player/__init__.py` 和 `human_player/__main__.py`

* 创建 `data/` 数据存储目录（`data/records/`, `data/recordings/`）

* 更新 `pixi.toml` 添加 `pynput` 依赖

* 添加 pixi task：`human-play = "python -m human_player"`

#### 步骤 1.2：配置模块 (`config.py`)

```python
from arcengine import GameAction

DATA_DIR = "data"
RECORDS_DIR = "data/records"
RECORDINGS_DIR = "data/recordings"

KEYMAP_WASD = {
    'w': GameAction.ACTION1,
    's': GameAction.ACTION2,
    'a': GameAction.ACTION3,
    'd': GameAction.ACTION4,
    'space': GameAction.ACTION5,
    'z': GameAction.ACTION7,
    'r': GameAction.RESET,
}

KEYMAP_ARROWS = {
    'up': GameAction.ACTION1,
    'down': GameAction.ACTION2,
    'left': GameAction.ACTION3,
    'right': GameAction.ACTION4,
    'f': GameAction.ACTION5,
    'z': GameAction.ACTION7,
    'r': GameAction.RESET,
}

DEFAULT_RENDER_MODE = "terminal"
```

#### 步骤 1.3：输入映射模块 (`input_handler.py`)

核心职责：

* 使用 `pynput` 监听键盘按键，映射为 `GameAction`

* 使用 `pynput` 监听鼠标点击，映射为 `ACTION6`（附带 x,y 坐标）

* 支持键位方案切换（WASD / 方向键）

* 过滤不可用动作（对照 `env.action_space`）

* 提供线程安全的事件队列

关键接口：

```python
import threading
from collections import deque
from pynput import keyboard, mouse
from arcengine import GameAction

class InputHandler:
    def __init__(self, keymap_scheme="wasd"):
        self.keymap = KEYMAP_WASD if keymap_scheme == "wasd" else KEYMAP_ARROWS
        self._event_queue: deque[tuple[GameAction, dict]] = deque()
        self._lock = threading.Lock()
        self._keyboard_listener = None
        self._mouse_listener = None

    def start(self):
        """启动键盘和鼠标监听（后台线程）"""

    def stop(self):
        """停止监听"""

    def get_pending_actions(self) -> list[tuple[GameAction, dict]]:
        """获取所有待处理的动作（线程安全）"""

    def switch_keymap(self, scheme: str):
        """切换键位方案"""

    def _on_key_press(self, key) -> bool:
        """键盘按下回调 → 入队 (GameAction, {})"""

    def _on_mouse_click(self, x, y, button, pressed) -> bool:
        """鼠标点击回调 → 入队 (ACTION6, {"x": gx, "y": gy})"""
```

**pynput 键盘事件处理：**

```python
def _on_key_press(self, key):
    try:
        key_name = key.char.lower()  # 字母键：key.char
    except AttributeError:
        key_name = key.name.lower()  # 特殊键：key.name (up/down/left/right/space)

    if key_name in self.keymap:
        action = self.keymap[key_name]
        with self._lock:
            self._event_queue.append((action, {}))
    return True  # 继续监听
```

**pynput 鼠标事件处理（ACTION6 坐标转换）：**

```python
def _on_mouse_click(self, x, y, button, pressed):
    if button == mouse.Button.left and pressed:
        gx, gy = self._screen_to_grid(x, y)
        if 0 <= gx < 64 and 0 <= gy < 64:
            with self._lock:
                self._event_queue.append((GameAction.ACTION6, {"x": gx, "y": gy}))
    return True

def _screen_to_grid(self, screen_x, screen_y):
    """将屏幕像素坐标转换为网格坐标

    注意：终端模式下，每个网格单元对应终端中的一个字符位置。
    需要根据终端字体大小和窗口位置计算偏移。
    此转换是近似值，精确坐标建议通过键盘输入方式指定。
    """
    char_width = 8   # 终端字符宽度（像素，近似值）
    char_height = 16 # 终端字符高度（像素，近似值）
    term_offset_x = 0
    term_offset_y = 0
    gx = (screen_x - term_offset_x) // char_width
    gy = (screen_y - term_offset_y) // char_height
    return gx, gy
```

**重要说明 — ACTION6 坐标输入的替代方案：**

由于终端模式下鼠标坐标转换精度有限，提供以下备选输入方式：

1. **键盘输入坐标**：按 `C` 键进入坐标输入模式，然后输入 `x,y` 回车确认
2. **鼠标点击**：在 `render_mode="human"`（Matplotlib）模式下，鼠标坐标可精确映射
3. **方向键微调**：先用鼠标大致定位，再用方向键微调

#### 步骤 1.4：游戏管理模块 (`game_manager.py`)

核心职责：

* 封装 `arc_agi.Arcade` 和 `EnvironmentWrapper` 的交互

* 管理游戏会话生命周期

* 维护游戏状态（步数、时间、当前关卡）

* 使用自定义 `renderer` 回调追加 HUD 信息

关键接口：

```python
class GameManager:
    def __init__(self, render_mode="terminal"):
        self.arc = arc_agi.Arcade()
        self.env = None
        self.game_id = None
        self.render_mode = render_mode
        self.step_count = 0
        self.level_start_time = None
        self.levels_completed = 0
        self._hud_callback = None

    def list_games(self) -> list:
        """获取可用游戏列表"""

    def start_game(self, game_id: str) -> bool:
        """启动指定游戏，创建环境并 reset"""

    def execute_action(self, action: GameAction, data: dict = None) -> FrameDataRaw | None:
        """执行动作并更新状态计数"""

    def reset_level(self) -> FrameDataRaw | None:
        """重置当前关卡"""

    def close_game(self):
        """关闭当前游戏"""

    def _create_hud_renderer(self):
        """创建带 HUD 的自定义渲染器

        策略：使用 renderer 回调替代 render_mode，
        在内置渲染逻辑基础上追加 HUD 信息行。
        """

    def get_state_summary(self) -> dict:
        """获取当前游戏状态摘要"""
```

**HUD 渲染器实现策略：**

```python
def _hud_renderer(self, steps: int, frame_data: FrameDataRaw) -> None:
    # 先调用内置终端渲染（通过 render_mode="terminal" 已自动完成）
    # 然后追加 HUD 信息
    state_name = frame_data.state.name
    levels = frame_data.levels_completed
    elapsed = int((time.time() - self.level_start_time) * 1000) if self.level_start_time else 0
    actions = [a.name for a in self._current_action_space]

    print(f"─────────────────────────────────────────")
    print(f"🎮 {self.game_id} | 关卡 {levels+1} | 步数: {steps} | ⏱ {elapsed//1000}s")
    print(f"状态: {state_name} | 可用: {', '.join(actions)}")
    print(f"[ESC]菜单 [R]重置 [Z]撤销 [C]输入坐标")
    print(f"─────────────────────────────────────────")
```

**注意**：如果 `render_mode` 和 `renderer` 同时提供，`renderer` 优先。因此需要选择以下策略之一：

* **策略 A**：只用 `render_mode="terminal"`，HUD 信息在游戏主循环中手动 print

* **策略 B**：只用自定义 `renderer`，在回调中同时渲染网格和 HUD

* **策略 C**：使用 `render_mode="terminal"` + 主循环追加 HUD print

**推荐策略 C**：最简单，复用内置渲染，只在主循环中追加 HUD 输出。

### 阶段 2：菜单与关卡管理（优先级：高）

#### 步骤 2.1：终端菜单模块 (`menu.py`)

核心职责：

* 显示游戏列表和进度

* 接收用户选择

* 显示成绩统计

* 显示/修改设置

关键接口：

```python
class TerminalMenu:
    def __init__(self, game_manager: GameManager, level_manager: LevelManager,
                 stats_manager: StatsManager):
        self.game_manager = game_manager
        self.level_manager = level_manager
        self.stats_manager = stats_manager

    def show_main_menu(self) -> str | None:
        """显示主菜单，返回选择的游戏 ID 或 None（退出）"""

    def show_game_select(self) -> str | None:
        """显示游戏选择界面"""

    def show_stats(self):
        """显示成绩统计"""

    def show_settings(self) -> dict:
        """显示设置界面，返回配置变更"""

    def _render_progress_bar(self, completed: int, total: int, width: int = 10) -> str:
        """渲染进度条字符串"""

    def _clear_screen(self):
        """清屏"""
```

#### 步骤 2.2：关卡管理模块 (`level_manager.py`)

与原方案相同，管理进度数据。

关键变更：关卡总数通过游戏运行时动态获取（`obs.levels_completed` 变化推断），而非预先知道。

```python
class LevelManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.progress_file = os.path.join(data_dir, "progress.json")
        self.progress = self._load_progress()

    def get_game_progress(self, game_id: str) -> dict:
        """获取指定游戏的进度"""

    def update_level_status(self, game_id: str, level_index: int,
                            completed: bool, steps: int, time_ms: int):
        """更新关卡状态"""

    def get_total_levels(self, game_id: str) -> int:
        """获取游戏总关卡数（从进度数据推断，或返回已知值）"""

    def _load_progress(self) -> dict: ...
    def _save_progress(self): ...
```

### 阶段 3：成绩统计与录像（优先级：中）

#### 步骤 3.1：成绩统计模块 (`stats_manager.py`)

与原方案相同。

#### 步骤 3.2：录像模块 (`recording.py`)

与原方案相同，JSONL 格式录像。

**新增功能 — 录像回放：**

```python
class RecordingManager:
    # ... 原有接口 ...

    def replay_recording(self, filepath: str, game_manager: GameManager):
        """回放录像：读取 JSONL 文件，逐步重放动作

        用途：验证录像正确性，或让 AI 观看人类操作过程
        """
        records = self.load_recording(filepath)
        for record in records:
            action = GameAction[record["action"]]
            data = record.get("action_data", {})
            game_manager.execute_action(action, data if data else None)
            time.sleep(0.2)  # 回放间隔
```

### 阶段 4：主程序集成（优先级：高）

#### 步骤 4.1：主入口 (`__main__.py`)

```python
def main():
    game_manager = GameManager(render_mode="terminal")
    input_handler = InputHandler(keymap_scheme="wasd")
    level_manager = LevelManager()
    stats_manager = StatsManager()
    recording_manager = RecordingManager()
    menu = TerminalMenu(game_manager, level_manager, stats_manager)

    while True:
        # 1. 显示菜单，选择游戏
        game_id = menu.show_main_menu()
        if game_id is None:
            break

        # 2. 启动游戏
        if not game_manager.start_game(game_id):
            print("启动失败")
            continue

        # 3. 启动输入监听
        input_handler.start()
        session_id = recording_manager.start_session(game_id)

        # 4. 游戏主循环
        try:
            while True:
                # 获取待处理动作
                actions = input_handler.get_pending_actions()
                for action, data in actions:
                    # 过滤不可用动作
                    if action not in game_manager.env.action_space:
                        continue

                    # 特殊键处理
                    if action == GameAction.RESET and data.get("quit"):
                        raise GameExitException()

                    # 执行动作
                    obs = game_manager.execute_action(action, data)

                    # 记录
                    recording_manager.record_step(
                        action, data, obs,
                        game_manager.step_count,
                        game_manager.get_elapsed_ms()
                    )

                    # 追加 HUD
                    _print_hud(game_manager, obs)

                    # 检查状态
                    if obs and obs.state == GameState.WIN:
                        _handle_level_win(game_manager, level_manager,
                                          stats_manager, recording_manager)
                    elif obs and obs.state == GameState.GAME_OVER:
                        _handle_game_over(game_manager)

        except GameExitException:
            pass
        finally:
            input_handler.stop()
            recording_manager.end_session(...)
            game_manager.close_game()

    # 保存所有数据
    level_manager.save()
    stats_manager.save()
```

### 阶段 5：Matplotlib 模式支持（优先级：低，可选增强）

当用户选择 `render_mode="human"` 时：

* Matplotlib 弹窗显示网格图形

* 鼠标点击可直接映射到网格坐标（精确）

* 需要处理 Matplotlib 事件循环与 pynput 的协调

```python
# Matplotlib 模式下的鼠标坐标转换
def _matplotlib_click_to_grid(self, event):
    """Matplotlib 鼠标事件 → 网格坐标

    Matplotlib 的 event.xdata, event.ydata 直接对应图像坐标，
    可以精确映射到网格位置。
    """
    if event.inaxes:
        gx = int(event.xdata)
        gy = int(event.ydata)
        return gx, gy
    return None, None
```

***

## 五、开发顺序与里程碑（修订）

| 里程碑        | 内容                | 预计文件                                                          |
| ---------- | ----------------- | ------------------------------------------------------------- |
| **M1**     | 项目结构 + 配置 + 输入映射  | `__init__.py`, `__main__.py`, `config.py`, `input_handler.py` |
| **M2**     | 游戏管理 + 终端 HUD     | `game_manager.py`                                             |
| **M3**     | 终端菜单 + 关卡进度       | `menu.py`, `level_manager.py`                                 |
| **M4**     | 成绩统计 + 数据持久化      | `stats_manager.py`                                            |
| **M5**     | 录像系统              | `recording.py`                                                |
| **M6**     | 集成测试 + 优化         | 全部文件                                                          |
| **M7**（可选） | Matplotlib 模式鼠标支持 | `input_handler.py` 扩展                                         |

***

## 六、关键设计决策（修订）

### 6.1 ACTION6 坐标输入方案

终端模式下鼠标坐标转换精度有限，采用多策略方案：

| 策略                  | 适用场景                  | 精度          |
| ------------------- | --------------------- | ----------- |
| 键盘输入 `C` → 输入 `x,y` | 终端模式                  | 精确          |
| 鼠标点击（pynput）        | 终端模式                  | 近似（受终端字体影响） |
| 鼠标点击（Matplotlib）    | `render_mode="human"` | 精确          |
| 鼠标点击（Pygame）        | 自定义渲染器                | 精确          |

### 6.2 渲染策略

**推荐**：`render_mode="terminal"` + 主循环追加 HUD print

```python
env = arc.make("ls20", render_mode="terminal")
# 每次 env.step() 后，终端自动渲染网格
# 主循环中追加 print HUD 信息
```

**不推荐**：自定义 `renderer` 替代内置渲染（丢失内置渲染的彩色输出能力）

### 6.3 pynput 与终端渲染的协调

* pynput 在后台线程监听键盘/鼠标

* 主线程运行游戏循环：`get_pending_actions()` → `env.step()` → 自动渲染

* 两个线程通过 `deque + Lock` 通信

* 终端渲染由 ARC-AGI-3 内部处理，与 pynput 无冲突

### 6.4 退出机制

* 按 `ESC` 或 `Q` 键退出当前游戏，返回菜单

* 在菜单中按 `Q` 退出程序

* 退出前自动保存进度和录像

***

## 七、依赖管理（修订）

### 7.1 需要添加的依赖

```toml
# pixi.toml [pypi-dependencies] 新增
pynput = ">=1.7.6"
```

**注意**：不再需要 `pygame` 依赖。

### 7.2 新增 pixi task

```toml
# pixi.toml [tasks] 新增
human-play = "python -m human_player"
```

***

## 八、风险与缓解（修订）

| 风险                       | 影响                     | 缓解措施                    |
| ------------------------ | ---------------------- | ----------------------- |
| pynput 在 Windows 上需焦点    | 切换窗口后可能丢失按键            | 提示用户保持终端窗口焦点            |
| 终端鼠标坐标转换不精确              | ACTION6 坐标偏差           | 提供键盘输入坐标备选方案            |
| 终端渲染需要足够宽的窗口             | 网格显示换行变形               | 启动时检测终端宽度并提示            |
| pynput 与 Python 3.14 兼容性 | 可能无法安装                 | 先测试，必要时用 `keyboard` 库替代 |
| 终端颜色支持差异                 | 不同终端彩色输出不一致            | 使用 ANSI 标准转义码           |
| WIN 后关卡推进时序              | levels\_completed 变化时机 | 仔细处理 obs 返回值            |

***

## 九、与原方案的对比

| 维度   | 原方案（Pygame）   | 修订方案（终端优先）                |
| ---- | ------------- | ------------------------- |
| 新增依赖 | pygame        | pynput                    |
| 代码量  | \~1500 行      | \~600 行                   |
| 渲染代码 | 全部自建（\~400 行） | 复用内置（0 行）                 |
| 开发周期 | 长             | 短                         |
| 鼠标精度 | 高（窗口内坐标）      | 中（终端近似 / Matplotlib 精确）   |
| 视觉效果 | 图形化           | 终端文本                      |
| 扩展性  | 高             | 中（可升级到 Matplotlib/Pygame） |
| 上手难度 | 需理解 Pygame    | 终端原生体验                    |

**核心优势**：修订方案复用了 ARC-AGI-3 已有的渲染能力，将开发精力集中在输入映射、关卡管理和数据记录这些真正缺失的功能上，避免重复造轮子。
