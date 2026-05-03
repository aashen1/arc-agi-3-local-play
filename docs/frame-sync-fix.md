# 帧同步与动画播放修复

## 问题描述

在 Pygame 实现的人类玩家控制台中，存在三个与帧更新相关的问题：

### Case 1：通关后落后一帧

当玩家通过某一关时，官方网页版会在踩到通关点的瞬间进行结算，然后下一帧直接渲染下一关的初始地图。但 Pygame 实现中，通关后仍然停在终点画面，再次按键会直接跳过下一关的初始状态，进入走了一步之后的状态。

**现象**：第 N 关通关 → 画面仍显示第 N 关终点 → 按键 → 直接显示第 N+1 关走了一步后的状态。

### Case 2：推板动画缺失

在 LS20 游戏中，当方块踩上推板时，引擎会将方块一路推到撞上墙为止。官方实现会渲染逐格推动的动画，但 Pygame 实现中看不到推动过程，方块坐标已经到达终点，再按键才会刷新到最终位置。

**现象**：踩上推板 → 看不到推动动画 → 方块"瞬移"到被推后的位置。

### Case 3：SU15 游戏交互反馈缺失

SU15 游戏中有鼠标点击融合机制：
- 点击后不会立即完成融合，而是先刷新白圈动画
- 白圈是向内收缩的动画（单游戏步内发生，不占用步数）
- 尺寸不匹配时会有闪烁并弹回的动画

但 Pygame 实现中：
- 点击第一下没有视觉反馈（白圈不出现）
- 白圈显示为静态圆圈，没有收缩动画
- 尺寸不匹配的闪烁弹回动画完全看不到

**核心问题**：玩家操作使游戏状态已更新，但屏幕显示的仍是旧状态，需要第 X+1 次操作才能看到第 X 次操作的结果。

## 根因分析

### 引擎架构

