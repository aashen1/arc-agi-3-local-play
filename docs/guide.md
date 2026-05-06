# 快速上手指南

## 环境配置

### 安装依赖

```bash
pixi install
```

### 设置 API Key（可选）

无 API Key 时使用匿名 Key，只能访问 3 个公开游戏。注册后可解锁全部公开游戏。

1. 前往 [arcprize.org/platform](https://arcprize.org/platform) 注册
2. 在用户资料中创建 API Key
3. 设置环境变量：

```bash
export ARC_API_KEY="your-api-key-here"
```

或写入 `.env` 文件：

```bash
echo 'ARC_API_KEY=your-api-key-here' > .env
```

## 第一个游戏

项目根目录已有 `play.py`：

```python
import arc_agi
from arcengine import GameAction

arc = arc_agi.Arcade()
env = arc.make("ls20", render_mode="terminal")

print(env.action_space)
obs = env.step(GameAction.ACTION1)
print(arc.get_scorecard())
```

运行：

```bash
pixi run python play.py
```

## 随机智能体

```python
import random
from arcengine import GameAction, GameState
import arc_agi

arc = arc_agi.Arcade()
env = arc.make("ls20", render_mode="terminal")

for step in range(100):
    action = random.choice(env.action_space)
    action_data = {}
    if action.is_complex():
        action_data = {"x": random.randint(0, 63), "y": random.randint(0, 63)}

    obs = env.step(action, data=action_data)

    if obs and obs.state == GameState.WIN:
        print(f"Game won at step {step}!")
        break
    elif obs and obs.state == GameState.GAME_OVER:
        env.reset()

scorecard = arc.get_scorecard()
if scorecard:
    print(f"Final Score: {scorecard.score}")
```

## 运行模式

```python
from arc_agi import Arcade, OperationMode

arc = Arcade(operation_mode=OperationMode.OFFLINE)    # 本地（推荐开发）
arc = Arcade(operation_mode=OperationMode.ONLINE)     # 在线（记分卡/回放）
arc = Arcade(operation_mode=OperationMode.COMPETITION) # 竞赛（排行榜必需）
```

| 模式 | 速度 | 记分卡 | 回放 | API Key |
|------|------|--------|------|---------|
| OFFLINE | ~2000 FPS | 无 | 无 | 不需要 |
| ONLINE | 受限 | 有 | 有 | 需要 |
| COMPETITION | 受限 | 有 | 有 | 需要 |

## 人类游玩

在 [arcprize.org/tasks](https://arcprize.org/tasks) 上用键盘/鼠标直接操作：

| 控制方案 | 上 | 下 | 左 | 右 | 交互 | 点击 | 撤销 |
|---------|---|---|---|---|------|------|------|
| WASD | W | S | A | D | Space | 鼠标 | Ctrl+Z |
| 方向键 | ↑ | ↓ | ← | → | F | 鼠标 | Ctrl+Z |

## 深入阅读

| 主题 | 文档 |
|------|------|
| 游戏结构、状态、关卡 | [game-mechanics.md](game-mechanics.md) |
| RHAE 评分公式和规则 | [scoring-system.md](scoring-system.md) |
| 7 种标准动作详解 | [actions-reference.md](actions-reference.md) |
| 构建自定义智能体 | [agent-development.md](agent-development.md) |
| REST API 端点和认证 | [rest-api.md](rest-api.md) |
| 人机对比方法论 | [human-vs-ai.md](human-vs-ai.md) |

## 有用的链接

- 官方文档：[docs.arcprize.org](https://docs.arcprize.org)
- 游戏列表：[arcprize.org/tasks](https://arcprize.org/tasks)
- ARC-AGI Toolkit：[github.com/arcprize/arc-agi](https://github.com/arcprize/arc-agi)
- ARC-AGI-3 Agents：[github.com/arcprize/ARC-AGI-3-Agents](https://github.com/arcprize/ARC-AGI-3-Agents)

