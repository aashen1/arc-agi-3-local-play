# 游戏控制映射与关卡管理系统开发计划

## 一、项目背景与约束分析

### 1.1 ARC-AGI-3 动作体系

ARC-AGI-3 定义了 7 种标准化动作，所有游戏共用此接口：

| 动作 | 类型 | 语义 | 复杂度 |
|------|------|------|--------|
| `RESET` | 控制 | 初始化/重启游戏或关卡 | 简单 |
| `ACTION1` | 移动 | 上（Up） | 简单 |
| `ACTION2` | 移动 | 下（Down） | 简单 |
| `ACTION3` | 移动 | 左（Left） | 简单 |
| `ACTION4` | 移动 | 右（Right） | 简单 |
| `ACTION5` | 交互 | 交互/选择/旋转/执行 | 简单 |
| `ACTION6` | 点击 | 点击指定坐标（需 x,y 0-63） | **复杂** |
| `ACTION7` | 撤销 | 撤销上一步操作 | 简单 |

### 1.2 官方键位映射（网页 UI 已有方案）

**方案 A — WASD + Space：**

| 动作 | 按键 |
|------|------|
| ACTION1（上） | W |
| ACTION2（下） | S |
| ACTION3（左） | A |
| ACTION4（右） | D |
| ACTION5（交互） | Space |
| ACTION6（点击） | 鼠标左键 |
| ACTION7（撤销） | Ctrl+Z |
| RESET | R |

**方案 B — 方向键 + F：**

| 动作 | 按键 |
|------|------|
| ACTION1（上） | ↑ |
| ACTION2（下） | ↓ |
| ACTION3（左） | ← |
| ACTION4（右） | → |
| ACTION5（交互） | F |
| ACTION6（点击） | 鼠标左键 |
| ACTION7（撤销） | Ctrl+Z |
| RESET | R |

### 1.3 关键 API 接口

```python
arc = arc_agi.Arcade()                    # 主入口
env = arc.make("ls20", render_mode=...)    # 创建环境
env.action_space                           # 获取可用动作列表
env.step(action, data={}, reasoning={})    # 执行动作
env.reset()                                # 重置环境
env.observation_space                      # 帧数据（含 state, frame, score, levels_completed）
arc.get_environments()                     # 获取可用游戏列表
arc.get_scorecard()                        # 获取记分卡
```

### 1.4 游戏状态流转

```
NOT_FINISHED → (动作循环) → WIN → (自动下一关或 RESET) → GAME_OVER → (仅 RESET)
```

### 1.5 现有项目文件

- `play.py` — 最简游戏脚本（仅 15 行）
- `pixi.toml` — Python 环境（Python >=3.14, arc-agi >=0.9.8）
- `docs/` — 7 个中文文档
- 无其他代码文件

---

## 二、技术选型

### 2.1 GUI 框架：Pygame

**选择理由：**
- 原生支持键盘/鼠标事件捕获，无需额外钩子
- 支持 2D 网格渲染，完美匹配 ARC-AGI-3 的 64x64 网格
- 游戏循环模式与 ARC-AGI-3 的回合制交互天然契合
- 跨平台，Windows 10 兼容性好
- 轻量级，无需浏览器或 Web 服务

**备选方案及排除理由：**
- tkinter：网格渲染能力弱，游戏体验差
- Web（Flask+JS）：架构复杂，键盘钩子需额外处理
- PyGObject/GTK：Windows 依赖复杂

### 2.2 数据存储：JSON 文件

**选择理由：**
- 人类玩家数据量小，无需数据库
- JSON 可读性好，方便手动检查和调试
- 与 ARC-AGI-3 官方录制格式（JSONL）一致
- Python 标准库原生支持

**存储结构：**
```
data/
├── progress.json          # 全局进度（游戏-关卡完成状态）
├── records/               # 成绩记录
│   ├── ls20.json          # 每个游戏一个文件
│   └── ft09.json
└── recordings/            # 人类玩家录像
    ├── ls20_20260503_143022.jsonl
    └── ft09_20260503_150000.jsonl
```

### 2.3 录像格式：JSONL（与官方一致）

每行一条记录，兼容官方 recording 格式并扩展人类专属字段：

