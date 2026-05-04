---
alwaysApply: true
scene: environment_configuration
---

# 🛑 Global Config Rule — 禁止修改全局级配置

## ⚠️ STOP — Before ANY Global Config Change

**About to run `pixi config set/unset --global`, `git config --global`, or any `--global` flag? → STOP NOW.**
Use project-level config instead. NO exceptions.

### Self-Check

1. Am I modifying a global/user-level config? → **STOP, use project-level**
2. Am I running `pixi config --global`? → **STOP, use project-level**
3. Am I running `git config --global`? → **STOP, use project-level**
4. Am I editing files outside the project directory (e.g. `~/pixi/config.toml`)? → **STOP, use project-level**

If ANY match → DO NOT modify global config. Use project-level alternative below.

## Core Rule

**NEVER modify any global/user-level configuration.** Use project-level config instead.

This includes but is not limited to:
- `pixi config --global` → use `pixi config` (project-level) or `.pixi/config.toml`
- `git config --global` → use `git config` (repo-level) or `.git/config`
- Editing `~/.*` config files → use project-local equivalents

## Why

Global config affects ALL projects on the machine, not just the current one.
A change that "fixes" one project may break others.
The user's global config is their business, not ours.

## How — Project-Level Alternatives

### pixi mirrors (conda-forge 镜像)

Instead of:
```bash
# ❌ NEVER DO THIS
pixi config set --global mirrors '{"https://conda.anaconda.org/conda-forge": [...]}'
```

Do:
```bash
# ✅ Project-level only
pixi config set mirrors '{"https://conda.anaconda.org/conda-forge": [...]}'
```

This creates `.pixi/config.toml` in the project directory, affecting only this project.

### git settings

Instead of:
```bash
# ❌ NEVER DO THIS
git config --global user.name "..."
```

Do:
```bash
# ✅ Repo-level only
git config user.name "..."
```

## Incident Log

- 2026-05-05: 误执行 `pixi config unset mirrors --global`，清空了用户的全局 ustc 镜像配置。
  起因是跨平台 `pixi install` 时 ustc 镜像返回 403，正确做法应该是用项目级配置绕过。
