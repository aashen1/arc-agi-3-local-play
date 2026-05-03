# Pygame 菜单 UI 细节优化计划

## 问题总览

5 个优化任务，按依赖关系和难度排序实施：

| # | 任务                  | 难度 | 涉及文件                                                 |
| - | ------------------- | -- | ---------------------------------------------------- |
| 1 | 背景点击退出 Bug + 按钮鼠标支持 | 低  | `__main__.py`, `menu.py`                             |
| 2 | 进度条 + 完成勾 + 上次游玩高亮  | 中  | `menu.py`, `level_manager.py`                        |
| 3 | 关卡宫格布局 + 列表滚动模式     | 高  | `menu.py`, `__main__.py`, `config.py`                |
| 4 | 窗口缩放与最大化支持          | 高  | `config.py`, `__main__.py`, `menu.py`, `renderer.py` |

***

## 任务 1：背景点击退出 Bug + 按钮鼠标支持

### 根因分析

[`_handle_menu_event`](__main__.py:276) 中，键盘按 Q 返回 `None` 表示退出；但 [`handle_main_menu_click`](menu.py:102) 在点击空白区域时也返回 `None`，主循环把 `None` 统一当作"退出"处理：

```python
# __main__.py:70-72
result = _handle_menu_event(event, menu_renderer, games)
if result is None:          # ← 点击空白也走到这里！
    pygame.quit()
    sys.exit()
```

同时，点击 Quit 按钮返回 `"quit"` 字符串，但主循环没有处理 `"quit"` 分支，导致 Quit 按钮鼠标点击无效。

### 修复方案

1. **`menu.py`** **—** **`handle_main_menu_click`**：点击空白区域返回 `False` 而非 `None`
2. **`__main__.py`** **— 主循环**：增加 `result == "quit"` 分支处理
3. **`menu.py`** **— 按钮悬停效果**：为底部按钮增加 hover 高亮（与游戏列表 hover 一致），让用户感知按钮可点击
4. **`menu.py`** **— 按钮光标**：鼠标悬停在按钮上时，记录 hover 状态，绘制时改变背景色

### 具体改动

**`menu.py`**:

* 新增 `self.button_hover = None` 属性

* `handle_main_menu_hover` 增加按钮区域检测，设置 `self.button_hover`

* `draw_main_menu` 绘制按钮时，根据 `self.button_hover` 改变背景色

* `handle_main_menu_click` 末尾 `return None` → `return False`

**`__main__.py`**:

* 主循环 MAIN\_MENU 分支增加 `elif result == "quit"` → 退出

* 确保 `result is None` 只在键盘 Q 时触发

***

## 任务 2：进度条 + 完成勾 + 上次游玩高亮

### 当前状态

* `menu.py:57-62` 已有文字进度 `"4/7"`，但无视觉进度条

* `level_manager.py` 已有 `completed_at` 时间戳，可据此判断"上次游玩"

* 无"已完成"视觉标记（绿色勾）

### 实现方案

1. **完成勾（✓）**：当 `completed == total and total > 0` 时，在游戏条目右侧绘制绿色勾
2. **视觉进度条**：在文字进度下方绘制一个细长矩形，填充比例 = `completed / total`

   * 底色：深灰 `(60, 60, 60)`

   * 填充色：`COLOR_WIN`（绿色）

   * 高度 6px，圆角
3. **上次游玩高亮**：遍历所有游戏的 `completed_at`，找到最新时间戳对应的游戏，给该条目加一个左边框高亮（`COLOR_HIGHLIGHT` 金色，3px 宽）
4. **LevelManager 扩展**：新增 `get_last_played_game_id()` 方法，遍历所有游戏的所有关卡找最新 `completed_at`

### 具体改动

**`level_manager.py`**:

* 新增 `get_last_played_game_id() -> str | None`

* 新增 `get_level_progress(game_id) -> dict`，返回每关的完成状态列表（供进度条细分显示）

**`menu.py`**:

