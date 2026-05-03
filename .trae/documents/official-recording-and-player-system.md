# 官方格式录像 + 玩家系统 实施计划（v2）

## 核心设计理念

### 录像的生命周期

**一次进入游戏到退出 = 一个录像文件**。这是最自然的记录周期。

玩家与一个游戏的关系是渐进的：

1. **首次接触**：玩家第一次进入游戏，可能打了几关就退出了 → 生成录像 A（未通关）
2. **继续探索**：几天后玩家再来，从上次进度继续，可能又打了几关 → 生成录像 B（未通关）
3. **首次通关**：终于打通所有关卡 → 生成录像 C（WIN）
4. **二次游玩**：已经通关了，再来玩，更熟练 → 生成录像 D（WIN，更快）

**录像 A + B + C 连起来**，才是完整的"从零到首次通关"的学习过程。这是最有分析价值的数据。
录像 D 及之后的数据，反映的是"熟练度"，性质不同。

### 设计原则

1. **每次进入游戏到退出 = 一个录像文件**，不删除任何录像
2. **以官方 JSONL 格式为基础**，兼容官方回放工具
3. **自动追踪"首次通关里程碑"**：通过索引文件标记哪些录像属于"首次通关前"vs"通关后"
4. **小关数据也保留**：现有轻量级录像继续工作
5. **玩家概念**：每个玩家独立数据目录

***

## 录像格式设计

### 官方格式录像文件

**文件命名**：`{game_id}.{guid}.recording.jsonl`

* 例：`ls20-9607627b.a1b2c3d4-e5f6-7890-abcd-ef1234567890.recording.jsonl`

* guid 在每次进入游戏时生成，保证唯一

**存储路径**：`data/players/{player_name}/recordings/{game_id}/`

* 按游戏 ID 分子目录，方便查找同一游戏的所有录像

**每步记录格式**（与官方完全一致）：

```json
{"timestamp": "2026-05-03T14:30:22.123456+00:00", "data": {
  "game_id": "ls20-9607627b",
  "frame": [[5,5,5,...], [4,4,4,...], ...],
  "state": "NOT_FINISHED",
  "levels_completed": 2,
  "win_levels": 7,
  "action_input": {"id": 1, "data": {"game_id": "ls20-9607627b"}, "reasoning": null},
  "guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "full_reset": false,
  "available_actions": [1, 2, 3, 4]
}}
```

**最后一行汇总**（与官方一致）：

```json
{"timestamp": "2026-05-03T15:20:00.000000+00:00", "data": {
  "won": 0,
  "played": 1,
  "total_actions": 150,
  "levels_completed": 3,
  "cards": {
    "ls20-9607627b": {
      "game_id": "ls20-9607627b",
      "total_plays": 1,
      "guids": ["a1b2c3d4-..."],
      "levels_completed": [3],
      "states": ["NOT_FINISHED"],
      "actions": [150],
      "actions_by_level": [[[1,30],[2,80],[3,150]]],
      "resets": [2],
      "total_actions": 150
    }
  }
}}
```

### 录像索引文件

**文件路径**：`data/players/{player_name}/recordings/{game_id}/index.json`

记录同一玩家对同一游戏的所有录像元数据，并标记"首次通关里程碑"：

```json
{
  "game_id": "ls20-9607627b",
  "player": "alice",
  "first_win_index": 2,
  "sessions": [
    {
      "guid": "a1b2c3d4-...",
      "filename": "ls20-9607627b.a1b2c3d4-....recording.jsonl",
      "started_at": "2026-05-01T10:00:00+00:00",
      "ended_at": "2026-05-01T10:30:00+00:00",
      "total_actions": 150,
      "levels_completed": 3,
      "final_state": "NOT_FINISHED",
      "phase": "learning"
    },
    {
      "guid": "b2c3d4e5-...",
      "filename": "ls20-9607627b.b2c3d4e5-....recording.jsonl",
      "started_at": "2026-05-03T14:00:00+00:00",
      "ended_at": "2026-05-03T15:00:00+00:00",
      "total_actions": 300,
      "levels_completed": 6,
      "final_state": "NOT_FINISHED",
      "phase": "learning"
    },
    {
      "guid": "c3d4e5f6-...",
      "filename": "ls20-9607627b.c3d4e5f6-....recording.jsonl",
      "started_at": "2026-05-05T09:00:00+00:00",
      "ended_at": "2026-05-05T11:00:00+00:00",
      "total_actions": 546,
      "levels_completed": 7,
      "final_state": "WIN",
      "phase": "learning"
    },
    {
      "guid": "d4e5f6a7-...",
      "filename": "ls20-9607627b.d4e5f6a7-....recording.jsonl",
      "started_at": "2026-05-10T20:00:00+00:00",
      "ended_at": "2026-05-10T20:30:00+00:00",
      "total_actions": 200,
      "levels_completed": 7,
      "final_state": "WIN",
      "phase": "practice"
    }
  ]
}
```