通过阅读 `arcengine` 和 `arc_agi` 库源码，发现 ARC-AGI-3 引擎的 `perform_action()` 方法（[base_game.py](b:\useradmin\.cache\rattler\uv-cache\archive-v0\Yw20ssF-oTdZF6ysPS8LL\arcengine\base_game.py#L189-L260)）会为每个动作生成**多帧动画序列**：

```python
@final
def perform_action(self, action_input: ActionInput, raw: bool = False) -> FrameDataRaw:
    # ...
    frame_list: list[ndarray] = []
    
    while not self.is_action_complete():  # 动画循环
        if self._next_level:
            self._really_set_next_level()  # 关卡切换
        else:
            self.step()                     # 游戏逻辑（推板、融合等）
        frame = self.camera.render(sprites)
        frame_list.append(frame)           # 收集每一帧
    
    frame_raw.frame = frame_list           # 返回帧列表
    return frame_raw
```

`FrameDataRaw.frame` 是一个 `List[ndarray]`，包含该动作从开始到结束的所有渲染帧。例如：
- 推板推动：可能产生 5-10 帧，逐格显示方块移动
- 关卡切换：可能产生 2-3 帧，包含过渡效果
- 融合动画：可能产生 3-5 帧，包含白圈收缩效果

### 原实现的问题

**问题 1：只取 `frame[0]`**

原 `get_current_frame()` 实现：
```python
def get_current_frame(self) -> np.ndarray | None:
    frame = obs.frame
    if isinstance(frame, list):
        return np.array(frame[0]) if frame else None  # ← 只取第一帧
```

这导致：
- `frame[0]` 是动作执行后**第一子步**的状态
- `frame[-1]` 才是动作完成后的**最终状态**
- 玩家看到的永远是"落后一帧"的画面

**问题 2：完全丢弃动画帧**

引擎返回的 `frame[1:]` 帧（动画中间帧）被完全忽略，导致：
- 推板推动动画不可见
- 融合收缩动画不可见
- 通关过渡效果不可见

**问题 3：WIN 后错误调用 `env.reset()`**

原主循环在 WIN overlay 消失时：
```python
elif overlay_state == "win":
    # ...
    game_manager.env.reset()  # ← 错误！
```

根据 `ARCBaseGame.handle_reset()` 逻辑：
```python
def handle_reset(self) -> None:
    if self._action_count == 0 or self._state == GameState.WIN:
        self.full_reset()  # ← 回到第 0 关！
```

但引擎在通关时已通过 `next_level()` 推进了关卡，`env.reset()` 会触发 `full_reset()` 将所有关卡重置回初始状态，而不是继续到下一关。

## 修复思路

### 方案：动画帧缓冲系统

不改变游戏逻辑的前提下，在 `GameManager` 中添加动画帧缓冲，实现多帧动画的平滑播放。

### 数据流

```
env.step(action)
    ↓
返回 FrameDataRaw
    ├─ frame: [frame_0, frame_1, frame_2, ..., frame_N]  ← 动画序列
    ├─ state: GameState.WIN / NOT_FINISHED / ...
    └─ levels_completed: int
    ↓
_start_animation(obs)
    ├─ len(frame) > 1 → 存入 _anim_frames，开始播放
    └─ len(frame) == 1 → 清空动画缓冲（单帧动作）
    ↓
主循环每帧调用 advance_animation()
    ├─ 计算经过时间 → 目标帧索引
    └─ 更新 _anim_index
    ↓
get_current_frame()
    ├─ is_animating() → 返回 _anim_frames[_anim_index]
    └─ not animating → 返回 obs.frame[-1]
```

### 关键设计决策

| 决策 | 说明 |
|------|------|
| **基于时间的动画播放** | 使用 `time.time()` 计算经过时间，不依赖固定帧计数，避免与游戏 FPS（30）耦合 |
| **15 FPS 动画速率** | 独立于游戏渲染 FPS（30），15 FPS 足够流畅且不会过快 |
| **动画期间阻塞输入** | 防止玩家在动画播放期间误操作，但允许按任意键跳过动画 |
| **跳过动画机制** | 玩家按任意键立即跳到动画最终帧，恢复交互 |

## 具体修改

### 1. `human_player/game_manager.py`

#### 新增动画状态

```python
ANIMATION_FPS = 15

class GameManager:
    def __init__(self):
        # ... 原有状态 ...
        self._anim_frames: list[np.ndarray] = []
        self._anim_index: int = 0
        self._anim_start_time: float = 0.0
        self._anim_frame_duration: float = 1.0 / ANIMATION_FPS
```

#### 新增方法

| 方法 | 职责 |
|------|------|
| `is_animating()` | 检查是否正在播放动画 |
| `advance_animation()` | 每帧调用，根据时间推进动画索引 |
| `skip_animation()` | 立即结束动画，跳到最终状态 |
| `_start_animation(obs)` | 解析 `obs.frame`，启动动画播放 |

#### 修改 `get_current_frame()`

```python
def get_current_frame(self) -> np.ndarray | None:
    if self.is_animating():
        return self._anim_frames[self._anim_index]  # 动画帧
    
    obs = self.env.observation_space if self.env else None
    if obs is None or obs.frame is None:
        return None
    frame = obs.frame
    if isinstance(frame, list):
        return np.array(frame[-1])  # 最终帧（修复 frame[0] → frame[-1]）
    return np.array(frame)
```

#### 修改 `execute_action()` 和 `reset_level()`

在每次 `env.step()` 或 `env.reset()` 后调用 `_start_animation()`：

```python
def execute_action(self, action: GameAction, data: dict = None):
    # ... 调用 env.step() ...
    if obs:
        self._update_from_obs(obs)
        self._start_animation(obs)  # 启动动画
    return obs
```

### 2. `human_player/__main__.py`

#### 主循环动画处理

```python
elif state == "GAME":
    action_result = False
    if game_manager.is_animating():
        # 动画播放期间：只处理跳过和退出
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                game_manager.skip_animation()
                action_result = "exit"
            else:
                game_manager.skip_animation()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            game_manager.skip_animation()
    else:
        # 正常交互模式
        action_result = _handle_game_event(event, game_manager, renderer)
```

#### 每帧推进动画

```python
elif state == "GAME":
    game_manager.advance_animation()  # 新增
    frame = game_manager.get_current_frame()
    # ... 渲染 ...
```

#### 修复 WIN overlay 逻辑

```python
if overlay_state == "win":
    if game_manager.levels_completed >= game_manager.max_levels:
        overlay_state = "all_complete"
    else:
        overlay_state = None
        # 移除 game_manager.env.reset() ← 修复！
        game_manager.step_count = 0
        game_manager.level_start_time = time.time()
```

### 3. `human_player/renderer.py`

防御性修复：

```python
def _draw_grid(self, frame, mouse_grid_pos):
    if isinstance(frame, list):
        grid = np.array(frame[-1]) if frame else None  # frame[0] → frame[-1]
    else:
        grid = np.array(frame)
```

## 验收结果

### 测试用例

| 测试 | 操作 | 预期结果 | 实际结果 |
|------|------|----------|----------|
| T1 | 启动游戏，进入 LS20 | 正常显示初始关卡 | ✅ 通过 |
| T2 | 踩上推板 | 看到方块逐格推动动画 | ✅ 通过 |
| T3 | 通关 LS20 | 看到通关动画，按任意键进入下一关初始状态 | ✅ 通过 |
| T4 | 通关后继续游戏 | 进入下一关（而非重置回第 0 关） | ✅ 通过 |
| T5 | SU15 点击融合 | 白圈出现并收缩 | ✅ 通过 |
| T6 | SU15 尺寸不匹配 | 看到闪烁弹回动画 | ✅ 通过 |
| T7 | 动画播放期间按 ESC | 跳过动画并退出到菜单 | ✅ 通过 |
| T8 | 动画播放期间按其他键 | 跳过动画，继续游戏 | ✅ 通过 |

### 单元测试

```
Test 1 - Single frame: is_animating=False (expected False)  ✅
Test 2 - Multi frame: is_animating=True (expected True)     ✅
Test 2 - Frame count: 5 (expected 5)                        ✅
Test 3 - Last frame value: 2 (expected 2)                   ✅
Test 4 - Anim frame 0 value: 0 (expected 0)                 ✅
Test 5 - After 2.5 frame durations, target_index=2          ✅

GameManager animation tests passed!                         ✅
```

### 集成测试

```
Single frame: is_animating=False (expected False)           ✅
Multi frame: is_animating=True (expected True)              ✅
Current frame value: 0 (expected 0)                         ✅
After 3 frames: still_animating=True (expected True)        ✅
Current frame value: 3 (expected 3)                         ✅
After skip: is_animating=False (expected False)             ✅

GameManager animation tests passed!                         ✅
```

## 技术细节

### 动画时序

```
env.step() 返回帧序列 [F0, F1, F2, F3, F4]
  ↓
t=0.000s: _start_animation(), _anim_index=0, 显示 F0
t=0.033s: advance_animation(), elapsed=33ms, target_index=0, 仍显示 F0
t=0.067s: advance_animation(), elapsed=67ms, target_index=1, 显示 F1
t=0.100s: advance_animation(), elapsed=100ms, target_index=1, 仍显示 F1
t=0.133s: advance_animation(), elapsed=133ms, target_index=2, 显示 F2
...
t=0.267s: advance_animation(), elapsed=267ms, target_index=4, 显示 F4
t=0.300s: advance_animation(), elapsed=300ms, 动画结束，清空缓冲
```

### 性能影响

- **内存**：每个动作最多缓存 1000 帧（引擎限制），每帧 64x64 int8 = 4KB，最大 4MB
- **CPU**：`advance_animation()` 每帧一次浮点除法和比较，可忽略
- **渲染**：无额外开销，直接返回 numpy 数组

### 兼容性

- 单帧动作（大多数动作）：动画缓冲为空，行为与之前完全一致
- 多帧动作：自动播放动画，玩家可跳过
- 录像系统：不受影响，录制的是 `obs` 原始数据
- 记分卡：不受影响，统计的是 `step_count`

## 相关文件

- [human_player/game_manager.py](file:///b:/project/arcprize/taa3-try-arg-agi-3/human_player/game_manager.py) — 动画核心逻辑
- [human_player/__main__.py](file:///b:/project/arcprize/taa3-try-arg-agi-3/human_player/__main__.py) — 主循环动画处理
- [human_player/renderer.py](file:///b:/project/arcprize/taa3-try-arg-agi-3/human_player/renderer.py) — 渲染防御性修复
- [arcengine/base_game.py](b:\useradmin\.cache\rattler\uv-cache\archive-v0\Yw20ssF-oTdZF6ysPS8LL\arcengine\base_game.py) — 引擎动画循环源码（参考）

## Git 提交

```
commit e9bb79d
fix: resolve frame lag and missing animation in pygame renderer

- Change get_current_frame() to return frame[-1] instead of frame[0]
- Add animation frame buffer system with 15 FPS playback
- Fix WIN overlay dismissing: remove env.reset() call
- Fix _draw_grid() and get_frame_as_2d_list() to use frame[-1]
```
