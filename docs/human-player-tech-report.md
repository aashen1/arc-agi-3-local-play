# ARC-AGI-3 人类玩家控制台 — 技术报告

## 1. 项目概述

为 ARC-AGI-3 基准测试平台开发了一套终端交互式人类游玩系统，实现键盘控制映射、关卡管理、成绩统计和操作录像功能。系统复用 ARC-AGI-3 内置终端渲染，仅补充输入层和跨关卡管理层。

## 2. 技术选型与决策

### 2.1 渲染：复用内置，不造轮子

ARC-AGI-3 提供 `render_mode="terminal"` 终端渲染，能将 64x64 网格以彩色字符输出到终端，效果已经很好。我们直接复用，不在渲染上花任何代码。

内置渲染在每次 `env.step()` 或 `env.reset()` 时自动触发，输出网格画面和 `Step: N - State: XXX` 信息行。我们的 HUD 信息只在状态变化（WIN/GAME_OVER）时用 rich 面板输出，避免和内置渲染冲突。

### 2.2 输入：msvcrt 而非 pynput

**最终选择**：Windows 内置 `msvcrt` 模块

**选择理由**：
- 零依赖，Python 标准库自带
- `msvcrt.getwch()` 提供无回显单键读取，正好适合游戏操作
- `msvcrt.kbhit()` 提供非阻塞按键检测，可做轮询式游戏循环
- Windows 10 原生支持，无需管理员权限

**关键代码**：

```python
def _read_key() -> str | None:
    if msvcrt.kbhit():          # 非阻塞检测：有没有按键？
        ch = msvcrt.getwch()    # 读取一个字符（无回显）
        return ch
    return None
```

**方向键的特殊处理**：Windows 终端中方向键产生两字节序列，首字节 `\x00` 或 `\xe0`，次字节为方向码（H=上, P=下, K=左, M=右）。因此键位映射中方向键的 key 是 `'\x00H'`、`'\x00P'` 等：

```python
KEYMAP_ARROWS = {
    '\x00H': GameAction.ACTION1,   # ↑
    '\x00P': GameAction.ACTION2,   # ↓
    '\x00K': GameAction.ACTION3,   # ←
    '\x00M': GameAction.ACTION4,   # →
    'f': GameAction.ACTION5,
    'z': GameAction.ACTION7,
    'r': GameAction.RESET,
}
```

读取时需要先检测首字节，再读次字节：

```python
if key == '\x00' or key == '\xe0':
    ext = msvcrt.getwch()           # 读第二字节
    ext_key = '\x00' + ext          # 组合成双字节 key
    if ext_key in keymap:
        action = keymap[ext_key]
```

**CPU 空转问题**：`_read_key()` 无按键时立即返回 None，主循环会高速空转。解决方案是在无按键时 `time.sleep(0.02)`（50Hz 轮询频率），既不浪费 CPU，又保持足够响应速度。

### 2.3 菜单 UI：rich 库

**选择理由**：
- `rich.table.Table` — 游戏列表、成绩表格
- `rich.panel.Panel` — 状态面板（关卡完成、游戏结束）
- `rich.prompt.Prompt` — 带验证的菜单选择输入
- `rich.text.Text` — 带样式的文本组合
- 开箱即用的进度条字符（█░）

**菜单输入 vs 游戏输入的区分**：
- 菜单阶段用 `rich.prompt.Prompt.ask()` — 阻塞式，等待用户输入后回车
- 游戏阶段用 `msvcrt.getwch()` — 非阻塞，单键即触发，无需回车

这两种输入模式在同一个程序中共存，通过状态机切换：菜单 → 游戏 → 菜单。

## 3. 模块架构

```
human_player/
├── __init__.py            # 空文件，包标记
├── __main__.py            # 入口 + 游戏主循环
├── config.py              # 常量：键位映射、路径、标签
├── game_manager.py        # Arcade/EnvironmentWrapper 封装
├── level_manager.py       # 关卡进度读写（JSON）
├── stats_manager.py       # 成绩记录读写（JSON）
├── recording.py           # 操作录像读写（JSONL）
└── menu.py                # rich 终端 UI 渲染
```

### 3.1 __main__.py — 主循环

核心流程：

```
main() → while True:
    1. show_banner() + show_game_list() → 用户选择游戏
    2. game_manager.start_game(game_id) → 创建环境
    3. recording_manager.start_session() → 开始录像
    4. _game_loop() → 游戏内循环
       ├─ 检查 obs.state → WIN/GAME_OVER/NOT_FINISHED
       ├─ _read_key() → msvcrt 键盘读取
       ├─ keymap[key] → GameAction 映射
       ├─ game_manager.execute_action() → env.step()
       ├─ recording_manager.record_step() → JSONL 写入
       └─ did_level_up() → 关卡完成检测
    5. 退出时 recording_manager.end_session() + game_manager.close_game()
```