```json
{
  "timestamp": "2026-05-03T14:30:22.123456+08:00",
  "step": 5,
  "action": "ACTION1",
  "action_data": {},
  "reasoning": null,
  "frame_state": "NOT_FINISHED",
  "levels_completed": 0,
  "score": 0,
  "elapsed_ms": 1234,
  "player_type": "human",
  "session_id": "ls20_20260503_143022"
}
```

---

## 三、系统架构设计

### 3.1 模块划分

```
human_player/
├── __init__.py
├── main.py                # 程序入口，Pygame 主循环
├── config.py              # 配置常量（颜色、尺寸、键位映射）
├── input_handler.py       # 输入映射模块（键盘/鼠标 → GameAction）
├── renderer.py            # 网格渲染模块（FrameData → Pygame 画面）
├── game_manager.py        # 游戏管理模块（Arcade 交互封装）
├── level_manager.py       # 关卡管理模块（列表、选择、进度）
├── stats_manager.py       # 成绩统计模块（记录、查询、展示）
├── recording.py           # 录像模块（动作记录、JSONL 写入）
└── ui/
    ├── __init__.py
    ├── base.py            # UI 基类
    ├── game_screen.py     # 游戏主界面
    ├── level_select.py    # 关卡选择界面
    ├── stats_screen.py    # 成绩统计界面
    └── settings_screen.py # 设置界面（键位自定义）
```

### 3.2 核心类图

```
┌─────────────┐     ┌────────────────┐     ┌──────────────┐
│   main.py   │────▶│  GameManager   │────▶│  Arcade(env) │
│  (Pygame)   │     │                │     └──────────────┘
└──────┬──────┘     │ - arc: Arcade  │
       │            │ - env: EnvWrap │     ┌──────────────┐
       │            │ - game_id      │────▶│LevelManager  │
       │            └────────────────┘     │ - levels[]   │
       │                                    │ - progress   │
       │            ┌────────────────┐     └──────────────┘
       ├───────────▶│ InputHandler   │
       │            │ - key_map      │     ┌──────────────┐
       │            │ - mouse_pos    │────▶│StatsManager  │
       │            └────────────────┘     │ - records    │
       │                                    │ - storage    │
       │            ┌────────────────┐     └──────────────┘
       ├───────────▶│  Renderer      │
       │            │ - draw_grid()  │     ┌──────────────┐
       │            │ - draw_ui()    │────▶│  Recording   │
       │            └────────────────┘     │ - jsonl      │
       │                                    │ - session    │
       │            ┌────────────────┐     └──────────────┘
       └───────────▶│  UI Screens    │
                    │ - GameScreen   │
                    │ - LevelSelect  │
                    │ - StatsScreen  │
                    │ - Settings     │
                    └────────────────┘
```

### 3.3 状态机（界面切换）

```
                    ┌──────────────┐
                    │  启动画面     │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
              ┌────▶│  关卡选择     │◀────┐
              │     └──────┬───────┘     │
              │            │ 选择游戏     │ ESC
              │     ┌──────▼───────┐     │
              │     │  游戏主界面   │─────┘
              │     └──────┬───────┘
              │            │ Tab
              │     ┌──────▼───────┐
              │     │  成绩统计     │─────┐
              │     └──────────────┘     │
              │                          │ ESC
              │     ┌──────────────┐     │
              └─────│  设置界面     │◀────┘
                    └──────────────┘
```

---

## 四、详细实现步骤

### 阶段 1：基础框架搭建（优先级：最高）

#### 步骤 1.1：项目结构初始化

- 创建 `human_player/` 包目录及所有子模块文件
- 创建 `data/` 数据存储目录
- 更新 `pixi.toml` 添加 `pygame` 依赖
- 创建 `pixi` task：`human-play`

#### 步骤 1.2：配置模块 (`config.py`)

定义所有常量和默认配置：

