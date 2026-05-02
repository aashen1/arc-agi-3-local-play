# 智能体开发指南

## 概述

ARC-AGI-3 提供了两种开发智能体的方式：

1. **ARC-AGI Toolkit**（`arc-agi` Python 包）— 适合快速原型和本地开发
2. **ARC-AGI-3-Agents 仓库** — 完整的智能体框架，包含 Swarm 编排和多种模板

## 方式一：使用 ARC-AGI Toolkit

### 最简智能体

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
        action_data = {
            "x": random.randint(0, 63),
            "y": random.randint(0, 63),
        }

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

### 操作模式

```python
from arc_agi import Arcade, OperationMode

arc = Arcade(operation_mode=OperationMode.OFFLINE)
arc = Arcade(operation_mode=OperationMode.ONLINE)
arc = Arcade(operation_mode=OperationMode.COMPETITION)
```

也可通过环境变量设置：`OPERATION_MODE=COMPETITION`

### 记分卡管理

```python
arc = arc_agi.Arcade()

scorecard_id = arc.create_scorecard(
    tags=["experiment", "my-agent-v1"],
    source_url="https://github.com/my/repo",
    opaque={"custom_field": "any data"}
)

scorecard = arc.get_scorecard()
arc.close_scorecard()
```

### 本地 REST 服务器

启动本地 Flask 服务器，暴露与在线 API 相同的 REST 接口：

```python
arc = Arcade()
arc.listen_and_serve(port=8001)
```

这在 Kaggle 竞赛环境中也会使用，可以在本地复现 Kaggle 环境进行开发和测试。

高级用法：

```python
def on_close(scorecard):
    print(f"Scorecard closed: {scorecard.score}")

arc.listen_and_serve(
    port=8001,
    competition_mode=True,
    on_scorecard_close=on_close,
    save_all_recordings=True,
)
```

## 方式二：使用 ARC-AGI-3-Agents 仓库

### 克隆仓库

```bash
git clone https://github.com/arcprize/ARC-AGI-3-Agents.git
cd ARC-AGI-3-Agents
```

### 运行内置智能体

```bash
uv run main.py --agent=random --game=ls20
```

### 创建自定义智能体

#### 步骤 1：创建智能体文件

在 `agents/` 目录下创建新的 Python 文件：

```python
from .agent import Agent
from .structs import FrameData, GameAction, GameState
import random

class MyAwesomeAgent(Agent):

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        if latest_frame.state in [GameState.NOT_PLAYED, GameState.GAME_OVER]:
            action = GameAction.RESET
        else:
            action = random.choice([a for a in GameAction if a is not GameAction.RESET])

        if action.is_simple():
            action.reasoning = f"Chose {action.value} randomly"
        elif action.is_complex():
            action.set_data({
                "x": random.randint(0, 63),
                "y": random.randint(0, 63),
            })
            action.reasoning = {"action": action.value, "reason": "Random choice"}

        return action
```

#### 步骤 2：注册智能体

在 `agents/__init__.py` 中添加导入：

```python
from .my_awesome_agent import MyAwesomeAgent

__all__ = [
    "MyAwesomeAgent",
    "AVAILABLE_AGENTS",
]
```

#### 步骤 3：运行

```bash
uv run main.py --agent=myawesomeagent --game=ls20
```

### 核心接口

智能体必须实现两个方法：

| 方法 | 说明 |
|------|------|
| `is_done(frames, latest_frame)` | 判断游戏是否结束 |
| `choose_action(frames, latest_frame)` | 根据帧数据选择下一步动作 |

参数说明：

| 参数 | 类型 | 说明 |
|------|------|------|
| `frames` | `list[FrameData]` | 所有历史帧数据 |
| `latest_frame` | `FrameData` | 最新一帧的数据 |

## LLM 智能体模板

ARC-AGI-3-Agents 仓库内置了 4 种 LLM 智能体模板：

### LLM Agent