* `draw_main_menu` 中每个游戏条目增加：

  * 进度条绘制（6px 高，位于文字进度下方）

  * 完成勾绘制（绿色 ✓，位于条目右侧）

  * 上次游玩高亮（左边框 3px 金色）

* 新增 `_draw_progress_bar(x, y, w, completed, total)` 辅助方法

* 新增 `_draw_checkmark(x, y, size)` 辅助方法

***

## 任务 3：关卡宫格布局 + 列表滚动模式

### 当前问题

25 个游戏以列表排列，每行 60px，第 9 行（y=580）已与底部按钮（y=590）重叠，后面的游戏完全不可见。

### 两种 UI 模式

#### 模式 A：宫格模式（默认）

* 5 列 × 5 行，所有游戏一页展示

* 每个单元格约 140×90 px

* 单元格内容：

  * 四位游戏 ID（大字，居中）

  * 迷你进度条（底部 4px）

  * 完成勾（右上角小绿勾）

  * 上次游玩高亮（单元格边框金色）

* 鼠标悬停时单元格背景变亮

* 点击单元格进入游戏

#### 模式 B：列表模式（verbose）

* 保持当前一行一行的布局，但增加：

  * 右侧滚动条（宽 12px）

  * 鼠标滚轮滚动

  * 拖拽滚动条滑块

  * 点击滚动条轨道跳转

* 每行显示：编号、游戏 ID、标题、进度条、完成勾、标签

* 底部按钮区域固定不随滚动

### 切换按钮

* 右上角放置一个切换按钮（图标或文字 "⊞/☰"）

* 点击切换宫格/列表模式

* 模式偏好保存到 `user_config.json`

### 滚动实现

**`menu.py`** **新增属性**:

* `self.view_mode = "grid"` / `"list"`

* `self.scroll_offset = 0`（列表模式下的滚动偏移）

* `self.scroll_dragging = False`

* `self.scroll_thumb_rect = None`

**滚动条绘制**:

* 轨道：右侧 12px 宽的半透明条

* 滑块：根据可见比例计算高度和位置

* 颜色：轨道 `COLOR_PANEL`，滑块 `COLOR_ACCENT`

**事件处理**:

* `pygame.MOUSEWHEEL`：调整 `scroll_offset`，步长 = 一行高度（60px）

* 鼠标左键按下在滑块上：开始拖拽

* 鼠标左键按下在轨道上：跳转到对应位置

* 鼠标移动（拖拽中）：更新 `scroll_offset`

* 鼠标左键释放：结束拖拽

**滚动范围**:

* 最大滚动 = 总内容高度 - 可见区域高度

* `scroll_offset` 钳制在 `[0, max_scroll]`

### 具体改动

**`config.py`**:

* 新增 `VIEW_MODE_KEY = "view_mode"` 配置键

**`level_manager.py`**:

* 新增 `get_last_played_game_id()` 方法

**`menu.py`**:

* 重构 `draw_main_menu` 为 `_draw_grid_menu` 和 `_draw_list_menu`

* 新增 `_draw_scrollbar`、`_draw_grid_cell`、`_draw_list_item` 辅助方法

* 新增 `handle_scroll`、`handle_scrollbar_click`、`handle_scrollbar_drag` 方法

* 新增 `toggle_view_mode` 方法

* `handle_main_menu_click` 根据当前模式分发到 `_handle_grid_click` 或 `_handle_list_click`

* `handle_main_menu_hover` 同理

**`__main__.py`**:

* 主循环增加 `pygame.MOUSEWHEEL` 事件处理

* 主循环增加视图模式切换按钮点击处理

* 增加 `scroll_offset` 状态变量传递

***

## 任务 4：窗口缩放与最大化支持

### 设计策略：虚拟分辨率 + 表面缩放

核心思路：所有渲染逻辑仍基于 800×640 的"设计分辨率"，最终通过 `pygame.transform.scale` 缩放到实际窗口大小。这样改动最小，且不会破坏现有布局。

### 实现步骤

1. **创建窗口时添加** **`pygame.RESIZABLE`** **标志**

   ```python
   screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
   ```

