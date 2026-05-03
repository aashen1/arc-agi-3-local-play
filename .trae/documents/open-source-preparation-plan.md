# 开源准备计划

## 项目现状总结

- **项目名**: `taa3-try-arg-agi-3`（内部开发名，开源时需改名）
- **当前分支**: `migrate-to-pygame`（所有 Pygame 人类玩家控制台代码在此分支）
- **main 分支**: 仅有初始提交
- **上游仓库**: `arcprize/arc-agi`（MIT 许可证）
- **核心功能**: 用 Pygame-CE 为 ARC-AGI-3 评测工具包包装了一个人类玩家控制台，支持键盘/鼠标操作、关卡进度保存、多玩家、录像等
- **未提交变更**: `human_player/__main__.py` 和 `human_player/renderer.py` 有未暂存修改

---

## 开源前需要完成的事项

### 1. 清理内部/开发专用文件（排除出仓库）

以下文件/目录包含开发工具配置或内部文档，开源时应排除或清理：

| 文件/目录 | 处理方式 | 原因 |
|---|---|---|
| `.trae/` | 加入 `.gitignore` | Trae IDE 的内部配置，不属于项目本身 |
| `CLAUDE.md` | 加入 `.gitignore` | Claude/AI 助手的内部指令文件，不适合开源项目 |
| `plgd/` | 已在 `.gitignore` | 官方文档源文件（MDX），不应随项目发布 |
| `.trashbin/` | 已在 `.gitignore` | 删除文件暂存，不需要 |
| `docs/frame-sync-fix.md` | 评估是否保留 | 内部技术笔记，开源用户可能不关心 |
| `play.py` | 评估是否保留 | 早期测试脚本，功能已被 `human_player` 模块取代 |

### 2. 添加开源必备文件

| 文件 | 说明 |
|---|---|
| `README.md` | 项目主文档，包含项目介绍、截图/GIF、安装、使用、配置等 |
| `LICENSE` | MIT 许可证（与上游 `arc-agi` 保持一致） |
| `CONTRIBUTING.md` | 贡献指南（可选，建议有） |

### 3. README.md 内容规划

README 应包含以下部分：

1. **项目标题 + 一句话描述** — "ARC-AGI-3 Human Player Console — 用 Pygame 玩转 ARC-AGI-3 评测游戏"
2. **项目简介** — 说明这是什么、为什么做（让人类也能像玩游戏一样体验 ARC-AGI-3 的谜题，建立直觉，与 AI 表现对比）
3. **功能特性** — 键盘/鼠标操控、关卡进度保存、多玩家、录像回放、网格/列表视图、可调整窗口等
4. **截图/GIF** — 游戏主菜单、游戏画面、关卡选择等（需要你手动截图）
5. **快速开始** — 安装 pixi → `pixi install` → 配置 API Key → `pixi run game`
6. **操作说明** — 键位映射（WASD/箭头两套方案）、鼠标操作
7. **项目结构** — 简要的目录说明
8. **配置** — API Key、环境变量说明
9. **与上游的关系** — 说明本项目是 `arc-agi` 的非官方人类玩家前端，基于其 API 构建
10. **许可证** — MIT
11. **致谢** — ARC Prize 基金会、arc-agi 工具包等

### 4. .gitignore 补充

需要新增以下条目：

```gitignore
# IDE / AI assistant configs
.trae/
CLAUDE.md

# Development artifacts
play.py
```

### 5. 代码审查与调整建议

#### 5.1 项目名称
- `taa3-try-arg-agi-3` 是内部开发名，开源建议改为更直观的名字，如：
  - `arc-agi-human-player` — 直接描述功能
  - `arc-agi-3-player` — 简洁
  - `arc-agi-playground` — 更有玩味
- `pixi.toml` 中的 `name` 字段也需同步修改

