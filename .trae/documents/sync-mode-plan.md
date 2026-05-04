# 计划书：游戏同步策略改进 — 保守模式 vs 自动模式

## 问题

当前 `needs_sync()` 只在本地游戏数为 0 时才返回 True，导致：

* 已有 6 个本地游戏但远程有 25 个时，下载按钮不显示

* 用户无法方便地获取新增游戏

* 没有配置项让用户选择自己的 API 连接策略

## 方案：两种同步模式

### 保守模式（conservative，默认）

* **首次运行**（本地无游戏）：自动触发一次同步，下载所有游戏

* **后续运行**：主菜单始终显示 `[D] Sync` 按钮，用户手动点击才同步

* API 连接次数最少，仅在用户主动请求时连接

### 自动模式（auto）

* **每次启动**：自动连接 API，对比远程游戏数，下载缺失的游戏，然后断开

* 始终保持与云端游戏数一致

* API 连接次数更多，但用户无需操心

## 实施步骤

### 第一步：在 config.py 中添加同步模式配置

在 `user_config.json` 中新增 `sync_mode` 字段，值为 `"conservative"` 或 `"auto"`。

添加函数：

* `get_sync_mode() -> str` — 读取配置，默认 `"conservative"`

* `set_sync_mode(mode: str) -> None` — 写入配置

### 第二步：在 game\_sync.py 中修改 needs\_sync 逻辑

修改 `needs_sync()` 函数：

* 保守模式：`get_local_game_count() == 0`（仅首次无游戏时自动触发）

* 自动模式：始终返回 True（每次启动都同步）

新增 `should_show_sync_button()` 函数：

* 保守模式：始终返回 True（让用户随时手动触发）

* 自动模式：返回 False（自动同步，无需手动按钮）

### 第三步：修改 GameManager 中的同步检测

修改 `GameManager.__init__()`：

* 使用新的 `needs_sync()` 逻辑

* `_needs_sync` 仅控制启动时是否自动进入同步流程

* `_show_sync_button` 控制主菜单是否显示同步按钮

### 第四步：修改 __main__.py 中的同步流程

* 启动时：如果 `needs_sync()` 为 True，自动进入 SYNCING 状态

* 主菜单：如果 `should_show_sync_button()` 为 True，始终显示 `[D] Sync` 按钮

* 同步完成后：销毁 NORMAL 模式 Arcade 实例，重建 OFFLINE 模式 GameManager

### 第五步：修改 menu.py 中的按钮显示

* 保守模式：始终显示 `[D] Sync` 按钮（让用户手动触发）

* 自动模式：不显示按钮（启动时已自动同步）

* 按钮标签从 "Download" 改为 "Sync"（更准确）

### 第六步：在 Settings 页面添加同步模式切换

在 `menu.py` 的 `draw_settings()` 中添加同步模式选择：

* Conservative: "Manual sync only"

* Auto: "Sync on every startup"

### 第七步：提交代码

## 文件变更摘要

| 文件                             | 变更                                               |
| ------------------------------ | ------------------------------------------------ |
| `human_player/config.py`       | 新增 `get_sync_mode()` / `set_sync_mode()`         |
| `human_player/game_sync.py`    | 修改 `needs_sync()`，新增 `should_show_sync_button()` |
| `human_player/game_manager.py` | 修改同步检测逻辑                                         |
| `human_player/__main__.py`     | 修改启动同步流程 + 手动同步按钮                                |
| `human_player/menu.py`         | 修改按钮显示 + Settings 添加同步模式选项                       |