```python
# 窗口配置
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS = 30

# 网格渲染配置
CELL_SIZE = 10          # 每个网格单元的像素大小
GRID_OFFSET_X = 50      # 网格左上角 X 偏移
GRID_OFFSET_Y = 50      # 网格左上角 Y 偏移

# ARC-AGI-3 16色调色板（索引 0-15）
ARC_PALETTE = [
    (0, 0, 0),          # 0 - 黑色
    (0, 116, 217),      # 1 - 蓝色
    (255, 65, 54),      # 2 - 红色
    (46, 204, 64),      # 3 - 绿色
    (255, 220, 0),      # 4 - 黄色
    (170, 102, 204),    # 5 - 紫色
    (255, 133, 27),     # 6 - 橙色
    (0, 191, 191),      # 7 - 青色
    (255, 255, 255),    # 8 - 白色
    (128, 128, 128),    # 9 - 灰色
    (255, 192, 203),    # 10 - 粉色
    (139, 69, 19),      # 11 - 棕色
    (0, 0, 139),        # 12 - 深蓝
    (220, 20, 60),      # 13 - 深红
    (0, 100, 0),        # 14 - 深绿
    (255, 215, 0),      # 15 - 金色
]

# 默认键位映射（方案 A：WASD + Space）
DEFAULT_KEYMAP_A = {
    pygame.K_w: GameAction.ACTION1,
    pygame.K_s: GameAction.ACTION2,
    pygame.K_a: GameAction.ACTION3,
    pygame.K_d: GameAction.ACTION4,
    pygame.K_SPACE: GameAction.ACTION5,
    pygame.K_z: GameAction.ACTION7,
    pygame.K_r: GameAction.RESET,
}

# 默认键位映射（方案 B：方向键 + F）
DEFAULT_KEYMAP_B = {
    pygame.K_UP: GameAction.ACTION1,
    pygame.K_DOWN: GameAction.ACTION2,
    pygame.K_LEFT: GameAction.ACTION3,
    pygame.K_RIGHT: GameAction.ACTION4,
    pygame.K_f: GameAction.ACTION5,
    pygame.K_z: GameAction.ACTION7,
    pygame.K_r: GameAction.RESET,
}
```

#### 步骤 1.3：输入映射模块 (`input_handler.py`)

核心职责：
- 监听 Pygame 键盘事件，映射为 `GameAction`
- 监听鼠标点击事件，映射为 `GameAction.ACTION6`（附带 x,y 坐标）
- 支持键位方案切换（A/B）
- 支持自定义键位配置
- 过滤不可用动作（对照 `env.action_space`）

关键接口：

```python
class InputHandler:
    def __init__(self, keymap_scheme="A"):
        self.keymap = DEFAULT_KEYMAP_A if keymap_scheme == "A" else DEFAULT_KEYMAP_B
        self.mouse_grid_converter = None  # 像素坐标→网格坐标转换器

    def handle_event(self, event, available_actions) -> tuple[GameAction | None, dict | None]:
        """处理单个 Pygame 事件，返回 (action, data) 或 (None, None)"""

    def set_grid_params(self, grid_size, cell_size, offset_x, offset_y):
        """设置网格参数，用于鼠标坐标转换"""

    def pixel_to_grid(self, pixel_x, pixel_y) -> tuple[int, int]:
        """将鼠标像素坐标转换为网格坐标"""

    def switch_keymap(self, scheme: str):
        """切换键位方案"""

    def remap_key(self, old_key, new_key):
        """自定义键位映射"""
```

**鼠标坐标转换逻辑：**

```
grid_x = (pixel_x - offset_x) // cell_size
grid_y = (pixel_y - offset_y) // cell_size
# 校验范围：0 <= grid_x < grid_width, 0 <= grid_y < grid_height
```

### 阶段 2：游戏渲染与管理（优先级：高）

#### 步骤 2.1：网格渲染模块 (`renderer.py`)

核心职责：
- 将 `FrameDataRaw.frame`（2D 数组）渲染为 Pygame 画面
- 绘制 HUD 信息（当前关卡、步数、时间、可用动作）
- 绘制游戏状态提示（WIN / GAME_OVER）
- 支持鼠标悬停高亮网格单元

关键接口：

```python
class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen

    def draw_frame(self, frame_data: FrameDataRaw, step_count: int, elapsed_ms: int):
        """绘制完整游戏画面（网格 + HUD）"""

    def draw_grid(self, grid: list[list[int]], grid_size: tuple[int, int]):
        """绘制网格"""

    def draw_hud(self, state, step_count, elapsed_ms, levels_completed, available_actions):
        """绘制 HUD 信息栏"""

    def draw_status_overlay(self, state: GameState):
        """绘制 WIN/GAME_OVER 状态覆盖层"""

    def draw_mouse_highlight(self, grid_x: int, grid_y: int):
        """绘制鼠标悬停高亮"""
```