#### 5.2 pixi.toml 平台支持
- 当前仅 `platforms = ["win-64"]`，开源应考虑跨平台：
  - 改为 `platforms = ["win-64", "linux-64", "osx-64", "osx-arm64"]`
  - Pygame-CE 和 arc-agi 都是跨平台的，应该没问题

#### 5.3 Python 版本要求
- 当前要求 `python = ">=3.14.4,<3.15"`，这非常激进（Python 3.14 是最新版本）
- 开源项目应考虑兼容性，建议放宽到 `python = ">=3.11"` 或至少 `">=3.12"`
- 需要检查代码中是否使用了 3.14 专属特性（如 `X | None` 类型语法在 3.10+ 就支持了）

#### 5.4 代码中的硬编码和魔法值
- `game_manager.py` 的 `jump_to_level()` 方法直接访问了 `env._game` 内部属性（`_levels`, `set_level`, `_state`, `_score`, `_action_count`），这是对 arc-agi 内部实现的依赖，上游 API 变动可能导致崩溃
- 建议添加 try-except 保护，或在上游提 issue 请求公开关卡跳转 API

#### 5.5 未提交的修改
- `human_player/__main__.py` 和 `human_player/renderer.py` 有未暂存修改，需要先提交

### 6. 分支整理

当前分支结构：
- `main` — 仅有初始提交
- `dev` — 存在
- `migrate-to-pygame` — 所有实际工作（当前分支）

开源前的分支整理方案：
1. 将 `migrate-to-pygame` 合并到 `main`（或 rebase 到 main 上）
2. 开源后 `main` 就是主分支，删除临时分支
3. 或者直接将 `migrate-to-pygame` 重命名为 `main`

### 7. 关于合并回上游（arcprize/arc-agi）

**不建议直接合并回上游**，原因：
- 上游 `arc-agi` 是一个评测工具包（Python API），定位是给 AI agent 用的
- 本项目是一个人类玩家 GUI 前端，定位完全不同
- 两者依赖不同（上游不需要 Pygame-CE）
- 合并进去会让上游变得臃肿

**推荐做法**：
- 作为独立仓库开源，在 README 中说明与上游的关系
- 可以在上游仓库提一个 issue 或 PR，在他们的 README 中添加"社区项目"链接
- 也可以向上游提 issue 建议：在 `arc-agi` 的文档中添加"第三方工具/前端"列表

### 8. 开源发布清单

按顺序执行：

1. ✅ 提交当前未暂存的修改
2. ✅ 更新 `.gitignore`（添加 `.trae/`, `CLAUDE.md`, `play.py`）
3. ✅ 从 Git 历史中移除已被忽略但已跟踪的文件（`git rm --cached`）
4. ✅ 修改 `pixi.toml`（项目名、平台支持、Python 版本范围）
5. ✅ 添加 `LICENSE` 文件（MIT）
6. ✅ 编写 `README.md`
7. ✅ 整理分支（将当前工作合并到 main）
8. ✅ 在 GitHub 创建新仓库并推送
9. ✅ 在上游 `arcprize/arc-agi` 提 issue 通知社区
10. 📸 截图/GIF 需要你手动添加到 README

---

## 实施步骤（按优先级排序）

### Step 1: 提交未暂存修改
- 提交 `__main__.py` 和 `renderer.py` 的修改

### Step 2: 更新 .gitignore
- 添加 `.trae/`, `CLAUDE.md`, `play.py`
- 从 Git 跟踪中移除这些文件（`git rm --cached`）

### Step 3: 修改 pixi.toml
- 修改项目名（待确认）
- 扩展平台支持
- 放宽 Python 版本要求

### Step 4: 添加 LICENSE
- 创建 MIT LICENSE 文件

### Step 5: 编写 README.md
- 按上述规划编写完整的 README

### Step 6: 整理分支
- 将 `migrate-to-pygame` 合并到 `main`

### Step 7: 代码保护性修改（可选）
- 为 `jump_to_level()` 中的内部 API 访问添加 try-except

### Step 8: 创建 GitHub 仓库并推送
