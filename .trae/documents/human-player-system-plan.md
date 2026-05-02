# 游戏控制映射与关卡管理系统开发计划（v3 — rich + msvcrt）

## 核心设计

| 层次 | 方案 | 说明 |
|------|------|------|
| 游戏内渲染 | `render_mode="terminal"` | 复用内置，不动 |
| 游戏外 UI | `rich` 库 | 菜单、进度、记分板 |
| 游戏内输入 | `msvcrt.getwch()` | Windows 内置，单键读取 |
| 菜单输入 | `rich.prompt.Prompt` | 标准终端输入 |
| 数据存储 | JSON / JSONL | 进度、成绩、录像 |

## 模块结构

```
human_player/
├── __init__.py
├── __main__.py            # 入口 + 主循环
├── config.py              # 键位映射、路径常量
├── game_manager.py        # Arcade/Environment 封装
├── level_manager.py       # 关卡进度（JSON）
├── stats_manager.py       # 成绩统计（JSON）
├── recording.py           # 录像（JSONL）
└── menu.py                # rich 终端菜单

data/
├── progress.json
├── records/
└── recordings/
```

## 依赖

- `rich >= 13.0` — 终端美化
- `msvcrt` — Windows 内置，无需安装
