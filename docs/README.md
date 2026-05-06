# About this folder

Welcome! You may notice that the docs in this folder are written in Simplified Chinese — but don't worry, they're mostly LLM-generated notes based on the official library, and are just a developer's personal reference.

For any information about the original `arc-agi` library, please visit the [official documentation site](https://docs.arcprize.org/).
*(Note: The core game engine and logic come from the official `arc-agi` library. This repo is just a simple `pygame-ce` based wrapper that adds a UI and console interface, with some small life quality feat like local save. I did **not** design the games themselves.)*

For a basic introduction to this repo, please read the `README.md` file in the root directory.

-----

你好！欢迎欢迎。

这个文件夹里的其他文档没啥特别重要的，都是 AI 根据官方文档整理出来的一些参考信息，以及一些给编程新手的科普。可看可不看，主要是我自己没事瞄两眼用的。很多文档定稿之后代码又有大的改动，还没有做整体的更新，仅供参考。

要了解`arc-agi`这个游戏引擎库的话，还是需要以[官方文档](https://docs.arcprize.org/)为准捏。

做这玩意儿的起因是某天刷到一篇微信文章，介绍了这个号称让顶级大模型全部折戟沉沙的评测集，于是过来琢磨了一下。

官方提供一个在线试玩 Demo，不需要任何准备就可以玩，可以点[这里](https://arcprize.org/tasks/ls20)体验。

不过看了一下，好像没有找到很方便的本地游戏的办法，所提供的`pypi`包也是为了 Agent 所设计的，那作为好奇心重的人类玩家，又想在本地玩的话，怎么办呢。

于是稍稍花了点时间，用 TRAE 搓了个 `pygame-ce` 的壳子套上了（以及，才知道 `pygame` 居然也转生了），附加一些玩家档案切换等等的生活质量功能，于是就成了这个小项目。

没有特别琢磨过质量，就是能跑，自己玩着，感觉是有官方网页版的八成舒适度吧，就是UI糙了点，不过存档在本地，而且因为网络因素，也不像网页版玩着总感觉有点卡手。自觉还是不错的，这两天没事儿就打开来玩玩，也算捍卫一下自己人类的身份。

但说句实话，找各位 AI 研读了半天官方文档，这么做好像稍微有点不在官方的设计意图之内，这个库好像是纯粹为了给 Agent 打榜而设计的，但是我把它包起来给人玩儿了……

为了尽力避免不小心把哈基人的数据传到 Agent 英雄榜上，我试着做了一个安全防护：默认模式下，会在进入游戏之前跑一遍 loading，把所有游戏关卡缓存到本地，后面就是全部 OFFLINE 模式，不连官网了。

~~至少 AI 是这么跟我保证的 XD~~

当然作为这个库的本来设计意图，我们也在代码里留了一些适配 Agent 的设计，理论上只要稍稍补一点代码，就可以方便地接入官方设计的那几种 Agent Templates，然后就可以人机比拼了，但目前是没有实装的，因为主要是我自己瘾大，怎么让 Agent 玩这个有点复杂的小解谜，目前我也不是很懂哈哈。

不得不说，确实挺好玩的。也不怪 AI 全部挂掉了，这没有很强悍的原生视觉能力加上深度融合推理能力的话，确实白瞎，有些关我自己都得想好一会儿。

行了，不说废话了，如果你也是想体验一下游戏又觉得官方网页版有点不顺手，可以直接在这个库当中开一个 bash （我用的是 Git Bash，像什么 cmd 的话应该也行吧？拿不准的话可以让小 AI 帮忙把把关），然后直接启动（当然要先装一下pixi这个东西）：

```bash
pixi run game
```

然后应该就会拉起来一个 `pygame` 窗口了，目前只做了英文，反正看图也能玩，而且这个评测集有意思的地方就是官方刻意没有玩法说明，就是要看 AI 能不能自己“悟”出来的。

顺便一说，本人只在自己的 Windows 10 小笔记本上真正试玩过，其他平台的兼容性有劳各位大佬（和大佬们的 AI）摸索了🙏

> 2026年5月6日 14:31 周三，by Ash