**关卡完成检测机制**：

ARC-AGI-3 的 `FrameDataRaw.levels_completed` 在 WIN 时递增。`GameManager.did_level_up()` 通过比较当前值和前一次值来检测：

```python
def did_level_up(self) -> bool:
    if self.levels_completed > self._prev_levels_completed:
        self._prev_levels_completed = self.levels_completed
        return True
    return False
```

**WIN 状态后的自动推进**：当 `obs.state == GameState.WIN` 时，系统自动调用 `env.reset()` 进入下一关，同时重置步数计数器和计时器。

### 3.2 game_manager.py — 游戏交互封装

封装了 `arc_agi.Arcade` 和 `EnvironmentWrapper` 的交互，提供：

| 方法 | 功能 |
|------|------|
| `list_games()` | 调用 `arc.get_environments()` |
| `start_game(game_id)` | 调用 `arc.make()` + `env.reset()` |
| `execute_action(action, data)` | 调用 `env.step()`，维护步数和时间 |
| `reset_level()` | 调用 `env.reset()`，重置步数和计时 |
| `did_level_up()` | 检测 `levels_completed` 是否递增 |

**`_update_from_obs()` 方法**：从 `FrameDataRaw` 中提取 `levels_completed` 和 `win_levels`，更新内部状态。使用 `hasattr` 防御性检查，因为 `FrameDataRaw` 的属性可能因版本不同而变化（实测发现 `score` 属性不存在）。

### 3.3 config.py — 键位映射

两套键位映射字典，key 为 `msvcrt.getwch()` 返回的字符，value 为 `GameAction` 枚举：

```python
KEYMAP_WASD = {
    'w': GameAction.ACTION1,    # 上
    's': GameAction.ACTION2,    # 下
    'a': GameAction.ACTION3,    # 左
    'd': GameAction.ACTION4,    # 右
    ' ': GameAction.ACTION5,    # 交互（空格键返回空格字符）
    'z': GameAction.ACTION7,    # 撤销
    'r': GameAction.RESET,      # 重置
}
```

**ACTION6 的处理**：ACTION6（点击）需要 x,y 坐标，无法通过单键映射。采用按 `C` 键触发坐标输入模式，用 `input()` 读取 `x,y` 格式字符串。

### 3.4 level_manager.py — 关卡进度

JSON 文件存储，每次更新立即写盘（`_save_progress()` 在 `update_level_status()` 末尾调用）。

**数据结构**：

```json
{
  "version": "1.0",
  "games": {
    "ls20": {
      "levels": {
        "0": {
          "completed": true,
          "best_steps": 15,
          "best_time_ms": 12345,
          "completed_at": "2026-05-03T14:30:00+08:00",
          "attempts": 3
        }
      },
      "total_levels": 5
    }
  }
}
```

**关卡总数获取**：ARC-AGI-3 API 不直接暴露关卡总数。通过两种方式推断：
1. `FrameDataRaw.win_levels` — 达到 WIN 所需的关卡数
2. 游玩过程中 `levels_completed` 的最大值

`update_total_levels()` 在每次关卡完成时调用，持续更新已知最大关卡数。

### 3.5 stats_manager.py — 成绩统计

每个游戏一个 JSON 文件（`data/records/{game_id}.json`），记录所有尝试：

```json
[
  {
    "level_index": 0,
    "session_id": "ls20_20260503_143022",
    "timestamp": "2026-05-03T14:30:22+08:00",
    "steps": 15,
    "time_ms": 12345,
    "result": "WIN"
  }
]
```

带内存缓存（`self._cache`），避免重复读文件。

### 3.6 recording.py — 操作录像

JSONL 格式，每步一条记录，与 ARC-AGI-3 官方录制格式兼容并扩展：

```json
{
  "timestamp": "2026-05-03T14:30:22.123+08:00",
  "step": 5,
  "action": "ACTION1",
  "action_data": {},
  "frame_state": "NOT_FINISHED",
  "levels_completed": 0,
  "score": 0,
  "elapsed_ms": 1234,
  "player_type": "human",
  "session_id": "ls20_20260503_143022"
}
```

**与官方格式的差异**：
- 新增 `elapsed_ms` — 从关卡开始到这步的毫秒数
- 新增 `player_type` — 固定为 "human"，方便 AI 训练数据中区分来源
- 新增 `session_id` — 会话标识，用于关联同一次游戏的记录
- `action` 使用名称字符串（如 "ACTION1"）而非数字索引

**文件命名**：`{game_id}_{YYYYMMDD_HHMMSS}.jsonl`

**写入策略**：每步 `flush()`，确保异常退出时不丢数据。

### 3.7 menu.py — rich 终端 UI

提供以下渲染函数：