- 标准 OpenAI API 智能体
- 维护 10 条消息的对话历史
- 使用 function calling 选择动作
- 默认模型：gpt-4o-mini
- 用法：`--agent=llm`

### Fast LLM Agent

- 跳过观察步骤（DO_OBSERVATION=False）
- 更快但可能不够准确
- 默认模型：gpt-4o-mini
- 用法：`--agent=fastllm`

### ReasoningLLM

- 使用 OpenAI o4-mini 模型
- 捕获详细推理元数据（reasoning tokens, thought process）
- 默认模型：o4-mini
- 用法：`--agent=reasoningllm`

### GuidedLLM

- 使用最高级 o3 模型
- 包含显式的游戏特定规则/策略提示
- 仅用于教育目的，不会泛化到其他游戏
- 默认模型：o3
- 用法：`--agent=guidedllm`

### 运行示例

```bash
uv run main.py --agent=llm --game=ls20
uv run main.py --agent=fastllm
uv run main.py --agent=reasoningllm --game=ft09
```

### 处理 LLM 格式错误输出

LLM 可能返回无效动作，建议添加后处理：

```python
import re
import random
from agents.structs import GameAction

def safe_parse(model_response: str) -> GameAction:
    match = re.search(r"(RESET|ACTION[1-6])", model_response)
    if match:
        action_name = match.group(0).strip()
        try:
            return GameAction.from_name(action_name)
        except ValueError:
            pass
    valid_actions = [a for a in GameAction if a is not GameAction.RESET]
    return random.choice(valid_actions)
```

三种增强策略：

1. **后处理模型输出** — 用正则提取第一个有效动作
2. **回退到安全动作** — 解析失败时选择随机有效动作
3. **记录错误响应** — 在 reasoning 字段中记录，方便调试

## Benchmarking 工具

用于可重复地评估智能体表现。

### 安装

```bash
git clone git@github.com:arcprize/arc-agi-3-benchmarking.git
cd arc-agi-3-benchmarking
uv venv
uv sync
```

### 使用

```bash
uv run python -m arcagi3.runner --check
uv run python -m arcagi3.runner --list-games
uv run python -m arcagi3.runner --list-models
uv run python -m arcagi3.runner --game_id ls20 --config gpt-5-2-openrouter --max_actions 3
```

### 支持的模型提供商

OpenAI, Anthropic, Google Gemini, OpenRouter, Fireworks, Groq, DeepSeek, Hugging Face

## Swarm 编排

Swarm 用于在多个游戏上同时运行智能体。

### 命令

```bash
uv run main.py --agent <agent_name> [--game <game_filter>] [--tags <tag_list>]
```

### 参数

| 参数 | 短写 | 必需 | 说明 |
|------|------|------|------|
| `--agent` | `-a` | 是 | 智能体名称 |
| `--game` | `-g` | 否 | 游戏过滤（逗号分隔） |
| `--tags` | `-t` | 否 | 记分卡标签（逗号分隔） |

### Swarm 行为

- 每个游戏创建一个智能体实例
- 所有智能体使用线程并发运行
- 自动管理记分卡的打开和关闭
- 完成后自动清理
- 提供在线回放链接

### 示例

```bash
uv run main.py --agent=random
uv run main.py --agent=llm --game=ls20
uv run main.py --agent=llm --tags="experiment,gpt-4,baseline"
uv run main.py --agent=random --game="ls20,ft09"
```

## 常见问题

### 相对导入错误

如果移动了智能体文件位置，需要调整导入路径：

```python
# agents/my_agents/my_file.py
from ..agent import Agent
from ..structs import FrameData
```

### 智能体未找到

出现 `ValueError: Agent '<your-agent>' not found` 时检查：

1. 智能体类是否在 `agents` 目录下
2. 类名拼写是否正确
3. `--agent` 参数使用类名的小写形式
4. 是否已保存文件更改

## 参见

- [动作参考手册](actions-reference.md) — 动作接口详解
- [REST API 参考](rest-api.md) — 通过 API 与游戏交互
- [评分系统详解](scoring-system.md) — RHAE 评分方法
