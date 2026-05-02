# 动作参考手册

## 概述

所有 ARC-AGI-3 游戏实现了一套标准化的动作接口，共 7 种核心动作。这套接口设计让智能体无需了解游戏具体规则就能开始交互，但要通过观察和推理来理解每种动作在不同游戏中的实际效果。

## 标准动作列表

| 动作 | 类型 | 语义映射 | 说明 |
|------|------|---------|------|
| `RESET` | 控制 | — | 初始化或重启游戏/关卡状态 |
| `ACTION1` | 简单 | 上（Up） | 具体效果因游戏而异 |
| `ACTION2` | 简单 | 下（Down） | 具体效果因游戏而异 |
| `ACTION3` | 简单 | 左（Left） | 具体效果因游戏而异 |
| `ACTION4` | 简单 | 右（Right） | 具体效果因游戏而异 |
| `ACTION5` | 简单 | 交互 | 交互/选择/旋转/附加/执行等 |
| `ACTION6` | 复杂 | 点击 | 需要 x,y 坐标（0-63 范围） |
| `ACTION7` | 简单 | 撤销 | 撤销上一步操作 |

## 动作分类

### 简单动作（Simple Actions）

ACTION1-ACTION5 和 ACTION7 是简单动作，只需要指定动作名称即可。

```python
from arcengine import GameAction

obs = env.step(GameAction.ACTION1)
obs = env.step(GameAction.ACTION5)
obs = env.step(GameAction.ACTION7)
```

### 复杂动作（Complex Action）

ACTION6 是唯一的复杂动作，需要额外提供 x,y 坐标。

```python
action = GameAction.ACTION6
action.set_data({
    "x": random.randint(0, 63),
    "y": random.randint(0, 63),
})
obs = env.step(action)
```

### 判断动作类型

```python
action = GameAction.ACTION1
if action.is_simple():
    print("简单动作")
elif action.is_complex():
    print("复杂动作，需要坐标")
```

## RESET 动作

RESET 是特殊的控制动作，用于：

1. **首次开始游戏** — 创建游戏会话并获取初始帧
2. **关卡重置** — 重新开始当前关卡
3. **游戏结束恢复** — 从 GAME_OVER 状态恢复

**注意**：在竞赛模式（COMPETITION）下，只允许关卡重置，不允许游戏重置（Game Reset 会自动降级为 Level Reset）。

## 可用动作（Available Actions）

每个游戏明确声明了可用的动作集合。关键点：

1. **不是所有游戏都支持所有动作** — 每个游戏有自己的可用动作子集
2. **帧元数据指示可用动作** — 每次动作后返回的数据会标明当前可用的动作
3. **ACTION6 不提供活跃坐标** — 如果 ACTION6 可用，只表示其可用性，不指定哪些坐标是有效的

### 编程获取可用动作

```python
env = arc.make("ls20")
print(env.action_space)
```

### 利用可用动作信息优化策略

```python
for step in range(100):
    available = env.action_space
    action = choose_from_available(available)
    obs = env.step(action)
```

智能体可以利用可用动作信息缩小动作空间，制定更有效的策略。

## 人类键位映射

在 ARC-AGI-3 网页 UI 中手动游玩时，可使用以下键位：

### WASD + Space 方案

| 动作 | 按键 |
|------|------|
| ACTION1（上） | W |
| ACTION2（下） | S |
| ACTION3（左） | A |
| ACTION4（右） | D |
| ACTION5（交互） | Space |
| ACTION6（点击） | 鼠标点击 |
| ACTION7（撤销） | Ctrl/Cmd + Z |

### 方向键 + F 方案

| 动作 | 按键 |
|------|------|
| ACTION1（上） | ↑ |
| ACTION2（下） | ↓ |
| ACTION3（左） | ← |
| ACTION4（右） | → |
| ACTION5（交互） | F |
| ACTION6（点击） | 鼠标点击 |
| ACTION7（撤销） | Ctrl/Cmd + Z |

## 游戏结束状态的处理

当游戏进入 `GAME_OVER` 状态时：

- 只能发送 `RESET`
- 发送其他动作（ACTION1-7）会返回 `400 Bad Request`
- 收到 `400` 错误时，检查游戏是否已结束，然后发送 `RESET`

```python
from arcengine import GameState

obs = env.step(GameAction.ACTION1)
if obs.state == GameState.GAME_OVER:
    obs = env.step(GameAction.RESET)
```

## 动作与推理（Reasoning）

每个动作可以附带推理信息，这在调试和回放分析时非常有用：

```python
action = GameAction.ACTION1
action.reasoning = "观察到目标在上方，选择向上移动"
obs = env.step(action)
```

对于复杂动作：

```python
action = GameAction.ACTION6
action.set_data({"x": 10, "y": 20})
action.reasoning = {"action": "ACTION6", "reason": "点击目标位置"}
obs = env.step(action)
```

推理信息会记录在回放文件中，方便事后分析智能体的决策过程。

## 参见

- [游戏机制详解](game-mechanics.md) — 游戏状态和帧数据
- [智能体开发指南](agent-development.md) — 如何在智能体中使用动作
- [REST API 参考](rest-api.md) — 通过 API 提交动作