#### 步骤 2.2：游戏管理模块 (`game_manager.py`)

核心职责：
- 封装 `arc_agi.Arcade` 和 `EnvironmentWrapper` 的交互
- 管理游戏会话生命周期（创建、重置、关闭）
- 维护游戏状态（步数、时间、当前关卡）
- 协调输入→动作→渲染的完整流程

关键接口：

```python
class GameManager:
    def __init__(self):
        self.arc = arc_agi.Arcade()
        self.env = None
        self.game_id = None
        self.step_count = 0
        self.start_time = None
        self.levels_completed = 0

    def start_game(self, game_id: str) -> bool:
        """启动指定游戏"""

    def execute_action(self, action: GameAction, data: dict = None) -> FrameDataRaw | None:
        """执行动作并更新状态"""

    def reset_level(self) -> FrameDataRaw | None:
        """重置当前关卡"""

    def get_available_games(self) -> list[EnvironmentInfo]:
        """获取可用游戏列表"""

    def get_current_state(self) -> dict:
        """获取当前游戏状态摘要"""
```

### 阶段 3：关卡与进度管理（优先级：高）

#### 步骤 3.1：关卡管理模块 (`level_manager.py`)

核心职责：
- 获取并展示游戏列表
- 追踪每个游戏的关卡完成状态
- 提供关卡选择界面数据

关键接口：

```python
class LevelManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.progress = self._load_progress()

    def get_game_list(self) -> list[dict]:
        """获取游戏列表（含完成状态）"""

    def get_level_status(self, game_id: str) -> list[dict]:
        """获取指定游戏的关卡状态列表"""

    def mark_level_completed(self, game_id: str, level_index: int, steps: int, time_ms: int):
        """标记关卡完成"""

    def get_progress_summary(self) -> dict:
        """获取全局进度摘要"""

    def _load_progress(self) -> dict:
        """从 JSON 文件加载进度"""

    def _save_progress(self):
        """保存进度到 JSON 文件"""
```

**进度数据结构 (`progress.json`)：**

```json
{
  "version": "1.0",
  "last_updated": "2026-05-03T14:30:00+08:00",
  "games": {
    "ls20": {
      "title": "Agent Reasoning",
      "levels": {
        "0": {
          "completed": true,
          "best_steps": 15,
          "best_time_ms": 12345,
          "completed_at": "2026-05-03T14:30:00+08:00"
        },
        "1": {
          "completed": false
        }
      }
    }
  }
}
```

### 阶段 4：成绩统计系统（优先级：中）

#### 步骤 4.1：成绩统计模块 (`stats_manager.py`)

核心职责：
- 记录每次游戏的详细成绩
- 查询历史最佳成绩
- 计算与官方 RHAE 基线的对比
- 提供统计数据展示

关键接口：

```python
class StatsManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir

    def record_attempt(self, game_id: str, level_index: int, steps: int,
                       time_ms: int, result: str, session_id: str):
        """记录一次游戏尝试"""

    def get_best_record(self, game_id: str, level_index: int) -> dict | None:
        """获取最佳记录"""

    def get_all_records(self, game_id: str) -> list[dict]:
        """获取指定游戏的所有记录"""

    def get_comparison_with_baseline(self, game_id: str, level_index: int,
                                      human_baseline: int) -> dict:
        """与官方人类基线对比"""

    def get_summary_stats(self) -> dict:
        """获取全局统计摘要"""
```

**成绩记录格式 (`data/records/ls20.json`)：**

```json
{
  "game_id": "ls20",
  "title": "Agent Reasoning",
  "records": [
    {
      "level_index": 0,
      "session_id": "ls20_20260503_143022",
      "timestamp": "2026-05-03T14:30:22+08:00",
      "steps": 15,
      "time_ms": 12345,
      "result": "WIN",
      "actions_log": ["RESET", "ACTION1", "ACTION3", ...]
    }
  ]
}
```

