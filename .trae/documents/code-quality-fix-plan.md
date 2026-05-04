# 开源准备计划

## 背景

基于开源可行性分析，项目已确认"可以开源"且"有开源价值"。本计划逐项解决开源前的遗留问题。

***

## 第 1 项：plgd/ 目录 — 无需操作

`plgd/` 已在 `.gitignore` 第 227 行明确排除，不在版本管理中。之前分析中提出的"确认再分发权限"问题不存在——该目录不会被推送到公开仓库。

**操作**：无需任何操作。

***

## 第 2 项：第三方许可证声明

### 什么是第三方许可证声明？

开源项目使用 MIT 许可证，只管你自己的代码。但你依赖的库各有各的许可证（Apache-2.0、LGPL、BSD 等），这些许可证要求你在分发时**保留原始版权声明和许可证文本**。做法很简单：在项目根目录放一个文件（通常叫 `NOTICE`、`THIRD_PARTY_LICENSES` 或 `LICENSES`），把每个依赖库的许可证原文或摘要列出来。

### 需要声明的依赖

| 依赖                  | 许可证           | 声明要求                  |
| ------------------- | ------------- | --------------------- |
| arc-agi / arcengine | Apache-2.0    | 必须保留 NOTICE 和 LICENSE |
| pygame-ce           | LGPL-2.1-only | 必须保留版权声明，允许用户替换库      |
| rich                | MIT           | 必须保留版权声明              |
| numpy               | BSD-3-Clause  | 必须保留版权声明              |
| python-dotenv       | BSD-3-Clause  | 必须保留版权声明              |

### 操作步骤

1. 创建 `THIRD_PARTY_LICENSES` 文件
2. 列出每个依赖的：名称、版本、许可证类型、版权声明、许可证全文（或链接）

***

## 第 3 项：项目重命名

README 第 37 行的 git clone URL 中使用的名字为 **`arc-agi-3-human-player`**，这个名称清晰直观，按此重命名。

### 操作步骤

1. 将 `pixi.toml` 中的 `name = "taa3-try-arg-agi-3"` 改为 `name = "arc-agi-3-human-player"`
2. 确认 README 中已有的名称引用一致
3. 确认 `pyproject.toml` 或其他配置文件中无旧名称残留

***

## 第 4 项：.trae/ 目录 — 保留在 Git 中，export-ignore 已足够

`.trae/` 目录已在 `.gitattributes` 中设置 `export-ignore`，这意味着：

* `git archive` 生成的压缩包不会包含 `.trae/`

* GitHub 的 "Download ZIP" 不会包含 `.trae/`

* 但 Git 历史和 clone 中仍可见

用户确认这些是零碎的需求决策文档，公开没问题。`export-ignore` 确保打包发布时不带出去，这已经足够。

**操作**：无需任何操作。

***

## 第 5 项：Python 版本放宽到 3.12

### 现状分析

* `arc-agi` 要求 `Python >=3.12`（已通过 `importlib.metadata` 确认）

* `arcengine` 要求 `Python >=3.12`

* `pygame-ce` 要求 `Python >=3.10`

* `rich` 要求 `Python >=3.8`

* 项目代码实际最低兼容 Python 3.10（使用了 `X | Y` 联合类型和内置泛型）

**结论**：Python 版本下限由 `arc-agi` 决定，最低可放宽到 `>=3.12`。

### 如何测试放宽后不会带来问题

1. **修改** **`pixi.toml`**：将 `python = ">=3.14.4,<3.15"` 改为 `python = ">=3.12,<3.15"`
2. **重新解析环境**：`pixi install` 会根据新约束重新解析依赖
3. **运行冒烟测试**：`pixi run game` 启动后进入主菜单、选择游戏、玩几步、退出
4. **自动化验证**：编写一个最小测试脚本，验证所有 import 正常、核心类可实例化
5. **注意事项**：

   * `pixi install` 在解析时可能选择 Python 3.12.x 而非 3.14.x，需要确认所有依赖在此版本下有可用的 wheel

   * 如果 arc-agi 的某些功能依赖 3.14 特性（不太可能，因为其 Requires-Python 是 >=3.12），则需要在 3.12 环境下实际运行验证

### 操作步骤

1. 修改 `pixi.toml` 中 Python 版本约束为 `">=3.12,<3.15"`
2. 运行 `pixi install` 重新解析
3. 运行 `pixi run game` 冒烟测试
4. 编写并运行 import 验证脚本

***

## 第 6 项：跨平台支持

### 现状分析

代码层面的平台依赖极少：

| 问题                                     | 严重程度  | 说明                   |
| -------------------------------------- | ----- | -------------------- |
| `pixi.toml` 的 `platforms = ["win-64"]` | **高** | 直接阻止其他平台安装           |
| Consolas 字体硬编码（8 处）                    | **中** | 其他平台会静默回退默认字体，排版可能错位 |
| 无其他 Windows API 调用                     | -     | 代码本身是跨平台的            |

### 策略：扩展平台 + 字体回退

**不移除任何功能**，只做两件事：

1. **扩展 pixi.toml 平台列表**：添加 `linux-64` 和 `osx-64`、`osx-arm64`
2. **字体回退机制**：将 Consolas 硬编码改为带回退的字体选择器