| 函数 | 用途 |
|------|------|
| `show_banner()` | 标题面板 |
| `show_game_list()` | 游戏列表表格 + 选择提示 |
| `show_stats()` | 成绩统计面板 + 关卡详情表格 |
| `show_settings()` | 设置表格 + 键位说明 |
| `show_level_complete()` | 关卡完成面板（绿色） |
| `show_game_over()` | 游戏结束面板（红色） |
| `show_all_complete()` | 全部通关面板 |
| `show_game_hud()` | 游戏 HUD 面板（当前未在主循环使用） |

**游戏 ID 截断显示**：ARC-AGI-3 的完整游戏 ID 格式为 `ls20-9607627b`（含版本哈希），菜单中只显示前缀 `ls20`，避免列宽溢出：

```python
short_id = gid.split("-")[0] if "-" in gid else gid
```

## 4. 已知限制与未来改进

### 4.1 当前限制

| 限制 | 原因 | 影响 |
|------|------|------|
| 仅支持 Windows | `msvcrt` 是 Windows 专属模块 | Linux/macOS 无法运行 |
| ACTION6 坐标只能手动输入 | 终端模式下鼠标坐标转换精度差 | 需要 click 操作的游戏体验不佳 |
| 内置渲染与 rich 输出混排 | 两者都往 stdout 写 | HUD 信息可能被网格画面冲掉 |
| 键位方案运行时切换需返回菜单 | 游戏内循环读取固定 keymap | 不方便中途切换 |
| 关卡总数无法预知 | API 不暴露此信息 | 进度条首次游玩时不显示总数 |

### 4.2 改进方向

1. **跨平台输入**：用 `pynput` 或 `keyboard` 库替代 `msvcrt`，支持 Linux/macOS
2. **Matplotlib 模式**：`render_mode="human"` 弹窗渲染，鼠标点击可直接映射到网格坐标
3. **自定义渲染器**：用 `renderer` 回调替代 `render_mode`，在回调中同时渲染网格和 HUD，避免输出混排
4. **录像回放**：读取 JSONL 文件，逐步重放动作序列
5. **游戏内键位切换**：添加快捷键动态切换 WASD/方向键方案
6. **RHAE 评分对比**：加载官方人类基线数据，计算 RHAE 分数

## 5. 依赖清单

| 依赖 | 版本 | 用途 |
|------|------|------|
| `arc-agi` | >=0.9.8, <0.10 | ARC-AGI-3 核心 SDK |
| `rich` | >=13.0 | 终端美化（表格、面板、提示） |
| `msvcrt` | 标准库 | Windows 键盘输入（无回显单键读取） |

## 6. 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `human_player/__init__.py` | 0 | 包标记 |
| `human_player/__main__.py` | 255 | 入口、主循环、键盘输入 |
| `human_player/config.py` | 52 | 键位映射、路径常量 |
| `human_player/game_manager.py` | 115 | Arcade/Environment 交互封装 |
| `human_player/level_manager.py` | 80 | 关卡进度 JSON 读写 |
| `human_player/stats_manager.py` | 68 | 成绩记录 JSON 读写 |
| `human_player/recording.py` | 90 | JSONL 录像读写 |
| `human_player/menu.py` | 290 | rich 终端 UI 渲染 |
| **合计** | **~950** | |

## 7. 踩坑记录

### 7.1 FrameDataRaw 没有 score 属性

文档中提到 `FrameDataRaw` 有 `score` 字段，但实测 `obs.score` 抛出 `AttributeError`。改用 `getattr(obs, 'score', 0) or 0` 防御性访问。

### 7.2 方向键的双字节序列

Windows 终端中方向键不是返回单个字符，而是两字节序列 `\x00H`（上）、`\x00P`（下）等。`msvcrt.getwch()` 第一次调用返回 `\x00` 或 `\xe0`，需要再调用一次读取方向码。

### 7.3 render_mode 与 renderer 的优先级

ARC-AGI-3 规定：如果同时提供 `render_mode` 和 `renderer`，`renderer` 优先。这意味着如果用自定义 renderer，内置的终端渲染就不会执行。当前方案只用 `render_mode="terminal"`，不提供自定义 renderer，让内置渲染正常工作。

### 7.4 rich Prompt.ask 的 choices 验证

`Prompt.ask(choices=[...])` 会循环直到用户输入合法值。当游戏列表有 25 个时，choices 列表很长，但 rich 能正确处理。输入不匹配时会提示重新输入。

### 7.5 WIN 后的关卡推进

ARC-AGI-3 在 `obs.state == GameState.WIN` 后，需要调用 `env.reset()` 进入下一关。`reset()` 返回的 `FrameDataRaw` 中 `levels_completed` 已经是递增后的值。系统自动处理这一流程，玩家无需手动操作。
