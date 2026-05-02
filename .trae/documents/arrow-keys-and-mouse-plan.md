# 人类玩家系统增强计划：方向键修复 + 鼠标点击支持

## 问题诊断

### 问题 1：方向键不识别

**根因**：当前代码使用 `msvcrt.getwch()` 读取键盘，方向键处理逻辑在 __[main](file:///b:/project/arcprize/taa3-try-arg-agi-3/human_player/__main__.py#L173-L177)__[.py:173-177](file:///b:/project/arcprize/taa3-try-arg-agi-3/human_player/__main__.py#L173-L177)：

```python
elif key == '\x00' or key == '\xe0':
    ext = msvcrt.getwch()
    ext_key = '\x00' + ext
```

这段代码假设方向键返回 Windows 控制台扫描码（`\x00H/P/K/M`），但这只在 **cmd/PowerShell** 中成立。在 **Git Bash** 中，方向键发送的是 **VT 转义序列**：

| 按键 | cmd/PowerShell | Git Bash |
| -- | -------------- | -------- |
| ↑  | `\x00H`        | `\x1b[A` |
| ↓  | `\x00P`        | `\x1b[B` |
| ←  | `\x00K`        | `\x1b[D` |
| →  | `\x00M`        | `\x1b[C` |

当前代码只处理了 `\x00`/`\xe0` 前缀，完全没处理 `\x1b` 前缀的 VT 序列，所以方向键在 Git Bash 中无效。

**修复方案**：在 `_read_key()` 中增加 VT 转义序列解析，同时保留现有 Windows 扫描码支持。

### 问题 2：鼠标点击不可用

**根因**：当前 ACTION6（点击）只能通过按 `c` 键手动输入 `x,y` 坐标（[config.py](file:///b:/project/arcprize/taa3-try-arg-agi-3/human_player/config.py) 中 KEYMAP 没有绑定 ACTION6），没有任何鼠标事件监听。64×64 的网格让手动输坐标极其痛苦。

***

## 调研结论：Windows Terminal 鼠标捕获

### VT 转义序列方案（推荐尝试）

Windows Terminal 支持 **VT 鼠标追踪协议**，通过向 stdout 发送转义序列启用：

| 转义序列          | 模式     | 说明                      |
| ------------- | ------ | ----------------------- |
| `\x1b[?1000h` | Normal | 报告按钮按下和释放               |
| `\x1b[?1006h` | SGR 扩展 | 使用 SGR 格式，坐标无限制（**推荐**） |

启用后，鼠标点击事件以 SGR 格式通过 stdin 回传：

```
\x1b[<0;Cx;CyM   ← 左键按下（Cx=列号1-based, Cy=行号1-based）
\x1b[<0;Cx;Cym   ← 左键释放
```

**优点**：

* 零额外依赖

* 与现有 msvcrt 键盘读取可共存

* Windows Terminal 原生支持

**核心挑战 — 终端坐标→网格坐标映射**：

根据 [arc\_agi/rendering.py](file:///b:/useradmin/.cache/rattler/uv-cache/archive-v0/7ox3Vx6L9mpstzW_f8ciz/arc_agi/rendering.py) 源码分析：

* 每个网格单元 = `██`（2 个字符宽度）

* 帧头：`Step: X - State: Y\n\n`（占 2 行）

* 网格从第 3 行开始（0-based row 2）

映射公式：

```
grid_x = (terminal_col - 1) // 2    # SGR 坐标 1-based → 0-based，每格 2 字符宽
grid_y = terminal_row - 3           # 减去帧头 2 行 + SGR 1-based 偏移
```

**风险**：

* Git Bash 的 MSYS2 PTY 层可能干扰 VT 序列传递

* 终端窗口缩放/字体变化会影响坐标映射

* 需要精确知道网格在终端中的起始位置

### 其他方案对比

| 方案                       | 鼠标精度   | 依赖      | 开发量 | 与现有代码兼容性 | 可靠性             |
| ------------------------ | ------ | ------- | --- | -------- | --------------- |
| **VT 转义序列**              | 中（需映射） | 无       | 小   | 好        | 中（Git Bash 不确定） |
| **Pygame 自定义渲染**         | 高      | pygame  | 大   | 需重构渲染    | 高               |
| **Matplotlib 模式 + 鼠标钩子** | 高      | 无（已有）   | 中   | 中        | 中               |
| **blessed 库**            | 中      | blessed | 小   | 中        | 中               |

***

## 推荐方案：分阶段渐进增强

### 阶段 1：修复方向键（必做，低风险）

修改 `_read_key()` 和键位映射，同时支持 Windows 扫描码和 VT 转义序列：

1. 在 `config.py` 的 `KEYMAP_ARROWS` 中增加 VT 序列映射：

   ```python
   KEYMAP_ARROWS = {
       '\x00H': GameAction.ACTION1,  # Windows 扫描码
       '\x00P': GameAction.ACTION2,
       '\x00K': GameAction.ACTION3,
       '\x00M': GameAction.ACTION4,
       '\x1b[A': GameAction.ACTION1,  # VT 转义序列（Git Bash）
       '\x1b[B': GameAction.ACTION2,
       '\x1b[D': GameAction.ACTION3,
       '\x1b[C': GameAction.ACTION4,
       'f': GameAction.ACTION5,
       'z': GameAction.ACTION7,
       'r': GameAction.RESET,
   }
   ```

2. 修改 `_read_key()` 增加 VT 序列解析：

   * 检测到 `\x1b` 前缀时，继续读取后续字符（`[` + `A/B/C/D`）

   * 设置短超时（\~50ms）避免误判单独的 Esc 键

   * 保留现有 `\x00`/`\xe0` 扫展键处理

3. 同时修复 WASD 方案中的 Esc 键检测（当前 `\x1b` 会被忽略）

### 阶段 2：添加 VT 鼠标追踪（尝试性，零依赖）

在现有终端模式基础上增加鼠标点击支持：

1. **启用 VT 模式**：通过 ctypes 调用 Windows API 启用 `ENABLE_VIRTUAL_TERMINAL_PROCESSING`

2. **启用鼠标追踪**：游戏循环开始时发送 `\x1b[?1000h\x1b[?1006h`，退出时发送关闭序列

3. **解析鼠标事件**：在 `_read_key()` 的读取循环中，检测 SGR 格式鼠标序列 `\x1b[<Cb;Cx;CyM/m`

4. **坐标映射**：将终端 (col, row) 转换为网格 (x, y)

   * 需要运行时校准：首次使用时显示提示让用户点击已知位置来校准偏移量

   * 或者硬编码默认偏移（帧头 2 行 + 网格左对齐）

5. **集成到游戏循环**：鼠标左键点击 → 检查 ACTION6 是否可用 → 转换坐标 → 执行 `env.step(ACTION6, data={"x": gx, "y": gy})`

6. **安全清理**：`try/finally` + `atexit` 确保退出时关闭鼠标追踪

### 阶段 3：如果 VT 鼠标不可靠，切换到 Pygame（备选）

如果阶段 2 在 Git Bash + Windows Terminal 环境下测试不通过，则实施 Pygame 方案：

1. **添加 pygame 依赖**到 pixi.toml

2. **创建 Pygame 渲染器**：

   * 读取 `FrameDataRaw.frame`（64×64 numpy 数组）

   * 使用 ARC-AGI-3 的 16 色调色板渲染到 pygame 窗口

   * 每个格子 8-10 像素，总窗口约 640×640 + HUD 区域

3. **输入处理**：

   * pygame 键盘事件 → GameAction 映射（WASD / 方向键均原生支持）

   * pygame 鼠标事件 → ACTION6 坐标（像素坐标 / cell\_size → 网格坐标，精确）

4. **与 ARC-AGI-3 集成**：

   * 使用 `arc.make(game_id)` 不带 render\_mode（禁用内置渲染）

   * 手动从 `env.observation_space.frame` 读取帧数据

   * 在 pygame 中渲染

5. **保留终端菜单**：游戏选择、进度、设置仍用 rich 终端菜单，只在游戏中切换到 pygame

***

## 实施步骤（阶段 1 + 阶段 2）

### 步骤 1：修复方向键 — 修改 `_read_key()`

文件：`human_player/__main__.py`

* 重写 `_read_key()` 为 `_read_input()`，返回类型改为 `tuple[str, dict | None]`

  * 键盘事件返回 `(key_str, None)`

  * 鼠标事件返回 `("MOUSE_CLICK", {"col": c, "row": r})`

* 增加 VT 转义序列解析逻辑：

  * `\x1b` → 等待 50ms → 读取 `[` + 方向字母 → 拼接为 `\x1b[A` 等

  * `\x1b` → 等待 50ms → 读取 `[<` → 继续读取 SGR 鼠标序列

  * 单独 `\x1b`（无后续）→ 视为 Esc 键

### 步骤 2：修复方向键 — 更新键位映射

文件：`human_player/config.py`

* `KEYMAP_ARROWS` 增加 VT 序列键

* 增加 `KEYMAP_ARROWS_VT` 常量或直接合并到 `KEYMAP_ARROWS`

* 更新 `ARROW_HELP` 提示文本

### 步骤 3：修复方向键 — 更新游戏循环

文件：`human_player/__main__.py`

* 更新 `_game_loop()` 中的键位查找逻辑，兼容新的输入格式

### 步骤 4：添加 VT 鼠标追踪 — 启用/禁用函数

文件：新建 `human_player/mouse.py`

* `enable_vt_mode()` — ctypes 启用虚拟终端处理

* `enable_mouse_tracking()` — 发送 VT 鼠标追踪序列

* `disable_mouse_tracking()` — 关闭鼠标追踪

* `parse_sgr_mouse(buf)` — 从缓冲区解析 SGR 鼠标事件

* `terminal_to_grid(col, row, offset_x, offset_y)` — 终端坐标转网格坐标

### 步骤 5：添加 VT 鼠标追踪 — 集成到游戏循环

文件：`human_player/__main__.py`

* 游戏循环开始时调用 `enable_mouse_tracking()`

* 在输入读取循环中检测鼠标事件

* 鼠标左键点击 → 转换坐标 → 执行 ACTION6

* 游戏循环结束时（finally）调用 `disable_mouse_tracking()`

### 步骤 6：测试验证

* 在 Windows Terminal + Git Bash 中测试方向键

* 在 Windows Terminal + Git Bash 中测试鼠标点击

* 在 Windows Terminal + PowerShell 中测试（对比）

* 如果 VT 鼠标在 Git Bash 中不可靠，记录问题并准备阶段 3

***

## 关键设计决策

### 决策 1：优先尝试 VT 鼠标而非直接跳到 Pygame

理由：

* 零依赖，与现有架构完全兼容

* 如果成功，是最小改动方案

* 即使失败，也只需回退到手动坐标输入，不影响其他功能

* Pygame 方案作为备选，随时可以启动

### 决策 2：VT 序列解析放在 \_read\_key() 内部而非独立线程

理由：

* msvcrt.getwch() 已经是非阻塞的

* VT 鼠标序列通过 stdin 传入，和键盘事件走同一个通道

* 不需要额外的线程或库

* 保持代码简单

### 决策 3：坐标映射采用可校准方案

理由：

* 不同终端字体/窗口大小会影响偏移量

* 提供默认值（帧头 2 行 + 左对齐），同时支持运行时校准

* 校准方式：显示一个标记在已知网格位置，让用户点击，计算偏移差

***

## 风险与缓解

| 风险                            | 概率 | 影响      | 缓解                       |
| ----------------------------- | -- | ------- | ------------------------ |
| Git Bash MSYS2 PTY 吞掉 VT 鼠标序列 | 中  | 鼠标不可用   | 测试确认，不行则启动阶段 3 Pygame    |
| VT 序列与 msvcrt 读取冲突            | 低  | 丢失事件    | 使用缓冲区拼接 + 正则匹配           |
| 坐标映射不准                        | 中  | 点击偏移    | 运行时校准 + 视觉反馈（高亮悬停格）      |
| 程序崩溃未关闭鼠标追踪                   | 低  | 终端异常    | atexit + try/finally 双保险 |
| Python 3.14 + pygame 兼容性      | 中  | 阶段 3 阻塞 | 先测试兼容性，必要时降级             |

