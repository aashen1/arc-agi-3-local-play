# 计划书：人类玩家数据与 ARC-AGI-3 Agent 排行榜风险隔离

## 问题背景

本项目将 ARC-AGI-3 的 SDK（为 AI agent 评测设计）包装成 Pygame 人类玩家控制台。核心风险是：**人类玩家的游戏数据可能意外上传到 ARC 官方的 agent 排行榜，污染评测数据集。**

## 现状分析

### 当前代码风险点

| 位置 | 现状 | 风险等级 |
|------|------|----------|
| `mode.py:60` | Human 模式返回 `OperationMode.NORMAL` | **高** — NORMAL 模式会自动获取匿名 API Key、连接远程 API |
| `game_manager.py:66` | Human 模式 `make()` 不传 `scorecard_id` | **中** — SDK 在 `scorecard_id=None` 时自动创建默认 scorecard |
| `game_manager.py:21-22` | Agent 模式通过 `dotenv` 加载 `.env` | 低 — 仅 agent 模式触发 |
| `play.py:17` | 调用 `arc.get_scorecard()` | 低 — 仅测试脚本 |

### SDK 行为关键发现

1. **NORMAL 模式**：自动获取匿名 API Key → 连接 API 获取游戏列表 → `make()` 时从 API 下载游戏 → 创建**本地** scorecard（不上传）
2. **OFFLINE 模式**：无 API Key → 不连接 API → 仅显示本地已缓存的游戏 → 创建**本地** scorecard（不上传）
3. **ONLINE 模式**：需要 API Key → 创建**远程** scorecard → 结果进入排行榜
4. **游戏缓存机制**：NORMAL 模式下 `_download_game()` 会将 `metadata.json` 和游戏源码保存到 `environments_dir`；OFFLINE 模式的 `_find_local_game()` 能找到这些已下载的游戏

### 核心结论

- **OFFLINE 模式是安全的**：无任何网络请求，scorecard 纯本地内存，不会上传任何数据
- **NORMAL 模式有潜在风险**：虽然 scorecard 不上传，但会连接 API、获取匿名 Key，存在未来 SDK 变更或 bug 导致数据泄露的可能
- **ONLINE/COMPETITION 模式是高风险**：scorecard 会进入排行榜

## 实施方案

### 第一步：将人类模式改为 OFFLINE

**文件**：`human_player/mode.py`

将 `get_operation_mode()` 中人类模式的返回值从 `OperationMode.NORMAL` 改为 `OperationMode.OFFLINE`。

```python
def get_operation_mode() -> OperationMode:
    mode = get_player_mode()
    if mode == PlayerMode.HUMAN:
        return OperationMode.OFFLINE  # 改为 OFFLINE
    return OperationMode.ONLINE
```

**效果**：人类模式不再自动获取匿名 Key、不再连接远程 API。但代价是：未下载到本地的游戏将不可见。

### 第二步：添加游戏同步（下载）机制

**新建文件**：`human_player/game_sync.py`

创建一个独立的游戏同步模块，职责是：
- 检测本地已缓存的游戏数量
- 如果本地游戏不完整，提示用户进行一次性同步
- 临时创建 NORMAL 模式的 Arcade 实例，下载所有游戏到本地
- 下载完成后销毁该实例，回到 OFFLINE 模式

核心逻辑：

```python
def get_local_game_count() -> int:
    """统计本地已缓存的游戏数量"""
    # 扫描 environments_dir 下的 metadata.json 文件

def get_remote_game_count() -> int:
    """获取远程可用的游戏数量"""
    # 临时创建 NORMAL 模式 Arcade，调用 get_environments()

def sync_games(progress_callback=None) -> SyncResult:
    """同步所有游戏到本地"""
    # 1. 创建 NORMAL 模式 Arcade 实例
    # 2. 获取所有远程游戏列表
    # 3. 逐个调用 make() 触发下载
    # 4. 关闭所有环境，销毁 Arcade 实例
    # 5. 返回同步结果
```

**关键设计**：
- 同步时**不创建 scorecard**（显式传 `scorecard_id` 参数避免默认 scorecard）
- 同步完成后 Arcade 实例立即销毁，不保留任何状态
- 同步过程只下载游戏，不执行任何游戏动作

### 第三步：在 GameManager 中集成同步检测

**文件**：`human_player/game_manager.py`

在 `GameManager.__init__()` 中：
- 如果是 Human 模式且本地游戏为空，设置一个标志 `needs_sync = True`
- 在主菜单中显示同步提示

### 第四步：在主菜单中添加同步入口

**文件**：`human_player/__main__.py`、`human_player/menu.py`

- 在主菜单添加 "Download Games" 按钮（仅在需要同步时显示）
- 点击后调用 `game_sync.sync_games()`
- 显示下载进度
- 完成后刷新游戏列表

### 第五步：添加 Scorecard 安全防护

**文件**：`human_player/game_manager.py`

在 Human 模式下添加额外的防御性检查：
1. `start_game()` 中：确认 `_scorecard_id` 始终为 `None`
2. `close_game()` 中：确认不会调用 `close_scorecard()`
3. 在 `__init__()` 中：添加日志确认 OperationMode 为 OFFLINE
4. 添加一个 `assert` 或运行时检查：如果 Human 模式下 OperationMode 不是 OFFLINE，打印警告

### 第六步：同步完成后的 API Key 清理提示

**文件**：`human_player/__main__.py` 或 `human_player/menu.py`

- 在同步完成后，显示提示信息："游戏已全部下载到本地。如果您只是人类玩家，可以删除 .env 文件中的 ARC_API_KEY 以确保数据安全。"
- 在主菜单的设置页面添加 "清除 API Key" 选项（可选）

### 第七步：更新 play.py 测试脚本

**文件**：`play.py`

- 移除 `arc.get_scorecard()` 调用（或添加模式判断）
- 确保测试脚本也遵循安全规则

## 风险验证清单

实施完成后，需要验证以下场景：

- [ ] Human 模式 + OFFLINE + 无 API Key → 游戏正常运行，无网络请求
- [ ] Human 模式 + OFFLINE + 有 API Key（.env 中设置了） → 游戏正常运行，SDK 不使用 Key
- [ ] 首次运行（无本地游戏） → 提示同步，同步后游戏可用
- [ ] Agent 模式 → 行为不变，仍使用 ONLINE + scorecard
- [ ] 同步过程中 → 不创建 scorecard，不执行游戏动作
- [ ] 同步完成后 → Arcade 实例销毁，无残留状态

## 文件变更摘要

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `human_player/mode.py` | 修改 | Human 模式返回 OFFLINE |
| `human_player/game_sync.py` | 新建 | 游戏同步模块 |
| `human_player/game_manager.py` | 修改 | 集成同步检测 + scorecard 安全防护 |
| `human_player/__main__.py` | 修改 | 添加同步入口 + API Key 清理提示 |
| `human_player/menu.py` | 修改 | 添加同步按钮和提示 UI |
| `play.py` | 修改 | 移除不安全的 scorecard 调用 |