### 阶段 5：录像系统（优先级：中）

#### 步骤 5.1：录像模块 (`recording.py`)

核心职责：
- 记录人类玩家的每一步操作
- 生成 JSONL 格式录像文件
- 包含完整上下文信息（帧状态、时间戳、推理）
- 支持录像回放（读取并重放动作序列）

关键接口：

```python
class RecordingManager:
    def __init__(self, recordings_dir: str = "data/recordings"):
        self.recordings_dir = recordings_dir
        self.current_session = None
        self.session_start_time = None

    def start_session(self, game_id: str) -> str:
        """开始新的录像会话，返回 session_id"""

    def record_step(self, action: GameAction, data: dict, frame_data: FrameDataRaw,
                    step_count: int, elapsed_ms: int):
        """记录一步操作"""

    def end_session(self, result: str, total_steps: int, total_time_ms: int):
        """结束录像会话"""

    def list_recordings(self, game_id: str = None) -> list[dict]:
        """列出录像文件"""

    def load_recording(self, filepath: str) -> list[dict]:
        """加载录像数据"""
```

**录像文件格式（JSONL，每行一条记录）：**

```json
{"timestamp":"2026-05-03T14:30:22.123+08:00","step":0,"action":"RESET","action_data":{},"frame_state":"NOT_FINISHED","levels_completed":0,"score":0,"elapsed_ms":0,"player_type":"human","session_id":"ls20_20260503_143022"}
{"timestamp":"2026-05-03T14:30:23.456+08:00","step":1,"action":"ACTION1","action_data":{},"frame_state":"NOT_FINISHED","levels_completed":0,"score":0,"elapsed_ms":1333,"player_type":"human","session_id":"ls20_20260503_143022"}
```

### 阶段 6：UI 界面实现（优先级：中）

#### 步骤 6.1：游戏主界面 (`ui/game_screen.py`)

- 全屏网格渲染区域
- 右侧/底部 HUD 面板：
  - 当前游戏名、关卡编号
  - 步数计数器
  - 计时器
  - 可用动作列表（高亮当前可用）
  - 当前键位方案提示
- 状态覆盖层（WIN 绿色、GAME_OVER 红色）
- ESC 返回关卡选择

#### 步骤 6.2：关卡选择界面 (`ui/level_select.py`)

- 游戏列表（卡片式布局）
- 每个游戏卡片显示：
  - 游戏 ID 和标题
  - 标签
  - 完成进度条
  - 最佳成绩摘要
- 点击进入游戏

#### 步骤 6.3：成绩统计界面 (`ui/stats_screen.py`)

- 按游戏分组的成绩表格
- 每关最佳步数、最佳时间
- 与人类基线对比（RHAE 估算）
- 历史趋势图（简单文本/条形图）

#### 步骤 6.4：设置界面 (`ui/settings_screen.py`)

- 键位方案选择（A/B/自定义）
- 自定义键位绑定
- 渲染选项（网格大小、颜色主题）

### 阶段 7：主程序集成（优先级：高）

#### 步骤 7.1：主循环 (`main.py`)

```python
def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    game_manager = GameManager()
    input_handler = InputHandler(keymap_scheme="A")
    renderer = Renderer(screen)
    level_manager = LevelManager()
    stats_manager = StatsManager()
    recording_manager = RecordingManager()

    current_screen = "level_select"  # 状态机

    while True:
        # 1. 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # 保存数据并退出
                ...

            # 2. 根据当前界面分发事件
            if current_screen == "game":
                action, data = input_handler.handle_event(event, game_manager.env.action_space)
                if action:
                    obs = game_manager.execute_action(action, data)
                    recording_manager.record_step(action, data, obs, ...)
                    if obs.state == GameState.WIN:
                        stats_manager.record_attempt(...)
                        level_manager.mark_level_completed(...)
            elif current_screen == "level_select":
                ...

        # 3. 渲染
        if current_screen == "game":
            renderer.draw_frame(game_manager.env.observation_space, ...)
        elif current_screen == "level_select":
            renderer.draw_level_select(level_manager.get_game_list(), ...)

        pygame.display.flip()
        clock.tick(FPS)
```

---

## 五、开发顺序与里程碑