2. **新增虚拟渲染表面**

   ```python
   virtual_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
   ```

   所有绘制操作改为在 `virtual_surface` 上进行，最后缩放 blit 到 `screen`。

3. **处理** **`pygame.VIDEORESIZE`** **事件**

   * 更新 `screen` 为新尺寸

   * 记录当前窗口尺寸 `window_w, window_h`

4. **缩放与居中（保持宽高比）**

   * 计算缩放因子：`scale = min(window_w / DESIGN_W, window_h / DESIGN_H)`

   * 计算缩放后尺寸：`scaled_w = int(DESIGN_W * scale)`, `scaled_h = int(DESIGN_H * scale)`

   * 计算偏移居中：`offset_x = (window_w - scaled_w) // 2`, `offset_y = (window_h - scaled_h) // 2`

   * 渲染流程：

     ```python
     virtual_surface.fill(COLOR_BG)  # 先清空（letterbox 背景）
     # ... 所有绘制在 virtual_surface 上 ...
     scaled = pygame.transform.scale(virtual_surface, (scaled_w, scaled_h))
     screen.fill((0, 0, 0))  # letterbox 黑边
     screen.blit(scaled, (offset_x, offset_y))
     ```

5. **鼠标坐标转换**

   * 窗口坐标 → 设计坐标：

     ```python
     def window_to_design(wx, wy):
         dx = (wx - offset_x) / scale
         dy = (wy - offset_y) / scale
         return int(dx), int(dy)
     ```

   * 所有鼠标事件处理前先转换坐标

6. **最小窗口尺寸限制**

   * 设置最小尺寸为 800×640，防止窗口过小导致 UI 不可用

   * 在 `VIDEORESIZE` 事件中钳制尺寸

7. **最大化支持**

   * `pygame.RESIZABLE` 自动支持 Windows 最大化按钮

   * 最大化后窗口填满屏幕，内容等比缩放 + letterbox

### 具体改动

**`config.py`**:

* 新增 `DESIGN_WIDTH = 800`, `DESIGN_HEIGHT = 640`（与现有 `WINDOW_WIDTH/HEIGHT` 一致，语义更清晰）

* 新增 `MIN_WINDOW_WIDTH = 800`, `MIN_WINDOW_HEIGHT = 640`

**`__main__.py`**:

* 窗口创建添加 `pygame.RESIZABLE`

* 新增 `virtual_surface`、`window_size`、`scale`、`offset` 状态变量

* 新增 `window_to_design()` 坐标转换函数

* 事件循环增加 `pygame.VIDEORESIZE` 处理

* 所有 `screen.blit` / 绘制调用改为在 `virtual_surface` 上操作

* 主循环末尾增加缩放+居中+blit 逻辑

* 鼠标坐标获取后先转换

**`menu.py`**:

* 构造函数接收 `virtual_surface` 而非 `screen`（或保持 `screen` 引用，由调用方确保指向虚拟表面）

**`renderer.py`**:

* 同上，构造函数接收虚拟表面

***

## 实施顺序

```
任务 1（Bug 修复 + 按钮鼠标）
  ↓
任务 2（进度条 + 完成勾 + 上次游玩高亮）
  ↓
任务 3（宫格布局 + 列表滚动）
  ↓
任务 4（窗口缩放）
```

任务 2 是任务 3 的前置依赖（宫格单元格需要进度条和完成勾），任务 4 放最后因为缩放机制是全局性的，先完成所有 UI 改动再统一适配。

***

## 风险与注意事项

1. **滚动事件与缩放的交互**：任务 4 完成后，鼠标滚轮事件需要同时处理滚动和坐标转换，需仔细测试
2. **字体缩放**：虚拟分辨率方案下字体不需要动态调整，因为始终在 800×640 上渲染，只是最终整体缩放
3. **性能**：每帧多一次 `pygame.transform.scale`，对 800×640 → 1920×1080 的缩放开销可忽略
4. **游戏内渲染**：`renderer.py` 的网格渲染也需要迁移到虚拟表面，但逻辑不变