字体回退方案：

```python
# 之前
pygame.font.SysFont("consolas", 22, bold=True)

# 之后
pygame.font.SysFont("consolas,monospace", 22, bold=True)
```

Pygame 的 `SysFont` 支持逗号分隔的字体列表，会按顺序查找第一个可用的。`monospace` 是通用的等宽字体族名，在所有平台上都有对应的等宽字体。

### 操作步骤

1. 修改 `pixi.toml`：`platforms = ["win-64", "linux-64", "osx-64", "osx-arm64"]`
2. 修改 `renderer.py` 和 `menu.py` 中的 8 处字体声明，添加回退字体
3. 在 Windows 上运行冒烟测试确认无回归
4. 在 README 中标注"Linux/macOS 支持为实验性，欢迎反馈"

***

## 第 7 项：代码质量改进（测试、文档字符串、错误处理）

### 7.1 测试

创建 `tests/` 目录，为数据层模块编写单元测试。

| 测试文件                         | 覆盖模块                   | 测试内容               |
| ---------------------------- | ---------------------- | ------------------ |
| `test_level_manager.py`      | level\_manager.py      | 进度读写、关卡状态更新、边界条件   |
| `test_stats_manager.py`      | stats\_manager.py      | 成绩记录读写、最佳成绩查询      |
| `test_player_manager.py`     | player\_manager.py     | 玩家创建/切换/删除、路径遍历防护  |
| `test_recording.py`          | recording.py           | JSONL 录像写入/读取、会话管理 |
| `test_official_recording.py` | official\_recording.py | 官方格式录像生成、索引文件、序列化  |
| `test_game_sync.py`          | game\_sync.py          | 同步逻辑、本地游戏检测        |
| `test_mode.py`               | mode.py                | 模式枚举、运行模式映射        |
| `test_config.py`             | config.py              | 配置加载、键位映射          |

测试框架使用 `pytest`（通过 `pixi add --pypi pytest` 添加）。

### 7.2 文档字符串

为所有公开类和公开方法添加 docstring，遵循 Google 风格：

```python
class LevelManager:
    """Manage level progress persistence for each game.

    Progress is stored as a JSON file mapping game IDs to level completion data.
    """

    def update_level_status(self, game_id: str, level_index: int, steps: int, time_ms: int):
        """Update the completion status for a specific level.

        Args:
            game_id: The 4-character game identifier.
            level_index: Zero-based level index.
            steps: Number of actions taken to complete the level.
            time_ms: Elapsed time in milliseconds.
        """
```

覆盖范围（按代码行数从多到少）：

| 文件                     | 行数  | 需添加 docstring 的公开 API               |
| ---------------------- | --- | ----------------------------------- |
| menu.py                | 894 | MenuRenderer 类 + 所有公开方法             |
| __main__.py            | 813 | main() + 辅助函数                       |
| renderer.py            | 276 | Renderer 类 + 所有公开方法                 |
| game\_manager.py       | 235 | GameManager 类 + 所有公开方法              |
| official\_recording.py | 225 | OfficialRecordingManager 类 + 所有公开方法 |
| config.py              | 144 | 所有公开函数                              |
| level\_manager.py      | 122 | LevelManager 类 + 所有公开方法             |
| player\_manager.py     | 106 | PlayerManager 类 + 所有公开方法            |
| game\_sync.py          | 90  | sync\_games() + 辅助函数                |
| recording.py           | 80  | RecordingManager 类 + 所有公开方法         |
| stats\_manager.py      | 69  | StatsManager 类 + 所有公开方法             |
| mode.py                | 57  | 所有公开函数                              |
| agent\_base.py         | 13  | AgentBase 类 + 抽象方法                  |

### 7.3 错误处理

关键修复点：

| 位置                       | 问题                                     | 修复方案                                          |
| ------------------------ | -------------------------------------- | --------------------------------------------- |
| game\_manager.py:240-269 | `jump_to_level()` 访问私有属性无 try-except   | 添加 try-except，捕获 AttributeError 并返回 False     |
| level\_manager.py        | `_load_progress()` 中 `json.load` 可能抛异常 | 添加 try-except (json.JSONDecodeError, OSError) |
| stats\_manager.py        | `_load_records()` 无异常处理                | 添加 try-except                                 |
| recording.py:27          | `open()` 无异常保护                         | 添加 try-except (OSError)                       |
| official\_recording.py   | 文件 I/O 操作需异常保护                         | 添加 try-except                                 |

***

## 执行顺序

按依赖关系和风险排序：

1. **项目重命名**（第 3 项）— 最简单，先做
2. **Python 版本放宽**（第 5 项）— 环境基础，尽早确认
3. **跨平台支持**（第 6 项）— 依赖第 5 项的 pixi.toml 修改
4. **第三方许可证声明**（第 2 项）— 独立任务
5. **错误处理**（第 7.3 项）— 代码改进
6. **文档字符串**（第 7.2 项）— 代码改进
7. **测试**（第 7.1 项）— 依赖 docstring 和错误处理完成后更稳定

每完成一项，立即 commit。
