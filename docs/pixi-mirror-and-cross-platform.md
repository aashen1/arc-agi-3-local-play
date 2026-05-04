# Pixi 镜像配置与跨平台支持笔记

> 本文档记录了在为 ARC-AGI-3 Human Player 项目添加跨平台支持时，关于 pixi 镜像配置的调研结果和踩坑经验。

---

## 1. Pixi 配置优先级

Pixi 配置按优先级从高到低加载，**高优先级覆盖低优先级**：

| 优先级 | Windows 位置 | 说明 |
|--------|-------------|------|
| 6 | 命令行参数 `--tls-no-verify` 等 | 最高优先级 |
| **5** | **`项目目录\.pixi\config.toml`** | **项目级配置** |
| 4 | `%PIXI_HOME%\config.toml` | 全局配置（PIXI_HOME） |
| 3 | `%USERPROFILE%\.pixi\config.toml` | 全局配置（用户目录） |
| 2 | `%APPDATA%\pixi\config.toml` | 用户级配置 |
| 1 | `C:\ProgramData\pixi\config.toml` | 系统级配置 |

**关键点**：项目级配置（优先级 5/6）**高于**全局配置（优先级 3/4），会覆盖全局的 mirrors 设置。

---

## 2. Mirror 配置语法

### 基本格式

```toml
[mirrors]
"https://conda.anaconda.org/conda-forge" = [
    "https://mirrors.ustc.edu.cn/anaconda/cloud/conda-forge/",
    "https://conda.anaconda.org/conda-forge",
]
"https://conda.anaconda.org/bioconda" = [
    "https://mirrors.ustc.edu.cn/anaconda/cloud/bioconda/",
    "https://conda.anaconda.org/bioconda",
]
```

### 关键规则

1. **列表是有序的**：pixi 按列表顺序尝试镜像
2. **原始 URL 需要显式列出**：如果想回退到官方源，必须把官方 URL 也加进列表
3. **可以按 host 匹配**：`"https://conda.anaconda.org/" = [...]` 会匹配该 host 下所有 channel
4. **更长的前缀优先**：如果同时配置了 host 级和 channel 级镜像，channel 级优先

### PyPI 镜像

Mirror 配置也影响 uv 的 PyPI 解析和下载，但 PyPI 的 index URL 和下载 URL 不同，需要两条配置：

```toml
[mirrors]
"https://pypi.org/simple" = ["https://mirrors.ustc.edu.cn/pypi/web/simple"]
"https://files.pythonhosted.org/packages" = ["https://mirrors.ustc.edu.cn/pypi/packages"]
```

---

## 3. Mirror Fallback 行为（实测结论）

### 结论：pixi 支持 fallback，但仅限连接级失败

| 失败类型 | 是否触发 fallback | 实测验证 |
|---------|------------------|---------|
| DNS 解析失败 | ✅ 触发 | 用不存在的域名 `mirror-does-not-exist.invalid` 测试通过 |
| TCP 连接超时 | ✅ 触发 | 理论推断（与 DNS 失败同类） |
| HTTP 403 Forbidden | ❌ 不触发 | ustc 镜像对 linux-64 repodata 返回 302→bfsu→403，pixi 直接报错 |
| HTTP 404 Not Found | ❌ 不触发 | 同上，pixi 视为"镜像已响应" |
| 302 重定向后 403 | ❌ 不触发 | ustc 镜像 302 到 bfsu，bfsu 返回 403，pixi 不回退 |

### 官方文档原文

> You can configure mirrors for conda channels. We expect that mirrors are **exact copies** of the original channel.
> We attempt to fetch the repodata (the most important file) from the **first** mirror in the list.
> The repodata contains all the SHA256 hashes of the individual packages, so it is important to get this file from a **trusted** source.

关键词 "exact copies" 和 "trusted source" 暗示 pixi 的设计假设镜像要么完整可用，要么完全不可达。它没有处理"镜像可达但不完整"的场景。

### Fallback 的实际意义

1. **容灾**：主镜像宕机（DNS 失败、连接超时）时自动切换备用
2. **地域加速**：国内镜像优先，镜像挂了回退官方源
3. **不支持**"镜像可达但部分平台缺失"的回退

---

## 4. 国内镜像跨平台问题

### 问题根源

国内 conda 镜像站通常**只同步 win-64 平台的包**，对 linux-64、osx-64、osx-arm64 的 repodata 请求：

- **ustc 镜像**：返回 302 重定向到 `mirrors.bfsu.edu.cn`，bfsu 返回 403
- **tuna 镜像**：直接返回 403
- **bfsu 镜像**：返回 403

