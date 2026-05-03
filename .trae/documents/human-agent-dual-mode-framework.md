# 人类/Agent 双模式框架设计计划

## 目标

1. **现阶段**：所有数据默认为人类模式，强制 OFFLINE，不加载 API Key
2. **未来扩展**：只需"拨一个开关"即可切换为 Agent 模式，自动启用 ONLINE/COMPETITION 模式、上传数据、标记来源
3. **Agent 接入方式**：对齐官方 ARC-AGI-3 Agents 仓库的架构模式（Agent 基类 + choose_action + is_done）

---

## 设计思路

### 核心概念：PlayerMode

引入 `PlayerMode` 枚举，作为整个系统的"开关"：

```python
class PlayerMode(enum.Enum):
    HUMAN = "human"
    AGENT = "agent"
```

- `HUMAN`（默认）：强制 OFFLINE 模式，不加载 API Key，所有录像/记分卡标记为 `human`
- `AGENT`：启用 ONLINE 模式（需要 API Key），数据上传排行榜，录像标记为 `agent` 类型

### 切换方式

通过 `user_config.json` 中的 `player_mode` 字段控制，默认 `"human"`。未来可在 UI 菜单或命令行参数中切换。

---

## 修改清单

### 1. 新建 `human_player/mode.py` — 模式定义与配置

- 定义 `PlayerMode` 枚举（HUMAN / AGENT）
- 定义 `AgentType` 枚举（预留，对齐官方模板：RANDOM / LLM / FAST_LLM / REASONING_LLM / GUIDED_LLM / CUSTOM）
- 提供 `get_player_mode()` / `set_player_mode()` 读写 `user_config.json`
- 提供 `get_agent_type()` / `set_agent_type()` 读写 `user_config.json`
- 提供 `get_operation_mode()` — 根据 PlayerMode 返回对应的 `OperationMode`：
  - HUMAN → `OperationMode.OFFLINE`
  - AGENT → `OperationMode.ONLINE`
- 提供 `get_player_tag()` — 返回用于 scorecard tags 的标识字符串：
  - HUMAN → `"human"`
  - AGENT → `"agent:{agent_type}"`

### 2. 新建 `human_player/agent_base.py` — Agent 基类（预留框架）

对齐官方 ARC-AGI-3 Agents 仓库的 Agent 接口：

```python
class AgentBase(ABC):
    @abstractmethod
    def is_done(self, frames, latest_frame) -> bool: ...

    @abstractmethod
    def choose_action(self, frames, latest_frame) -> GameAction: ...
```

- 预留 `agent_type` 属性，用于标记 Agent 类型
- 预留 `reasoning` 属性，用于记录推理过程（对齐官方 `action.reasoning` 字段）
- 此文件现阶段不会被调用，但为未来接入 Agent 提供接口约定

### 3. 修改 `human_player/game_manager.py` — 核心改造

**当前问题**：
- `Arcade()` 无参数，默认 NORMAL 模式，会自动创建 scorecard 上传
- `load_dotenv()` 无条件加载，即使 HUMAN 模式也会读取 API Key

**改造**：
- 导入 `mode.py` 中的 `get_operation_mode`、`get_player_mode`
- `__init__` 中：
  - 根据 `get_operation_mode()` 决定 `Arcade` 的 `operation_mode` 参数
  - HUMAN 模式下**跳过 `load_dotenv()`**，不加载 `.env` 中的 API Key
  - AGENT 模式下正常 `load_dotenv()`，让 API Key 生效
- `start_game` 中：
  - HUMAN 模式：`arc.make(game_id)` 无 scorecard_id
  - AGENT 模式：`arc.make(game_id, scorecard_id=...)` 并在 scorecard tags 中标记 agent 信息
- `execute_action` 中：
  - HUMAN 模式：`env.step(action)` 无 reasoning
  - AGENT 模式：`env.step(action, reasoning=...)` 附带推理信息

### 4. 修改 `human_player/recording.py` — 录像标记

- `record_step` 中的 `player_type` 字段目前硬编码为 `"human"`
- 改为从 `mode.py` 的 `get_player_mode()` 动态获取
- AGENT 模式下额外记录 `agent_type` 字段

### 5. 修改 `human_player/official_recording.py` — 官方录像标记

- `record_step` 中的 `action_input.reasoning` 目前硬编码为 `None`
- HUMAN 模式：保持 `None`
- AGENT 模式：填入 agent 的推理信息
- `start_session` 中在 index.json 的 session_entry 中增加 `player_mode` 和 `agent_type` 字段

### 6. 修改 `human_player/config.py` — 配置扩展

- 在 `user_config.json` 的读写函数中增加 `player_mode` 和 `agent_type` 字段的支持
- 默认值：`player_mode="human"`, `agent_type=None`

### 7. 修改 `play.py` — 同步改造

- 当前 `Arcade()` 无参数
- 改为使用 `mode.py` 中的 `get_operation_mode()` 来决定运行模式

---

## 文件变更总结

| 文件 | 操作 | 说明 |
|------|------|------|
| `human_player/mode.py` | **新建** | PlayerMode/AgentType 枚举 + 模式配置读写 + OperationMode 映射 |
| `human_player/agent_base.py` | **新建** | Agent 基类（预留，现阶段不调用） |
| `human_player/game_manager.py` | **修改** | 根据模式选择 OFFLINE/ONLINE，HUMAN 跳过 load_dotenv |
| `human_player/recording.py` | **修改** | player_type 从硬编码改为动态获取 |
| `human_player/official_recording.py` | **修改** | reasoning 字段按模式填充，session 增加 player_mode 标记 |
| `human_player/config.py` | **修改** | user_config 增加 player_mode/agent_type 支持 |
| `play.py` | **修改** | Arcade 初始化使用 mode 决定 operation_mode |

---

## 未来接入 Agent 的预期路径

当需要接入 Agent 时，只需：

1. 在 `human_player/agents/` 目录下创建具体 Agent 类（继承 `AgentBase`）
2. 设置 `player_mode = "agent"` + `agent_type = "llm"` 等
3. 在 `__main__.py` 的游戏循环中，当 `player_mode == AGENT` 时，将人类输入替换为 `agent.choose_action()` 的返回值
4. API Key 由 `.env` 加载（AGENT 模式下自动生效）

整个过程不需要修改核心框架代码，只需填充 Agent 实现和切换模式开关。