**phase 字段说明**：

* `"learning"` — 首次通关之前的所有尝试（包括未通关和首次通关那次）

* `"practice"` — 首次通关之后的游玩

**first\_win\_index**：指向 sessions 数组中首次通关的索引，方便快速定位"学习阶段"数据。

***

## 实施步骤

### Step 1: 新增玩家管理模块 `human_player/player_manager.py`

```python
class PlayerManager:
    def __init__(self):
        # 从 user_config.json 读取当前玩家

    def get_current_player(self) -> str
    def set_player(self, name: str) -> None
    def list_players(self) -> list[str]
    def get_player_data_dir(self, name: str = None) -> str
    # 返回 data/players/{name}/
    def get_recordings_dir(self, game_id: str, name: str = None) -> str
    # 返回 data/players/{name}/recordings/{game_id}/
```

* 默认玩家名 `"default"`

* 切换玩家时自动创建目录

* 持久化到 `data/user_config.json` 的 `current_player` 字段

### Step 2: 新增官方格式录像模块 `human_player/official_recording.py`

```python
ACTION_ID_MAP = {
    GameAction.RESET: 0,
    GameAction.ACTION1: 1,
    GameAction.ACTION2: 2,
    GameAction.ACTION3: 3,
    GameAction.ACTION4: 4,
    GameAction.ACTION5: 5,
    GameAction.ACTION6: 6,
    GameAction.ACTION7: 7,
}

class OfficialRecordingManager:
    def __init__(self, player_manager: PlayerManager):
        self._player_manager = player_manager
        self._guid = None
        self._file = None
        self._game_id = None
        self._win_levels = 0
        self._step_count = 0
        self._levels_at_start = 0  # 进入时的 levels_completed
        self._actions_by_level = {}  # {level: action_count}
        self._reset_count = 0
        self._current_level_actions = 0
        self._start_time = None

    def start_session(self, game_id: str, win_levels: int,
                      levels_at_start: int = 0) -> str:
        """开始一次录像会话，返回 guid"""
        # 1. 生成 guid
        # 2. 打开文件 data/players/{player}/recordings/{game_id}/{game_id}.{guid}.recording.jsonl
        # 3. 记录初始状态

    def record_step(self, action: GameAction, action_data: dict,
                    obs, available_actions: list) -> None:
        """记录一步操作"""
        # 构建 action_input: {"id": ACTION_ID_MAP[action], "data": {...}, "reasoning": null}
        # 构建 data dict，包含 frame, state, levels_completed, win_levels, action_input, guid, full_reset, available_actions
        # 写入 JSONL

    def end_session(self, final_state: str) -> None:
        """结束录像会话，写入汇总行 + 更新索引"""
        # 1. 写入汇总行（won, played, total_actions, levels_completed, cards）
        # 2. 关闭文件
        # 3. 更新 index.json
        #    - 追加 session 记录
        #    - 判断 phase: 如果 first_win_index 未设置且 final_state=="WIN" → 设 first_win_index
        #    - phase: index < first_win_index → "learning", 否则 → "practice"

    def get_session_index(self, game_id: str) -> dict:
        """获取某游戏的录像索引"""

    def list_sessions(self, game_id: str = None) -> list[dict]:
        """列出录像"""
```

**full\_reset 判断逻辑**：

* 当玩家执行 RESET 且 `levels_completed` 回到 0 时，`full_reset = True`

* 当玩家执行 RESET 但仍在同一关时，`full_reset = False`

* 当玩家从菜单选择"新游戏"（从第1关开始）时，第一次 RESET 标记为 `full_reset = True`

**actions\_by\_level 追踪**：

* 维护 `_current_level` 和 `_current_level_actions` 计数器

* 当 `levels_completed` 变化时，记录上一关的总动作数，开始新关计数

* 最终写入汇总行的 `actions_by_level`

### Step 3: 修改 `human_player/config.py`

新增：

```python
PLAYERS_DIR = os.path.join(DATA_DIR, "players")
```

### Step 4: 修改 `human_player/__main__.py`

集成官方录像和玩家系统：

1. **初始化**：

   * 创建 `PlayerManager` 和 `OfficialRecordingManager`

   * 根据当前玩家设置数据目录

2. **主菜单**：

   * 显示当前玩家名

   * 增加"切换玩家(P)"选项

3. **开始游戏**：

   * `official_recording.start_session(game_id, win_levels, levels_at_start)`

   * `levels_at_start` 来自 LevelManager（自动接续功能）

   * 保留现有 `recording_manager.start_session()`

4. **每步动作**：

   * `official_recording.record_step(action, data, obs, available_actions)`

   * 保留现有 `recording_manager.record_step()`

5. **关卡失败重试**：不结束 session，继续记录

