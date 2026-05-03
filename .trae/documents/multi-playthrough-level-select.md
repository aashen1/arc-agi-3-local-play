# 实现计划：已通关大关的任意选关功能（多周目支持）

## 需求分析

当前有 3 种状态已实现，需要新增第 4 种：

| 状态 | 描述 | 当前行为 | 目标行为 |
|------|------|---------|---------|
| 1 | 没玩过 | 直接开始新游戏 | 不变 |
| 2 | 玩了一部分退出 | 弹窗：继续/新游戏/返回 | 不变 |
| 3 | 全部通关 | 直接从头开始（等同于状态1） | 弹窗：新游戏/选关/返回 |
| 4 | 通关后又重新玩到某关 | 同状态3（无法区分） | 弹窗：继续/新游戏/选关/返回 |

**核心问题**：当前进度系统只记录"哪些小关完成过"，无法区分"通关后又开始的新周目进度"。

## 解决方案

在进度数据中新增 `current_level` 字段，专门追踪通关后的新周目位置。

### 进度数据结构变更

```json
{
  "games": {
    "game-id": {
      "levels": { "0": {...}, "1": {...} },
      "total_levels": 10,
      "current_level": 5
    }
  }
}
```

`current_level` 语义：
- 不存在或 `null`：从未通关过，或通关后未开始新周目
- `0`：通关后刚点"新游戏"，从第0关开始
- `N`（0 < N < total）：新周目进行中，当前在第N关
- >= total：新周目也通关了，回到"已通关"状态

---

## 修改文件清单

### 1. `human_player/level_manager.py`

**新增方法：**

- `get_current_level(game_id) -> int | None`：获取新周目当前关卡
- `set_current_level(game_id, level_index)`：设置新周目当前关卡

**修改逻辑：** 无其他修改，`is_fully_completed` 和 `get_level_info` 已在之前添加。

### 2. `human_player/menu.py`

**新增方法：**

- `draw_completed_prompt(game_id, total, current_level, has_playthrough)`：通关后的选择弹窗
  - 有新周目进度时：3个按钮（继续/新游戏/选关）+ 返回
  - 无新周目进度时：2个按钮（新游戏/选关）+ 返回
  - 显示通关标记 ✓ 和当前周目进度信息

- `draw_level_select(game_id, total_levels, level_manager)`：关卡选择界面
  - 标题："Select Level - {game_id}"
  - 宫格排列所有小关按钮（5列），每格显示关卡编号
  - 已完成的小关：绿色边框 + 小勾
  - 新周目当前关：黄色高亮
  - 底部数字输入框：可输入关卡编号直接跳转
  - 返回按钮

- `handle_level_select_click(pos) -> str | None`：处理关卡选择界面的点击
  - 点击关卡按钮返回 `"level:N"`
  - 点击返回按钮返回 `"back"`

**新增实例属性：**

- `level_rects: list[pygame.Rect]`：关卡按钮的矩形区域
- `level_input_text: str`：数字输入框文本
- `level_input_active: bool`：输入框是否激活

**修改主菜单显示（`_draw_grid_menu` / `_draw_list_menu`）：**

- 对已通关且有新周目进度的游戏，在进度条旁额外显示周目进度文字（如 "R2:L5" 表示第2轮第5关）

### 3. `human_player/__main__.py`

**修改 `_check_resume` 函数：**

当前逻辑：
```python
if completed == 0 or next_level is None:
    return "new"
```

改为：
```python
if completed == 0:
    return "new"

if level_manager.is_fully_completed(game_id):
    current_level = level_manager.get_current_level(game_id)
    has_playthrough = current_level is not None and current_level < total
    return _show_completed_prompt(...)

# 原有的部分完成逻辑不变
```

**新增 `_show_completed_prompt` 函数：**

阻塞式事件循环，显示通关选择弹窗：
- 处理键盘快捷键（C/N/L/Q）
- 处理鼠标点击按钮
- 若选择"选关"，调用 `_show_level_select` 进入关卡选择

**新增 `_show_level_select` 函数：**

阻塞式事件循环，显示关卡选择界面：
- 处理关卡按钮点击
- 处理数字输入（0-9、回车、退格）
- 返回 `"level:N"` 或 `None`（返回上一级）

**修改 `_start_game` 函数：**

新增对 `"level:N"` 返回值的处理：
```python
if resume.startswith("level:"):
    level_index = int(resume.split(":")[1])
    game_manager.jump_to_level(level_index)
    level_manager.set_current_level(game_id, level_index)
elif resume == "new":
    if level_manager.is_fully_completed(game_id):
        level_manager.set_current_level(game_id, 0)
```

**修改 `_handle_win` 函数：**

通关后的新周目中，每次过关更新 `current_level`：
```python
if level_manager.is_fully_completed(game_manager.game_id):
    level_manager.set_current_level(
        game_manager.game_id, game_manager.levels_completed
    )
```

---

## 交互流程图

```
点击已通关游戏
  │
  ├─ 无新周目进度 ──→ 弹窗：[N]新游戏  [L]选关  [Q]返回
  │                     │          │         │
  │                     ↓          ↓         ↓
  │                  从头开始   选关界面    返回菜单
  │
  └─ 有新周目进度 ──→ 弹窗：[C]继续(L5)  [N]新游戏  [L]选关  [Q]返回
                         │            │          │         │
                         ↓            ↓          ↓         ↓
                    继续周目      从头开始    选关界面   返回菜单

选关界面
  │
  ├─ 点击关卡按钮 ──→ 返回 "level:N" ──→ 开始游戏（跳到第N关）
  ├─ 输入数字+回车 ──→ 返回 "level:N" ──→ 开始游戏（跳到第N关）
  └─ ESC/返回 ──→ 回到通关弹窗
```

---

## 玩家隔离

进度数据存储在 `data/players/<玩家名>/progress.json`，切换玩家时 `LevelManager` 会重新加载对应玩家的进度文件。`current_level` 字段自然随进度文件隔离，无需额外处理。

---

## 实施步骤

1. `level_manager.py`：添加 `get_current_level` / `set_current_level` 方法
2. `menu.py`：添加 `draw_completed_prompt` 方法
3. `menu.py`：添加 `draw_level_select` / `handle_level_select_click` 方法
4. `menu.py`：修改主菜单显示，为有新周目进度的游戏添加视觉标识
5. `__main__.py`：修改 `_check_resume` 逻辑，区分全通关状态
6. `__main__.py`：新增 `_show_completed_prompt` / `_show_level_select` 函数
7. `__main__.py`：修改 `_start_game` 支持 `"level:N"` 和新周目初始化
8. `__main__.py`：修改 `_handle_win` 更新新周目进度
9. 测试验证
