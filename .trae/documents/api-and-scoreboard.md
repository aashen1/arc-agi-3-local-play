基于官网与文档，结论很明确：**API key 是 ARC API 的认证/授权入口，不是“人类/agent 身份标签”；排行榜数据则来自在线 scorecard/leaderboard 流程，而不是本地离线运行。** 对你这个“用面向 Agent 的 SDK 包一层 pygame，给人类玩家玩”的场景，**最安全的做法是完全本地化：`OFFLINE`、不设置 `ARC_API_KEY`、不走 scorecard/leaderboard API**。文档明确写了本地模式“无在线 scorecards、无分享 replay、无需 API key”，而在线模式才会产生 scorecards/replays 并进入 leaderboard。([ARC-AGI-3 文档][1])

1. **API key 的核心作用与使用场景**

   API key 的文档写法是：它允许你“跨游戏、跨会话追踪进度”，并在未来解锁完整公开游戏列表；在 Toolkit 里通过环境变量 `ARC_API_KEY` 或构造参数 `arc_api_key` 传入。与此同时，`arc_api_key` 这一项又被明确标成 **ONLINE mode 必需**；如果你没有给 key、但也没有处于 OFFLINE，Toolkit 会**自动拉取一个匿名 key**。([ARC-AGI-3 文档][2])

   匿名 key 的工作机制，文档给了两个关键信号：一是“空值且非离线时自动获取匿名 key”；二是“匿名用户在发布后默认只能玩 3 个游戏，想解锁剩余公开游戏需要 API key”。也就是说，**匿名 key 不是“无权限”，而是“默认游客态”**；它能让你继续跑，但不是注册态的完整访问。([ARC-AGI-3 文档][3])

   什么时候必须配 key？文档上最硬的一条是：**只要你要用 `OperationMode.ONLINE`，就需要 API key**；而 `OperationMode.OFFLINE` 则明确“不需要 API key”。如果你只是本地开发/测试，离线模式就是推荐路径。([ARC-AGI-3 文档][1])

2. **排行榜系统的运作机制**

   官网和技术报告把排行榜分成两类语义：**官方/verified（面向模型与前沿系统）** 和 **community（面向可复现、公开自报的提交）**。官方 policy 说得很直接：官方 leaderboard 的目标是衡量前沿模型接近人类级通用智能的程度，并且会尽量排除“专门针对 ARC-AGI-3 的 harness/过拟合”；community leaderboard 则是公开、自报、通常不独立验证。ARC-AGI-3 的技术报告还明确说，**官方 leaderboard 不会用 harness 报官方分数，公共集分数也不会出现在官方 leaderboard 上**。([ARC Prize][4])

   在 Toolkit 里，**scorecard 是进入在线成绩体系的核心对象**：它聚合的是“agent 的游戏表现”；通过 API 跑的 scorecard 能在 arcprize.org/scorecards 上查看；并且文档写明 **agent scorecards 会每约 15 分钟批量加入 leaderboard**。这条链路说明：**真正触发上传的是在线 scorecard 流程，不是本地 render 或普通 step 本身**。([ARC-AGI-3 文档][5])

   另外，`OperationMode.COMPETITION` 还被单独规定为：**为了出现在 Unverified leaderboard 必须使用**，并强制只能通过 API 交互、只能开一个 scorecard、不能中途读取 inflight scorecard、只能做 level reset 等。Kaggle 竞赛也被强制到这个模式。这个模式本身就是“排行榜/评测”通道，而不是人类本地试玩通道。([ARC-AGI-3 文档][6])

3. **人类玩家场景的特殊考量**

   你问“人类玩家能否通过本地配置 API key 将成绩上传至人类排行榜”，文档里**没有给出一个“人类排行榜 + API key 上传”的独立入口**。相反，community leaderboard 的提交方式是 **GitHub repo 自报提交**，官方 policy 也说社区榜单不做默认独立验证；而 API key 的文档只说它用于追踪进度、解锁游戏，并没有说它能把“人类试玩”写入某个人类专用榜单。换句话说，**文档没有支持“用 key 把人类成绩上传到人类排行榜”的工作流**。([ARC Prize][7])

   你问“人类排行榜是否仅记录网页在线游玩数据，而 SDK 仅用于 agent 数据收集”，从文档更合理的解读是：**网页 UI 是给人类手动玩游戏的入口；SDK/REST/scorecard 这一套是给 agent/harness 记录成绩的入口**。`Actions` 页面专门列了 human player keybindings；但 `Scorecards` 页面又把 scorecards 定义为“agent performance”的汇总。文档没有写“人类 UI 成绩会自动进入某个独立的人类排行榜”，所以这更像是**人类试玩入口**与**agent 评测通道**的分离，而不是“人类榜单上传管道”。([ARC-AGI-3 文档][8])

   关于“用 SDK 包 pygame 给人类玩，会不会把人类成绩误判成 agent 数据并上传”，**风险是存在的**。原因不是“系统会识别你是不是人类”，而是文档层面的上传条件只看你是否走 **API + scorecard** 流程：一旦你启用在线模式、开了 scorecard，系统就按 agent scorecard 去处理，并会批量进 leaderboard；它并没有一个“人类模式”的自动分流开关。反过来，**只要你保持 OFFLINE，本地 toolkit 又明确没有在线 scorecards 和 recordings**，就不会把人类试玩送进官方在线成绩流。([ARC-AGI-3 文档][5])

