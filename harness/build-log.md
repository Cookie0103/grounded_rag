# 开发日志（build-log）

> **进度的唯一依据**：只记观察到的事实（命令、输出、提交），不记计划。计划在 [build/](build/)，决策原因在 [context/](context/)。
> 追加规则：下面「活动记录」只追加、不改写旧条目；阶段状态表可以改。每个阶段完成时必须有验收证据才能标「完成」。
> 第一版（Dify 文档问答，阶段 00～21）的日志在 [archive/v1-dify-docs/build-log.md](archive/v1-dify-docs/build-log.md)。

## 当前状态（先读这里）

最后更新：2026-11-18（阶段 31 完成公开语料采集和加载器）

- **方向**：项目改为「索尼银行住宅贷款坐席 Copilot」概念验证，见 [GOALS.md](../GOALS.md)、[PLANS.md](../PLANS.md)。
- **代码**：第一版文档已归档。五个 Compose 服务原生 arm64 并 healthy，kuromoji 已实测，网关的本机 Ollama 和 DeepSeek 两档都返回非零 token 用量。
- **分支**：当前本地 `2026-11-18-build-corpus`，从阶段 30 验收提交 `83ddae0` 建立。阶段提交留在本机。
- **第一版遗留**：阶段 21 的消融还有 251 份回答没评审，随第一版一起归档，不再继续。
- **模型**：意图档用 Qwen3 4B Instruct，20 条合成日文短题 19/20，P95 95.2 毫秒；嵌入和精排用 MPS；生成档用 DeepSeek V4 Pro。测量口径见[阶段 30](build/phase-30-cleanup-infra.md#小模型冒烟ac5)。
- **语料**：在可见 Chrome 中按清单保存 54 份 HTML，53 份符合住宅贷款范围。哈希、非空正文和新加载器已核验，公开原文位于本机忽略目录。
- **下一步**：继续[阶段 31](build/phase-31-corpus.md) 的元数据迁移、合成语料、入库和出题用语料包。
- **阻塞**：无。阶段 36 由作者出题、校准和跑封存测试集；公开页面保存和 Dify 界面操作由执行模型用 Chrome 完成。
- **提醒**：远程仓库是公开的。推送前确认没有带入公开页面原文和参考方案原文。

## 阶段状态

状态取值：未开始 / 进行中 / 阻塞 / 完成。「完成」表示验收标准已观察到，不是计划。

| 阶段 | 状态 | 说明 |
|---|---|---|
| [30 清场与基础设施](build/phase-30-cleanup-infra.md) | 完成 | 五个 ARM 容器正常，网关两档通过，465 个常规检查测试、32 个集成测试通过 |
| [31 语料与知识库加工](build/phase-31-corpus.md) | 进行中 | 已用可见 Chrome 保存 54 份公开页面；HTML、PDF、Markdown 加载器通过检查 |
| [32 检索](build/phase-32-retrieval.md) | 未开始 | |
| [33 模拟业务系统与工具层](build/phase-33-tools.md) | 未开始 | |
| [34 双泳道编排](build/phase-34-orchestration.md) | 未开始 | |
| [35 流式与护栏](build/phase-35-streaming-guard.md) | 未开始 | |
| [36 评测与回归门禁](build/phase-36-evaluation.md) | 未开始 | 需要作者出题、校准、跑测试集 |
| [37 Dify 对照](build/phase-37-dify-compare.md) | 未开始 | 界面操作由执行模型用浏览器完成 |
| [38 收尾](build/phase-38-wrapup.md) | 未开始 | |

## 活动记录（追加）

### 2026-11-18 · 第二版计划（分支 `2026-11-18-sony-pivot`）

模型：Claude Fable 5.2（只写计划，不改代码）。

- 作者要求把项目改造成贴近参考方案（坐席 Copilot：工具 + RAG、双泳道、Dify 到 LangGraph 的对照），业务背景换成索尼。作者确认四项：业务线为索尼银行住宅贷款；知识库与回答用日文；本地真搭 Dify 做对照；在本仓库原地替换。
- 核对远程：`git branch --merged origin/main` 显示全部 8 个本地分支都已并入 `origin/main`；`git diff --stat HEAD origin/main` 无输出（改动前的工作区与远程 main 内容相同）。`gh repo view` 显示仓库为 PUBLIC。
- 建本地标签 `v1-dify-docs` 指向 `origin/main`（`4ae48f3`），未推送标签。
- `.git/index.lock` 是 2026-11-16 留下的 0 字节残留文件，当时没有 git 进程在运行，已删除。
- 用 `git mv` 把第一版的 `harness/build/`、`harness/context/`、`harness/code_review/`、`harness/build-log.md`、`GOALS.md`、`PLANS.md` 移到 `harness/archive/v1-dify-docs/`（85 个文件）。
- 新写：`GOALS.md`、`PLANS.md`、`AGENTS.md`、本文件、阶段 30～38 共 9 个阶段文件、[决策记录](context/phase-30-pivot-context.md)。
- 语料来源调研（浏览器人工访问）：`https://sonybank.jp/robots.txt` 与非浏览器请求均返回 403；住宅贷款栏目侧栏约 35 个页面；FAQ 的住宅贷款分类为 `category=5314`，下有 5 个子类；[利用条件](https://sonybank.jp/guide/notice/10.html)只允许私人使用、禁止再分发。结论写进了 PLANS §3.1 的约束。
- 没有运行 `poe check`：本轮没有改动任何代码或配置。
- 同日作者补充三点并已写进计划：公开页面改由执行模型操作真实浏览器低速保存（限制见 PLANS §3.1），作者不手工保存；Dify 界面的导入与核对也交给执行模型；本机内存 32GB。作者确认可以出约 60 道规程题。相应修改了 `GOALS.md`、`PLANS.md`、`AGENTS.md`、阶段 31 与 37 的文件和决策记录。
- 按作者要求把本地分支 `2026-11-18-sony-pivot` 改名为 `2026-11-18-reopen`（改名前该分支从未推送，远程也没有同名分支）；上面两次文档提交随分支一起保留。

### 2026-11-18 · 跨机器交接阶段计划

- 将 `2026-11-18-reopen` 推送到 GitHub 并设置上游。首次推送后发现 `.gitignore` 的 `build/` 规则也匹配 `harness/build/`，阶段 30～38 的九份计划因此遗漏。
- 为 `harness/build/` 添加精确路径例外，并将九份原计划纳入版本控制。`git status` 确认九份计划均可见，`git check-ignore` 确认构建输出、`.env`、`data/` 和 `.cache/` 仍被忽略。逐份核对计划内容，未发现密钥、公开页面原文或参考方案原文。
- `uv run --locked --offline poe check` 通过：格式、lint、分层、类型检查通过，463 项单元测试通过。下一步仍是执行阶段 30。

### 2026-11-18 · 阶段 30 代码与 Mac 基础环境（分支 `2026-11-18-local-infra`）

- 归档第一版 README、导学与面经、评测资料和报告；按作者确认更新本机环境和阶段 37 完整同题回放范围。新增 ES、Redis、MySQL、LiteLLM Compose 规格，网关档位共用已有的 OpenAI 兼容调用、预算与计费路径。
- `docker info` 确认 Docker VM 已分配约 24 GiB；五个镜像的仓库清单均有原生 Linux arm64。Qwen3 嵌入和精排实际完成 MPS 推理，详细输出见 [Mac 环境记录](context/phase-30-mac-context.md)。
- 通过 `uv --no-config lock --check --offline`，不需要重新生成锁文件。在 `backend/` 忽略本机 uv 全局配置后，`uv run --locked poe check` 通过 465 个测试、覆盖率 94.93%；`uv run --locked poe test-int` 通过 32 个 PostgreSQL 集成测试。
- 阶段 30 仍在执行，容器与模型权重在下载；五服务健康、kuromoji 分词、两模型意图冒烟和网关真实调用待核验。

### 2026-11-18 · 阶段 30 验收

- `docker compose up -d --build --wait --wait-timeout 120` 成功，五个服务均 healthy，运行镜像均为 `linux/arm64`；`/_analyze` 实际返回 kuromoji 日文词元。各服务内存快照见[阶段文件](build/phase-30-cleanup-infra.md#记录)。
- 同样 4096 token 上下文下，两款 Ollama 候选分别串行跑 20 条合成日文短题。Qwen3 4B Instruct 19/20、P95 95.2 毫秒，Qwen2.5 7B 18/20、P95 128.4 毫秒。选定 4B，Ollama 报告 3.2 GB、100% GPU。
- `uv run --locked python -m scripts.phase_30_models --gateway` 成功，两档均 HTTP 200。DeepSeek V4 Pro 返回 14 输入、3 输出 token，保守记账 ¥0.000219。
- 阶段 30 的 AC1～AC7 已核验。本阶段提交仅在本地，下一步进入阶段 31。

### 2026-11-18 · 阶段 31 公开语料和加载器（分支 `2026-11-18-build-corpus`）

- 在可见 Chrome 中逐个打开 54 个清单 URL，另有一次 FAQ 动态渲染重试。原文、清单、保存时间和哈希留在本机 `data/raw/public/`。逐份核验 54 个文件，哈希一致且全部能提取正文。开户 FAQ 从住宅贷款入库范围标出。最短记录间隔 5.101 秒。
- 新增本地 HTML、PDF、Markdown 加载器并扩展切块器，已有第一版调用继续使用原来的默认长度。锁文件仅增加用于解析的依赖。使用忽略全局 uv 配置的 `uv run --locked poe check`，470 个测试通过，覆盖率 94.47%。
- 阶段 31 已勾选 T1、T3。出题用语料包要等合成语料、版本元数据和 S 档导出完成后交付。
