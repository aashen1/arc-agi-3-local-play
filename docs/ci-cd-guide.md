# CI/CD 指南：从本地 pre-commit 到 GitHub Actions

## 你已经有的 vs 即将有的

| 层级 | 工具 | 作用 | 触发时机 |
|------|------|------|---------|
| 本地 | ruff | 代码风格检查 + 自动格式化 | 你手动运行或 pre-commit 自动触发 |
| 本地 | pre-commit | git commit 前自动运行 ruff | `git commit` |
| 远程 | GitHub Actions | 跑测试 + 跑 ruff | `git push` 或 PR |

**核心思路**：本地挡住低级错误（省时间），远程兜底（防漏网之鱼）。

---

## 第一层：ruff — 代码风格检查 + 格式化

### ruff 是什么？

ruff 是一个用 Rust 写的 Python linter + formatter，速度极快（比 flake8 快 10-100 倍）。它替代了：
- **flake8**（代码风格检查）
- **isort**（import 排序）
- **black**（代码格式化）
- **pyupgrade**（语法现代化）

一个工具干四个工具的活。

### 安装

```bash
pixi add --pypi ruff
```

### 基本用法

```bash
# 检查问题（只看不改）
pixi run ruff check .

# 自动修复能修的问题
pixi run ruff check --fix .

# 格式化代码（类似 black）
pixi run ruff format .

# 检查格式是否正确（只看不改）
pixi run ruff format --check .
```

### 配置

在 `pyproject.toml` 中添加：

```toml
[tool.ruff]
target-version = "py312"
line-length = 99

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes (未使用的 import、变量等)
    "I",    # isort (import 排序)
    "UP",   # pyupgrade (用新语法替换旧语法)
    "B",    # flake8-bugbear (常见 bug 模式)
    "SIM",  # flake8-simplify (简化写法)
]
ignore = [
    "E501",  # 行长度由 formatter 管理，不需要 lint 管
]

[tool.ruff.lint.isort]
known-first-party = ["human_player"]

[tool.ruff.format]
quote-style = "double"
```

### 在 pixi 中注册 task

在 `pixi.toml` 的 `[tasks]` 中添加：

```toml
lint = "ruff check ."
format = "ruff format ."
```

之后就可以：

```bash
pixi run lint      # 检查
pixi run format    # 格式化
```

---

## 第二层：pre-commit — git commit 前自动检查

### pre-commit 是什么？

pre-commit 是一个 Git hook 管理器。它在 `git commit` 执行前自动运行你配置的检查。如果检查失败，commit 会被阻止，逼你先修好代码再提交。

### 为什么需要它？

没有 pre-commit：你写完代码 → commit → push → CI 报错 → 再修 → 再 push（慢）
有 pre-commit：你写完代码 → commit → ruff 自动拦截 → 本地修 → 再 commit（快）

**本地 1 秒发现的问题，不用等 CI 3 分钟才发现。**

### 安装

```bash
pixi add --pypi pre-commit
```

### 配置

创建 `.pre-commit-config.yaml`：

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.11.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

这个配置做了两件事：
1. `ruff --fix`：自动修复 lint 问题（未使用的 import、坏习惯写法等）
2. `ruff-format`：自动格式化代码

### 安装 hook

```bash
pixi run pre-commit install
```

这一步会在 `.git/hooks/pre-commit` 中创建一个脚本。之后每次 `git commit` 都会自动运行 ruff。

### 日常使用

```bash
# 正常 commit — pre-commit 会自动运行
git commit -m "feat: add new feature"

# 如果 ruff 发现问题，commit 会被阻止
# ruff --fix 会自动修复能修的问题
# 修不了的会报错，你需要手动修

# 跳过 pre-commit（紧急情况，不推荐）
git commit --no-verify -m "hotfix: critical bug"
```

### 首次全量检查

```bash
# 对所有文件跑一遍 pre-commit（首次安装后建议做）
pixi run pre-commit run --all-files
```

---

## 第三层：GitHub Actions — 远程自动化

### GitHub Actions 是什么？

GitHub Actions 是 GitHub 提供的 CI/CD 服务。你在仓库里放一个 YAML 配置文件，GitHub 就会在指定事件（push、PR）触发时，自动开一台虚拟机，按你的配置执行命令。

**关键概念**：

| 术语 | 含义 |
|------|------|
| Workflow | 一个自动化流程，定义在 `.github/workflows/*.yml` 中 |
| Event | 触发 workflow 的事件（push、PR、定时任务等） |
| Job | workflow 中的一组步骤，可以并行或串行 |
| Step | job 中的一个具体操作（安装依赖、运行命令等） |
| Runner | 执行 job 的虚拟机（ubuntu/windows/macos） |

### 我们已有的 workflow

文件：`.github/workflows/test.yml`

