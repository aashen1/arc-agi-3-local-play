# 人机对比框架

## 概述

本项目的核心目标之一是系统化地对比人类与 AI 在 ARC-AGI-3 游戏上的表现。本文档建立了一个对比框架，定义了对比的维度、方法和数据收集方式。

## 对比维度

### 1. 效率维度

| 指标 | 说明 |
|------|------|
| 总动作数 | 完成关卡/游戏使用的动作总数 |
| 每关卡动作数 | 单个关卡的动作数 |
| RHAE 得分 | 官方评分（人类基线 / AI 动作数）² |
| 无效动作比例 | 不改变游戏状态或使状态变差的动作占比 |

### 2. 完成度维度

| 指标 | 说明 |
|------|------|
| 关卡完成率 | 成功完成的关卡比例 |
| 游戏完成率 | 完成所有关卡的游戏比例 |
| 最高关卡 | 在每个游戏中到达的最高关卡 |

### 3. 策略维度

| 指标 | 说明 |
|------|------|
| 探索策略 | 是否系统化探索 vs 随机尝试 |
| 规则发现速度 | 从观察到理解游戏规则用了多少步 |
| 策略调整 | 发现规则后是否调整策略 |
| 错误恢复 | 从错误中恢复的能力 |

### 4. 泛化维度

| 指标 | 说明 |
|------|------|
| 跨游戏泛化 | 在一个游戏中学到的策略是否迁移到其他游戏 |
| 新游戏适应 | 面对全新游戏的初始表现 |
| 规则变化适应 | 游戏规则微妙变化时的适应能力 |

## 人类数据收集

### 收集方法

1. **在线游玩** — 在 [arcprize.org/tasks](https://arcprize.org/tasks) 上游玩，系统自动记录
2. **脚本辅助** — 使用 Toolkit 的 `render_mode="terminal"` 在终端中游玩，手动记录动作
3. **录像分析** — 录屏后逐帧分析决策过程

### 需要记录的数据

```python
human_play_data = {
    "game_id": "ls20",
    "player_id": "human_001",
    "timestamp": "2026-05-03T10:00:00",
    "levels": [
        {
            "level": 1,
            "actions": ["RESET", "ACTION1", "ACTION3", "ACTION5"],
            "action_count": 4,
            "result": "WIN",
            "time_seconds": 12.5,
            "notes": "快速识别了移动规则"
        },
        {
            "level": 2,
            "actions": ["RESET", "ACTION1", "ACTION2", "ACTION1", "ACTION5"],
            "action_count": 5,
            "result": "WIN",
            "time_seconds": 18.3,
            "notes": "需要试错才发现交互规则"
        }
    ]
}
```

### 人类游玩建议

- **首次游玩**：不要提前了解游戏规则，模拟 AI 的"零样本"场景
- **记录思考过程**：边玩边口述或写下你的推理过程
- **多次游玩**：同一游戏玩多次，观察学习曲线
- **不同游戏**：尝试所有可用游戏，建立全面的基线

## AI 数据收集

### 不同 AI 技术的对比

| 技术 | 优势 | 劣势 | 适用场景 |
|------|------|------|---------|
| 随机智能体 | 基线对比 | 无策略 | 最低基线 |
| LLM Agent | 语言推理能力 | 动作空间理解弱 | 需要语义理解的场景 |
| Fast LLM | 速度快 | 准确性低 | 时间敏感场景 |
| ReasoningLLM | 深度推理 | 慢、成本高 | 复杂推理场景 |
| 强化学习 | 可优化策略 | 需要大量训练 | 可重复训练的场景 |
| 混合架构 | 灵活组合 | 复杂度高 | 综合场景 |

### 运行 AI 实验

```bash
# 随机基线
uv run main.py --agent=random --game=ls20 --tags="baseline,random"

# LLM 基线
uv run main.py --agent=llm --game=ls20 --tags="baseline,llm,gpt-4o-mini"

# 推理 LLM
uv run main.py --agent=reasoningllm --game=ls20 --tags="experiment,reasoning,o4-mini"
```

## 对比分析方法

### 1. 同游戏对比

同一游戏上，对比人类和不同 AI 的：

- 动作数分布
- 完成率
- RHAE 得分
- 策略差异（通过回放分析）

### 2. 同技术跨游戏对比

同一 AI 技术在不同游戏上的表现差异，观察泛化能力。

### 3. 学习曲线对比

- 人类：多次游玩同一游戏的进步曲线
- AI：不同 prompt 策略或模型版本的改进曲线

### 4. 错误模式分析

- 人类常犯的错误类型
- AI 常犯的错误类型
- 两者是否在相同的关卡上遇到困难

## 数据记录模板

建议在 `experiments/` 目录下按以下结构组织实验数据：

```
experiments/
├── 2026-05-03_ls20_human/
│   ├── play_data.json
│   ├── notes.md
│   └── screenshots/
├── 2026-05-03_ls20_random_agent/
│   ├── scorecard.json
│   └── recording.jsonl
├── 2026-05-03_ls20_llm_agent/
│   ├── scorecard.json
│   └── recording.jsonl
└── comparison/
    └── ls20_human_vs_ai.md
```

## 回放分析

回放（Recording）是对比人类和 AI 策略的重要工具。

### 在线回放

- 地址：`https://arcprize.org/replay/<guid>`
- 通过记分卡页面访问
- 可视化展示每一步的游戏状态和动作

### 本地回放文件

Swarm 运行时自动保存在 `recordings/` 目录，格式为 JSONL：

```
ls20-6cbb1acf0530.random.100.a1b2c3d4.recording.jsonl
```

文件名格式：`{game_id}.{agent_type}.{max_actions}.{guid}.recording.jsonl`

### 回放文件内容

每行一个 JSON 对象：

```json
{
    "timestamp": "2024-01-15T10:30:45.123456+00:00",
    "data": {
        "game_id": "ls20-016295f7601e",
        "frame": [...],
        "state": "NOT_FINISHED",
        "score": 5,
        "action_input": {
            "id": 0,
            "data": {"game_id": "ls20-016295f7601e"},
            "reasoning": "..."
        },
        "guid": "...",
        "full_reset": false
    }
}
```

## 关键研究问题

通过人机对比，我们希望回答：

1. **效率差距** — AI 需要比人类多多少动作才能完成同样的关卡？
2. **规则理解** — AI 是否真正"理解"了游戏规则，还是只是在模式匹配？
3. **泛化能力** — 人类能快速适应新游戏，AI 能做到吗？
4. **策略差异** — 人类和 AI 解决同一问题的策略有何不同？
5. **错误模式** — 人类和 AI 在哪些地方容易犯错？错误类型是否相同？
6. **学习速度** — 人类从错误中学习的速度 vs AI 改进的速度

## 参见

- [评分系统详解](scoring-system.md) — RHAE 评分方法
- [智能体开发指南](agent-development.md) — 构建 AI 智能体
- [游戏机制详解](game-mechanics.md) — 游戏结构和交互方式
