# CLAUDE.md — 项目总入口

## 项目目标

本项目旨在深度探索 **ARC-AGI-3**（第三代抽象与推理语料库）基准测试平台。核心目的有两个：

1. **人类选手体验** — 以人类身份亲自游玩 ARC-AGI-3 的各类游戏，建立对游戏机制、策略和难度的直觉理解
2. **AI 技术对比** — 尝试各种 AI 技术（LLM、强化学习、混合架构等）来玩同样的游戏，与人类表现进行系统化对比

通过人机对比，深入理解当前 AI 在抽象推理、泛化能力上的优势与不足。

## 项目环境

- **Python 环境**：使用 pixi 管理（`pixi install`）
- **核心依赖**：`arc-agi >= 0.9.8, < 0.10`（Python >= 3.14）
- **运行命令**：`pixi run python <script.py>`
- **禁止**：运行 `pip` 命令、查看 `.env` 文件内容
- **操作系统**：Windows 10 + Git Bash

## 文档索引

所有调研成果按主题拆分为独立文档，存储在 `docs/` 目录下：

| 文档 | 内容 |
|------|------|
| [docs/guide.md](docs/guide.md) | 快速上手指南 — 环境配置、第一个游戏、基本用法 |
| [docs/game-mechanics.md](docs/game-mechanics.md) | 游戏机制详解 — 网格结构、游戏状态、关卡设计、可用游戏 |
| [docs/scoring-system.md](docs/scoring-system.md) | 评分系统详解 — RHAE 评分公式、人类基线、加权聚合 |
| [docs/actions-reference.md](docs/actions-reference.md) | 动作参考手册 — 7 种标准动作、键位映射、复杂动作坐标 |
| [docs/agent-development.md](docs/agent-development.md) | 智能体开发指南 — 自定义智能体、LLM 智能体、Swarm 编排 |
| [docs/rest-api.md](docs/rest-api.md) | REST API 参考 — 端点、认证、会话管理、速率限制 |
| [docs/human-vs-ai.md](docs/human-vs-ai.md) | 人机对比框架 — 对比方法论、数据收集、分析维度 |

## 关键概念速查

| 术语 | 说明 |
|------|------|
| ARC-AGI-3 | 第三代抽象与推理基准，交互式游戏环境 |
| Arcade | Toolkit 主入口类 `arc_agi.Arcade()` |
| Environment | 一个可交互的游戏实例，通过 `arc.make("game_id")` 创建 |
| GameAction | 标准化动作枚举：RESET, ACTION1-7 |
| Scorecard | 记分卡，聚合智能体在游戏中的表现 |
| RHAE | 相对人类动作效率，核心评分方法 |
| Swarm | 跨多游戏并行编排智能体的系统 |
| OperationMode | OFFLINE / ONLINE / COMPETITION 三种运行模式 |

## 项目文件结构

```
taa3-try-arg-agi-3/
├── CLAUDE.md              ← 你正在这里（总入口）
├── pixi.toml              ← Python 环境配置
├── play.py                ← 最简游戏脚本
├── docs/
│   ├── guide.md           ← 快速上手
│   ├── game-mechanics.md  ← 游戏机制
│   ├── scoring-system.md  ← 评分系统
│   ├── actions-reference.md ← 动作参考
│   ├── agent-development.md ← 智能体开发
│   ├── rest-api.md        ← REST API
│   └── human-vs-ai.md     ← 人机对比
├── plgd/
│   └── arcprize-docs/     ← 官方文档源文件（MDX 格式）
└── .env                   ← API Key（禁止读取）
```

## 开发约定

- 新增脚本放在项目根目录或 `scripts/` 目录
- 实验记录和结果放在 `experiments/` 目录（按日期/实验名组织）
- 所有 Python 程序使用 `pixi run python` 执行
- 不要修改 `plgd/arcprize-docs/` 下的官方文档