| 里程碑 | 内容 | 预计文件 |
|--------|------|----------|
| **M1** | 基础框架 + 键盘控制 + 终端验证 | `config.py`, `input_handler.py`, `game_manager.py`, `main.py` |
| **M2** | Pygame 网格渲染 + 游戏主界面 | `renderer.py`, `ui/game_screen.py` |
| **M3** | 关卡选择 + 进度记录 | `level_manager.py`, `ui/level_select.py` |
| **M4** | 成绩统计 + 数据持久化 | `stats_manager.py`, `ui/stats_screen.py` |
| **M5** | 录像系统 | `recording.py` |
| **M6** | 设置界面 + 键位自定义 | `ui/settings_screen.py` |
| **M7** | 集成测试 + 优化 | 全部文件 |

---

## 六、关键设计决策

### 6.1 鼠标点击 → ACTION6 坐标转换

ARC-AGI-3 的 ACTION6 需要 (x, y) 坐标（0-63 范围），对应网格坐标。转换流程：

1. 获取鼠标在 Pygame 窗口中的像素坐标 (px, py)
2. 减去网格渲染偏移量：(gx, gy) = (px - offset_x, py - offset_y)
3. 除以单元格大小：(cx, cy) = (gx // cell_size, gy // cell_size)
4. 校验范围：0 <= cx < grid_width, 0 <= cy < grid_height
5. 发送 `env.step(GameAction.ACTION6, data={"x": cx, "y": cy})`

### 6.2 动作过滤机制

不是所有游戏都支持所有动作。每次按键后需检查：

```python
available = env.action_space  # list[GameAction]
if action in available:
    obs = env.step(action, data=data)
else:
    # 忽略或提示"动作不可用"
```

### 6.3 关卡完成检测

```python
if obs.state == GameState.WIN:
    levels_before = game_manager.levels_completed
    # 执行 RESET 进入下一关
    obs = env.reset()
    levels_after = obs.levels_completed if obs else levels_before
    if levels_after > levels_before:
        # 新关卡已加载
        ...
```

### 6.4 录像与官方格式的兼容性

- 使用 JSONL 格式，与官方 `recording.jsonl` 兼容
- 扩展字段（`player_type`, `session_id`, `elapsed_ms`）不影响官方解析
- 录像文件可被 AI 训练流程直接使用

### 6.5 数据安全

- 所有数据存储在本地 `data/` 目录
- 不上传任何数据到远程服务器
- 进度文件自动备份（写入前先复制为 `.bak`）

---

## 七、依赖管理

### 7.1 需要添加的依赖

```toml
# pixi.toml [pypi-dependencies] 新增
pygame = ">=2.5.0"
```

### 7.2 新增 pixi task

```toml
# pixi.toml [tasks] 新增
human-play = "python -m human_player"
```

---

## 八、测试策略

### 8.1 单元测试

- `test_input_handler.py` — 键位映射正确性、鼠标坐标转换
- `test_level_manager.py` — 进度读写、关卡状态标记
- `test_stats_manager.py` — 成绩记录、查询、对比
- `test_recording.py` — JSONL 写入、读取、格式校验

### 8.2 集成测试

- 完整游戏流程：启动 → 选择游戏 → 游玩 → 完成 → 记录
- 键位切换：方案 A ↔ 方案 B
- 数据持久化：退出后重新启动，进度保留

### 8.3 手动测试

- 实际游玩 ls20、ft09、vc33 三个公开游戏
- 验证所有键位映射响应正确
- 验证鼠标点击坐标准确
- 验证录像文件可被 AI 读取

---

## 九、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Pygame 与 arc-agi 的渲染模式冲突 | 可能无法同时使用 render_mode | 使用自定义 renderer 或关闭内置渲染 |
| 网格尺寸动态变化 | 不同关卡网格大小不同 | 渲染器自适应调整 cell_size |
| ACTION6 坐标系差异 | 鼠标坐标与网格坐标不匹配 | 严格按 offset+cell_size 转换 |
| pixi 添加 pygame 兼容性 | Python 3.14 + pygame 可能有问题 | 先测试兼容性，必要时降级 Python |
| 游戏状态判断时序 | WIN 后何时自动进入下一关 | 仔细处理 obs.levels_completed 变化 |