```yaml
name: Tests

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
      fail-fast: false

    steps:
      - uses: actions/checkout@v4       # 1. 拉代码
      - uses: prefix-dev/setup-pixi@v0.8.1  # 2. 安装 pixi
      - run: pixi install               # 3. 安装项目依赖
      - run: pixi run pytest tests/ -v  # 4. 跑测试
```

**逐行解读**：

```yaml
on:
  push:
    branches: [main, dev]      # 推送到 main 或 dev 分支时触发
  pull_request:
    branches: [main, dev]      # 向 main 或 dev 提 PR 时触发
```

```yaml
runs-on: ${{ matrix.os }}      # 用矩阵策略，三个系统各跑一遍
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
  fail-fast: false             # 一个系统失败不影响其他系统继续跑
```

```yaml
- uses: actions/checkout@v4           # GitHub 官方 action：把你的代码 clone 到 runner 上
- uses: prefix-dev/setup-pixi@v0.8.1  # 第三方 action：安装 pixi 包管理器
- run: pixi install                   # 执行 shell 命令：安装项目依赖
- run: pixi run pytest tests/ -v      # 执行 shell 命令：跑测试
```

### 增强版：加上 ruff 检查

建议在测试前加一个 lint job，让 ruff 也在远程跑一遍：

```yaml
name: CI

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: prefix-dev/setup-pixi@v0.8.1
      - run: pixi install
      - run: pixi run ruff check .
      - run: pixi run ruff format --check .

  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
      - uses: prefix-dev/setup-pixi@v0.8.1
      - run: pixi install
      - run: pixi run pytest tests/ -v
```

**lint 和 test 是两个独立的 job**，会并行运行。lint 几秒就跑完，test 需要几分钟。这样你可以更快看到 lint 结果。

---

## 三层协作流程

```
你写代码
  │
  ├─→ git add + git commit
  │     │
  │     └─→ pre-commit 自动运行 ruff
  │           │
  │           ├─ 通过 → commit 成功
  │           └─ 失败 → commit 被阻止，你修代码再 commit
  │
  └─→ git push
        │
        └─→ GitHub Actions 自动运行
              │
              ├─ lint job: ruff check + format check
              └─ test job: pytest (三平台)
                    │
                    ├─ 全部通过 → PR 可以合并 ✅
                    └─ 有失败 → PR 被标记为失败，需要修 ❌
```

### 为什么三层都要？

| 场景 | 只有本地 | 只有远程 | 三层都有 |
|------|---------|---------|---------|
| 忘了跑 ruff 就 commit | ❌ 错误入库 | ⚠️ push 后才发现 | ✅ pre-commit 拦住 |
| pre-commit 被 --no-verify 跳过 | ❌ 错误入库 | ⚠️ push 后才发现 | ✅ CI 兜底 |
| 代码在 Windows 能跑但 Linux 不行 | ❌ 发现不了 | ✅ CI 多平台发现 | ✅ CI 多平台发现 |
| 别人贡献代码没装 pre-commit | ❌ 拦不住 | ✅ CI 拦住 | ✅ CI 拦住 |

**本地是第一道防线（快），远程是最后一道防线（全）。**

---

## 常见问题

### Q: pre-commit 太慢怎么办？

ruff 本身极快（毫秒级），但 pre-commit 首次运行需要创建虚拟环境。后续运行会缓存，通常 < 2 秒。

### Q: CI 跑一次要多久？

取决于依赖安装时间。pixi install 通常 30-60 秒，pytest 2 秒，总计约 1-2 分钟。三平台并行，所以总等待时间取决于最慢的那个。

### Q: CI 免费吗？

GitHub Actions 对公开仓库免费，无限制。对私有仓库，每月 2000 分钟免费额度（三平台并行 = 每次消耗 3 分钟额度）。

### Q: 我能在本地模拟 CI 吗？

可以。CI 做的事情本质上就是：

```bash
pixi install
pixi run ruff check .
pixi run ruff format --check .
pixi run pytest tests/ -v
```

你在本地跑这三条命令，效果和 CI 一样。CI 只是自动化了这个过程。

### Q: `--no-verify` 什么时候可以用？

理论上永远不应该用。但现实中，紧急热修复、WIP commit 等场景偶尔需要。**规则是：用了就要在 push 前手动补上检查。**

---

## 实操清单

按以下顺序操作，把三层自动化全部搭好：

1. `pixi add --pypi ruff` — 安装 ruff
2. 在 `pyproject.toml` 中添加 `[tool.ruff]` 配置
3. 在 `pixi.toml` 中添加 `lint` 和 `format` task
4. `pixi run ruff check .` — 首次检查，看有哪些问题
5. `pixi run ruff check --fix .` — 自动修复
6. `pixi run ruff format .` — 格式化
7. `pixi add --pypi pre-commit` — 安装 pre-commit
8. 创建 `.pre-commit-config.yaml`
9. `pixi run pre-commit install` — 安装 git hook
10. `pixi run pre-commit run --all-files` — 首次全量检查
11. 更新 `.github/workflows/test.yml` — 加上 lint job
12. commit + push — 验证 CI 跑通