6. **退出游戏**（ESC 或返回菜单）：

   * `official_recording.end_session(final_state)` — final\_state 根据当前状态判断

   * 保留现有 `recording_manager.end_session()`

7. **全部通关**：

   * `official_recording.end_session("WIN")`

8. **玩家切换**：

   * 切换后，`OfficialRecordingManager` 使用新玩家的数据目录

   * `LevelManager` 和 `StatsManager` 的数据路径也跟随切换

### Step 5: 修改 `human_player/menu.py`

* 主菜单增加"切换玩家(P)"按钮，显示当前玩家名

* 切换玩家界面：

  * 列出已有玩家供选择

  * 输入新玩家名创建

  * ESC 返回

### Step 6: 修改 `human_player/game_manager.py`

* 添加 `get_frame_as_2d_array()` 方法：返回 obs.frame 的原始 2D 数组

* 添加 `get_available_action_ids()` 方法：将 env.action\_space 转为 ID 列表

* 添加 `is_full_reset()` 方法：判断最近一次 RESET 是否为 full\_reset

* 确保 `win_levels`（max\_levels）可获取

### Step 7: 修改 `human_player/level_manager.py` 和 `human_player/stats_manager.py`

* 数据路径跟随玩家切换

* 构造函数接受 `player_data_dir` 参数

* 当玩家切换时，重新加载数据

***

## 文件变更清单

| 文件                                   | 操作 | 说明                   |
| ------------------------------------ | -- | -------------------- |
| `human_player/player_manager.py`     | 新建 | 玩家管理器                |
| `human_player/official_recording.py` | 新建 | 官方格式录像管理器            |
| `human_player/config.py`             | 修改 | 新增 PLAYERS\_DIR      |
| `human_player/__main__.py`           | 修改 | 集成官方录像和玩家系统          |
| `human_player/menu.py`               | 修改 | 增加玩家切换 UI            |
| `human_player/game_manager.py`       | 修改 | 添加 frame/action 辅助方法 |
| `human_player/level_manager.py`      | 修改 | 数据路径跟随玩家             |
| `human_player/stats_manager.py`      | 修改 | 数据路径跟随玩家             |
| `human_player/recording.py`          | 不变 | 保留现有轻量级录像            |

***

## 数据目录结构

```
data/
├── players/
│   ├── default/
│   │   ├── recordings/
│   │   │   ├── ls20-9607627b/
│   │   │   │   ├── index.json                          ← 录像索引
│   │   │   │   ├── ls20-9607627b.a1b2c3d4-....recording.jsonl
│   │   │   │   ├── ls20-9607627b.b2c3d4e5-....recording.jsonl
│   │   │   │   └── ls20-9607627b.c3d4e5f6-....recording.jsonl
│   │   │   └── ls20-abcdef/
│   │   │       ├── index.json
│   │   │       └── ...
│   │   ├── records/              ← 现有成绩记录（跟随玩家）
│   │   └── progress.json         ← 现有关卡进度（跟随玩家）
│   ├── alice/
│   │   ├── recordings/
│   │   └── ...
│   └── bob/
│       └── ...
├── recordings/                   ← 现有轻量级录像（保持不变，全局共享）
└── user_config.json              ← 新增 current_player 字段
```

***

## 录像生命周期示例

### 场景：玩家 alice 首次接触 ls20-9607627b

```
Day 1: alice 进入游戏 → 打到第3关退出
  → 生成 ls20-9607627b.guid1.recording.jsonl (NOT_FINISHED, levels=3)
  → index.json: sessions=[{phase:"learning", ...}], first_win_index=null

Day 3: alice 继续 → 打到第6关退出
  → 生成 ls20-9607627b.guid2.recording.jsonl (NOT_FINISHED, levels=6)
  → index.json: sessions=[..., {phase:"learning", ...}], first_win_index=null

Day 5: alice 继续 → 通关！
  → 生成 ls20-9607627b.guid3.recording.jsonl (WIN, levels=7)
  → index.json: sessions=[..., {phase:"learning", ...}], first_win_index=2

Day 10: alice 二次游玩 → 更快通关
  → 生成 ls20-9607627b.guid4.recording.jsonl (WIN, levels=7)
  → index.json: sessions=[..., {phase:"practice", ...}], first_win_index=2
```

**分析时**：

* `sessions[0:3]`（phase="learning"）= 完整学习过程

* `sessions[3:]`（phase="practice"）= 熟练度对比数据

* `first_win_index=2` 可快速定位首次通关

***

## 兼容性说明

* 现有 `RecordingManager`（轻量级录像）完全保留，不受影响

* 现有全局 `data/recordings/` 目录继续工作

* `LevelManager` 和 `StatsManager` 数据路径改为跟随玩家，但默认玩家 `"default"` 使用原有数据位置，保证向后兼容

* 官方格式录像文件较大（含 frame 数据），这是官方标准格式的必要代价

* `index.json` 是我们自己的增强，不影响官方格式的兼容性