4. **API key 与排行榜的映射关系**

   你提到的“跨会话记录”和“分数记录”，从文档看，主体是 **scorecard 所记录的那次运行/那组运行**，而不是“人类身份本身”。`make()` 支持一个默认 scorecard，被自动复用到多次 `make()` 调用；`get_scorecard()` 与 `close_scorecard()` 也都是围绕这个默认 scorecard 工作。也就是说，这套映射关系是 **会话/运行级** 的；在官方语言里，它服务的是 **agent 的 performance tracking**。([ARC-AGI-3 文档][3])

   “官网账号绑定的 API key 会不会把人类玩家数据误传至 AI 排行榜”的答案是：**只要你用这个 key 走了在线 scorecard 流程，就有这种操作层面的风险；但 key 本身不是自动上传器。** 文档里真正决定是否进排行榜的是：是否在 API/在线模式下创建并关闭 scorecard、以及是否属于 agent scorecard / competition mode。换句话说，**key 只是门票，上传是后续 scorecard 流程做的事**。([ARC-AGI-3 文档][3])

5. **给你这个“pygame 包装给人类玩”的明确配置建议**

   最稳妥的配置是：

```python
from arc_agi import Arcade, OperationMode

arc = Arcade(operation_mode=OperationMode.OFFLINE)
env = arc.make("ls20", render_mode="human")
```

同时把环境变量里可能存在的在线配置去掉，尤其是不要让程序在非离线模式下“自动抓匿名 key”。文档里已经说明：**空 key 且非离线时会自动获取匿名 key**；而离线模式是**无 API key、无在线 scorecards** 的本地模式。([ARC-AGI-3 文档][3])

具体建议是这四条：第一，**显式用 `OperationMode.OFFLINE`**，不要用默认 `Arcade()`；第二，**不要设置 `ARC_API_KEY`**；第三，**不要调用 `create_scorecard/open_scorecard/get_scorecard/close_scorecard`**，也不要切到 `ONLINE` 或 `COMPETITION`；第四，**玩家成绩单独存你自己的本地日志，不要复用 ARC 的 scorecard**。这样可以把人类试玩和 ARC 的 agent 评测流彻底隔离开。([ARC-AGI-3 文档][3])

一句话总结：**对人类版 pygame 包装，默认原则是“离线、无 key、无 scorecard、无 competition mode”。** 这会最大程度避免人类数据意外进入 ARC 的 AI 评测/排行榜体系。([ARC-AGI-3 文档][1])

如果你愿意，我可以把上面的结论再整理成一份更适合内部评审的“风险矩阵 + 配置清单”。

[1]: https://docs.arcprize.org/local-vs-online "Local vs Online - ARC-AGI-3 Docs"
[2]: https://docs.arcprize.org/api-keys "API Keys - ARC-AGI-3 Docs"
[3]: https://docs.arcprize.org/toolkit/arc_agi "Arcade - ARC-AGI-3 Docs"
[4]: https://arcprize.org/policy "ARC Prize Verified Testing Policy"
[5]: https://docs.arcprize.org/scorecards "Scorecards - ARC-AGI-3 Docs"
[6]: https://docs.arcprize.org/toolkit/competition_mode "Competition Mode - ARC-AGI-3 Docs"
[7]: https://arcprize.org/leaderboard/community "ARC Prize - Community Leaderboard"
[8]: https://docs.arcprize.org/actions?utm_source=chatgpt.com "Actions - ARC-AGI-3 Docs"


----


下面按你这三个场景拆开说，我只依据官网/文档能确认的机制来判断。核心判断先放在前面：**只要你走到“API / online / scorecard”这条链路，ARC 就把它当作 agent 评测通道；人类手动游玩要尽量留在纯本地离线链路里。** 文档里明确写了：`ONLINE` 会启用 scorecards 和 replays，并且结果会出现在 leaderboard；`OFFLINE` 只加载本地游戏、没有在线 scorecards、也不需要 API key。([ARC-AGI-3 文档][1])