由于 pixi 对 HTTP 403 不触发 fallback，配置 `"ustc 镜像优先 + 官方源回退"` **无法解决跨平台 resolve 问题**。

### 实测记录

```
# pixi.toml: platforms = ["win-64", "linux-64", "osx-64", "osx-arm64"]
# .pixi/config.toml: ustc 优先 + 官方回退

❌ pixi install → 403 on linux-64 repodata (ustc → bfsu → 403, no fallback)
❌ pixi install → 403 on linux-64 repodata (tuna → 403, no fallback)
✅ pixi install → 成功 (直连官方源)
```

### OCI 镜像替代方案

pixi 支持 OCI registry 镜像，conda-forge 团队维护了一个 GHCR 镜像：

```toml
[mirrors]
"https://conda.anaconda.org/conda-forge" = [
    "oci://ghcr.io/channel-mirrors/conda-forge",
]
```

GHCR 镜像包含所有平台的包，但国内访问 ghcr.io 可能较慢或需要代理。

---

## 5. 当前项目的解决方案

### 项目级配置

`.pixi/config.toml`（项目级，优先级高于全局）：

```toml
[mirrors]
"https://conda.anaconda.org/bioconda" = ["https://conda.anaconda.org/bioconda"]
"https://conda.anaconda.org/conda-forge" = ["https://conda.anaconda.org/conda-forge"]
```

**强制使用官方源**，确保跨平台 resolve 正常。

### 为什么不用镜像优先 + 官方回退

因为国内镜像对非 Windows 平台返回 403（而非连接失败），pixi 不触发 fallback，resolve 直接报错。

### 全局配置不受影响

用户的全局 ustc 镜像配置仍然生效于其他项目。本项目通过项目级配置覆盖全局，只影响本项目。

### 国内用户加速方案

如果只使用 win-64 平台，可以删除 `.pixi/config.toml` 让项目继承全局镜像配置：

```bash
# 删除项目级配置，回退到全局 ustc 镜像
rm .pixi/config.toml
```

或者在 `pixi.toml` 中去掉非 Windows 平台：

```toml
platforms = ["win-64"]
```

---

## 6. pixi.toml 跨平台配置清单

### 需要修改的地方

```toml
# 1. 扩展平台列表
platforms = ["win-64", "linux-64", "osx-64", "osx-arm64"]

# 2. Python 版本下限由 arc-agi 决定（>=3.12）
python = ">=3.12,<3.15"
```

### 代码层面的跨平台适配

| 问题 | 修复方案 | 状态 |
|------|---------|------|
| Consolas 字体硬编码 | 改为 `"consolas,monospace"` 回退 | ✅ 已修复 |
| `pixi.toml` 仅 win-64 | 扩展为 4 平台 | ✅ 已修复 |
| Python 版本过高 | 放宽到 >=3.12 | ✅ 已修复 |
| 无 msvcrt / win32 API 依赖 | 代码本身跨平台 | ✅ 无需修改 |
| 路径使用 `os.path.join` | 已跨平台 | ✅ 无需修改 |

### 镜像配置文件

`.pixi/config.toml` 已加入版本管理（`.gitignore` 中 `!.pixi/config.toml` 排除了忽略规则），其他开发者 clone 后自动使用官方源。

---

## 7. 事故记录

### 2026-05-05：误清全局镜像配置

**起因**：添加跨平台支持后 `pixi install` 失败（ustc 镜像对 linux-64 返回 403）

**错误操作**：
```bash
pixi config unset mirrors --global  # ❌ 清空了全局镜像配置
```

**正确做法**：
```bash
pixi config set mirrors '...'  # ✅ 项目级配置，不加 --global
```

**恢复**：
```bash
pixi config set --global mirrors '{"https://conda.anaconda.org/conda-forge": ["https://mirrors.ustc.edu.cn/anaconda/cloud/conda-forge/"], "https://conda.anaconda.org/bioconda": ["https://mirrors.ustc.edu.cn/anaconda/cloud/bioconda/"]}'
```

**教训**：永远不要修改全局配置，用项目级配置替代。已写入 `.trae/rules/global-config-rule.md`。

---

## 8. 参考资料

- [Pixi Configuration 官方文档](https://pixi.sh/latest/reference/pixi_configuration/)（本地副本：`plgd/pixi_configuration.md`）
- [conda-forge GHCR 镜像](https://github.com/orgs/channel-mirrors/packages)
- 项目级配置文件：`.pixi/config.toml`
- 全局配置保护规则：`.trae/rules/global-config-rule.md`
