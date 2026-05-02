# REST API 参考

## 概述

ARC-AGI-3 提供了 REST API，用于以编程方式与游戏环境交互。这是 Toolkit 和 Swarm 底层使用的同一套 API。

**基础 URL**：`https://three.arcprize.org`

**认证**：所有请求需要 `X-API-Key` 头。

## 认证

### 获取 API Key

1. 前往 [arcprize.org/platform](https://arcprize.org/platform)
2. 使用 Google 或 GitHub 注册
3. 在用户资料的 API Keys 部分创建新 Key

### 使用 API Key

```python
import requests

session = requests.Session()
session.headers.update({
    "X-API-Key": "your-api-key-here",
    "Accept": "application/json"
})
```

## 会话亲和性（重要）

游戏是有状态的，服务器会设置 Cookie（特别是 `AWSALB*` Cookie），后续请求**必须包含这些 Cookie** 以保持会话亲和性。

大多数 HTTP 客户端（如 `requests.Session()`）会自动处理 Cookie，但请确保你的客户端保存并发送从 RESET 和 ACTION 响应中收到的 Cookie。

```python
session = requests.Session()
session.headers.update({
    "X-API-Key": API_KEY,
    "Accept": "application/json"
})
```

## API 端点

### 获取可用游戏

```
GET /api/games
```

返回可用游戏列表。

```python
response = session.get(f"{ROOT_URL}/api/games")
games = [g["game_id"] for g in response.json()]
```

### 打开记分卡

```
POST /api/scorecard/open
```

请求体：

```json
{
    "tags": ["experiment1", "v2.0"]
}
```

返回：

```json
{
    "card_id": "abc123..."
}
```

### 关闭记分卡

```
POST /api/scorecard/close
```

请求体：

```json
{
    "card_id": "abc123..."
}
```

### 开始/重置游戏

```
POST /api/cmd/RESET
```

请求体：

```json
{
    "game_id": "ls20-016295f7601e",
    "card_id": "abc123..."
}
```

返回：

```json
{
    "guid": "session-guid...",
    "state": "NOT_FINISHED",
    "score": 0,
    "frame": [...]
}
```

### 执行简单动作

```
POST /api/cmd/ACTION{1-5,7}
```

请求体：

```json
{
    "game_id": "ls20-016295f7601e",
    "card_id": "abc123...",
    "guid": "session-guid..."
}
```

### 执行复杂动作（ACTION6）

```
POST /api/cmd/ACTION6
```

请求体：

```json
{
    "game_id": "ls20-016295f7601e",
    "card_id": "abc123...",
    "guid": "session-guid...",
    "x": 10,
    "y": 20
}
```

## 完整游戏流程示例

```python
import requests
import os
import random
from dotenv import load_dotenv

load_dotenv()

ROOT_URL = "https://three.arcprize.org"
API_KEY = os.getenv("ARC_API_KEY")

session = requests.Session()
session.headers.update({
    "X-API-Key": API_KEY,
    "Accept": "application/json"
})

# 1. 获取可用游戏
response = session.get(f"{ROOT_URL}/api/games")
games = [g["game_id"] for g in response.json()]
game_id = random.choice(games)

# 2. 打开记分卡
response = session.post(
    f"{ROOT_URL}/api/scorecard/open",
    json={"tags": ["manual_demo"]}
)
card_id = response.json()["card_id"]

# 3. 开始游戏
response = session.post(
    f"{ROOT_URL}/api/cmd/RESET",
    json={"game_id": game_id, "card_id": card_id}
)
game_data = response.json()
guid = game_data["guid"]
state = game_data["state"]
score = game_data.get("score", 0)

# 4. 执行动作
for i in range(5):
    if state in ["WIN", "GAME_OVER"]:
        break

    action = random.choice(["ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "ACTION7"])
    request_data = {
        "game_id": game_id,
        "card_id": card_id,
        "guid": guid
    }

    if action == "ACTION6":
        request_data["x"] = random.randint(0, 29)
        request_data["y"] = random.randint(0, 29)

    response = session.post(
        f"{ROOT_URL}/api/cmd/{action}",
        json=request_data
    )
    game_data = response.json()
    state = game_data["state"]
    score = game_data.get("score", 0)

# 5. 关闭记分卡
session.post(
    f"{ROOT_URL}/api/scorecard/close",
    json={"card_id": card_id}
)

print(f"View results at: {ROOT_URL}/scorecards/{card_id}")
```

## 速率限制

| 项目 | 值 |
|------|-----|
| 速率限制 | 600 请求/分钟（RPM） |
| 超出响应 | `429` 状态码 |
| 超出响应体 | `{"error":"RATE_LIMIT_EXCEEDED","message":"rate limit has been exceeded"}` |
| SLA | 无（研究预览版，尽力服务） |

### 请求提升限制

如需更高吞吐量，联系 team@arcprize.org，主题行 "Increase Rate Limits"。

## 错误码

| 状态码 | 含义 | 处理方式 |
|--------|------|---------|
| 200 | 成功 | 正常处理 |
| 400 | 游戏已结束（GAME_OVER） | 发送 RESET 重置游戏 |
| 429 | 速率限制超出 | 等待后重试，使用指数退避 |
| 500 | 服务器端问题 | 稍后重试 |

## 本地 REST 服务器

使用 Toolkit 可以启动本地 REST 服务器，提供与在线 API 相同的接口：

```python
from arc_agi import Arcade

arc = Arcade()
arc.listen_and_serve(port=8001)
```

这在以下场景特别有用：

- 使用非 Python 语言开发智能体
- 在本地复现 Kaggle 竞赛环境
- 需要更快的响应速度（无网络延迟）

## OpenAPI 规范

完整的 API 规范可在官方文档的 `arc3v1.yaml` 文件中找到，位于 `plgd/arcprize-docs/arc3v1.yaml`。

## 参见

- [智能体开发指南](agent-development.md) — 使用 Toolkit 开发智能体
- [游戏机制详解](game-mechanics.md) — 游戏状态和帧数据
- [动作参考手册](actions-reference.md) — 动作接口详解