**场景 1：不配 key，NORMAL 模式，自动抓匿名 key，然后你用“人类界面”去玩。**
这时 `Arcade()` 默认是 `NORMAL`，会同时加载本地和远端游戏；如果没有 key 但又不是 `OFFLINE`，文档说会自动获取匿名 key。匿名用户默认只能访问 3 个游戏，剩余公开游戏需要 API key 才能解锁。([ARC-AGI-3 文档][2])
风险点在于：**你一旦仍然是在 SDK/API 这条链路里跑，文档中的“scorecard”就是按“agent performance”来定义的，而且 API 运行的 scorecard 可在线查看，agent scorecard 还会大约每 15 分钟批量进入 leaderboard。**所以，哪怕你的操作者是人，只要程序侧仍然在走在线/API scorecard 流程，就有被当作 agent 结果处理的风险。([ARC-AGI-3 文档][3])
所以这个场景下，**“匿名 key + NORMAL + 通过 SDK 玩”并不是我会推荐的人类试玩方案**；它适合“浏览本地+远端游戏并做程序化调用”，不适合作为“绝不污染 agent 排行榜”的保险方案。([ARC-AGI-3 文档][2])

**场景 2：你为了看全量游戏目录，给人类玩家配置了 API key。**
文档明确说：默认匿名用户只能访问 3 个游戏，**API key 用来解锁其余公开游戏**。同时，`ONLINE` 模式要求 API key，且是“scorecards and replays”的在线模式。([ARC-AGI-3 文档][4])
这里真正的“非预期上传”触发点，不是“key 本身”，而是**你是否让程序进入在线/API scorecard 通道**。因为 scorecards 记录的是 agent 的 game performance，API 跑出来的 scorecard 会在线可见，并且会进入 leaderboard。换句话说，**key 只是打开远端游戏的门票；一旦你的程序还在开 scorecard、走 online/competition/benchmarking，那就可能把人类操作记录进 ARC 的在线评分流。**([ARC-AGI-3 文档][3])
人类 leaderboard 是另一套网页页面，文档写的是“top humans…fewest actions”；我没有找到任何文档说明“API key 可以把人类游玩结果直接写进 human leaderboard”。所以，**你担心的“误进 agent 榜单”风险，主要来自在线 scorecard 路径，而不是 key 这个字符串本身。**([ARC Prize][5])

**场景 3：本地真的是 agent 在玩，如何正常提交成绩。**
这时就应该反过来：**明确使用在线/竞赛通道，而不是离线通道。** 文档说 `ONLINE` 会启用 scorecards 和 replays；`create_scorecard/open_scorecard` 是标准入口；而 `Competition Mode` 则是“显示在 Unverified leaderboard 所必需”，并且强制只通过 API 交互、只能开一个 scorecard、不能读取 inflight scorecard。([ARC-AGI-3 文档][1])
如果你只是做普通 agent 基准测试，官方还单独给了 benchmarking tooling：运行 benchmark 后会把 scorecard 存到 ARC server，登录后可在 arcprize.org/scorecards 查看。`Swarms` 也会自动管理 scorecard 打开和关闭。([ARC-AGI-3 文档][6])
所以，**agent 提交的正确姿势**就是：在线模式/benchmarking/competition mode + scorecard；而**人类试玩绝对不要用这套模式**。([ARC-AGI-3 文档][1])

**你最后问的重点：要不要“先用一次 key 把全量游戏缓存下来，然后以后全走 OFFLINE”？**
从文档能确认的是：`OFFLINE` 只看本地游戏，`NORMAL` 同时看本地+远端，`ONLINE` 只看远端；文档并**没有**给出一个清晰的“用一次 key 批量缓存远端游戏，然后永久离线使用”的标准工作流。([ARC-AGI-3 文档][2])
因此，**如果你的第一目标是“绝不让人类成绩污染 agent 榜单”，最稳妥的做法不是依赖一次性缓存技巧，而是把系统拆成两个配置档：**一个“管理员/同步”档，只用于你自己去发现、下载、整理游戏；另一个“人类游玩”档，固定 `OFFLINE`，不设置 `ARC_API_KEY`，不创建/打开/关闭 scorecard，不进 `ONLINE` / `COMPETITION` / benchmarking。这样才是文档语义下最干净的隔离。([ARC-AGI-3 文档][1])

一句话落地：**人类版 pygame 包装请默认 `OFFLINE`；只有真正的 agent 评测脚本才允许 `ONLINE` / `COMPETITION` / scorecard。** 如果你必须先拿全量目录，尽量把“同步远端游戏”的动作和“人类正式游玩”彻底分离，不要让同一个运行配置既能开 key 又能开 scorecard。([ARC-AGI-3 文档][1])

如果你愿意，我下一条可以直接给你一份“人类试玩安全配置模板”和“一份 agent 提交模板”，分别列出该设哪些环境变量、该禁哪些 API 调用。

