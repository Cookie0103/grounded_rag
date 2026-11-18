# 开发日志（build-log）

> **进度的唯一依据**：只记观察到的事实（命令、输出、提交），不记计划。计划在 [build/](build/)，决策原因在 [context/](context/)。
> 追加规则：下面「活动记录」只追加、不改写旧条目；阶段状态表可以改。每个阶段完成时必须有验收证据才能标「完成」。
> 第一版（Dify 文档问答，阶段 00～21）的日志在 [archive/v1-dify-docs/build-log.md](archive/v1-dify-docs/build-log.md)。

## 当前状态（先读这里）

最后更新：2026-11-18（阶段 35 验收，出题包可用）

- **方向**：项目改为「索尼银行住宅贷款坐席 Copilot」概念验证，见 [GOALS.md](../GOALS.md)、[PLANS.md](../PLANS.md)。
- **代码**：第一版文档已归档。本机六个 Compose 服务原生 arm64 并 healthy，kuromoji 已实测，网关的本机 Ollama 和 DeepSeek 两档都返回非零 token 用量。
- **分支**：阶段 35 在本地 `2026-11-18-streaming-guards` 验收。阶段提交留在本机。
- **第一版遗留**：阶段 21 的消融还有 251 份回答没评审，随第一版一起归档，不再继续。
- **模型**：意图档用 Qwen3 4B Instruct，20 条合成日文短题 19/20，P95 95.2 毫秒；嵌入和精排用 MPS；生成档用 DeepSeek V4 Pro。测量口径见[阶段 30](build/phase-30-cleanup-infra.md#小模型冒烟ac5)。
- **语料**：在可见 Chrome 中保存 54 份 HTML，53 份用于住宅贷款语料。S 档 185 篇、L 档 3,000 篇，两个存储均有 3,213 个规程块。出题包已校验，作者可以用本机 `.cache/policy-question-pack.zip` 开始准备阶段 36 的规程题。
- **检索**：`/retrieve` 已接通 ES 和 pgvector 的共同硬过滤，30 条日文冒烟的默认混合检索 S/L 均命中 30 条，P95 分别为 38.62/41.88 毫秒。默认关闭精排，仍可通过请求开关启用。
- **工具**：模拟业务已经以 MySQL 合成数据跑通，五个只读工具走同一鉴权、Redis、超时和裁剪链。真实联调保持坐席隔离，420 期返回 5 期并保留总数。
- **编排**：REST 与 MCP 已接入双泳道，客户查数转人工，坐席工具可与规程检索并行。Postgres 会话跨进程恢复已验证。阶段 34 的整段冒烟主意图 20/20。
- **流式**：SSE 已接入真实模型与 Redis 续推，入口日文脱敏和出口数字、引用检查均通过。预热串行 20 条合成冒烟，HTTP 首字 P95 2.346 秒，整段 P95 4.254 秒，撤回 0 条。冷态断线样例服务首字 5.231 秒，详见阶段 35。
- **下一步**：按[阶段 36](build/phase-36-evaluation.md) 建日文评测用例、指标报告、离线门禁和作者运行说明。
- **阻塞**：无。阶段 36 由作者出题、校准和跑封存测试集；公开页面保存和 Dify 界面操作由执行模型用 Chrome 完成。
- **提醒**：远程仓库是公开的。推送前确认没有带入公开页面原文和参考方案原文。

## 阶段状态

状态取值：未开始 / 进行中 / 阻塞 / 完成。「完成」表示验收标准已观察到，不是计划。

| 阶段 | 状态 | 说明 |
|---|---|---|
| [30 清场与基础设施](build/phase-30-cleanup-infra.md) | 完成 | 五个 ARM 容器正常，网关两档通过，465 个常规检查测试、32 个集成测试通过 |
| [31 语料与知识库加工](build/phase-31-corpus.md) | 完成 | S 185 篇、L 3,000 篇，双库 3,213 块，出题包已校验 |
| [32 检索](build/phase-32-retrieval.md) | 完成 | 双库硬过滤、精确编号、降级与四模式冒烟已实测 |
| [33 模拟业务系统与工具层](build/phase-33-tools.md) | 完成 | 五个只读工具联调，合成数据指纹及 420 期裁剪已核验 |
| [34 双泳道编排](build/phase-34-orchestration.md) | 完成 | 双图、进程重启恢复、20 条真模型节点耗时已验收 |
| [35 流式与护栏](build/phase-35-streaming-guard.md) | 完成 | 50 个 Redis 续推断点、HTTP 首字和整段、日文护栏已核验 |
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

### 2026-11-18 · 阶段 31 语料与入库验收

- `uv run --locked poe build-policies --as-of 2026-11-18` 生成 132 篇内部合成规程和 2,815 篇干扰文档，加 53 篇公开资料，共 3,000 篇。36 个版本组和 24 期带标记的架空月度通知通过清单校验。
- 开发库迁移至 0006；使用 MPS 嵌入并同步 kuromoji。两库均 3,213 块，规程块必填元数据缺失为 0，重复导入新增和重新嵌入均为 0。历史日期与现行日期的发布案例通过双库断言。
- `uv run --locked poe check` 为 462 个测试通过、覆盖率 92.77%；`uv run --locked poe test-int` 为 34 个通过。阶段证据见[阶段 31](build/phase-31-corpus.md#记录)，版本与同步选择见[语料决策](context/phase-31-corpus-context.md)。
- S 档出题包 `.cache/policy-question-pack.zip` 已验证。作者可以提前准备 40 道开发题和 20 道封存测试题，保留金标文档 ID 和必要的查询日期。公开来源快照和出题包留在本机。

### 2026-11-18 · 阶段 32 检索验收

- 用 `MetaFilter` 统一 pgvector、ES 和候选回读。20 组集成过滤的块 ID 完全一致。真实 API 请求以旧日期和当天分别命中指定 v1/v2，关闭精排时延迟保持检索级。
- `uv run --locked poe compare-retrieval` 在 S/L 各跑 30 条日文冒烟。默认混合时各 30/30、P95 38.62/41.88 毫秒，启用精排各 27/30、P95 1964.51/1993.04 毫秒。所有模式未出现失效候选。详细表与指令对照见[阶段 32](build/phase-32-retrieval.md#记录)，结论只覆盖本次冒烟样本。
- `uv lock --check` 解析 172 个包，`uv run --locked poe check` 通过 445 个测试，覆盖率 92.46%；`uv run --locked poe test-int` 通过 34 个测试。退役关键词代码和专属测试已归档。

### 2026-11-18 · 阶段 33 模拟业务与工具验收（分支 `2026-11-18-mock-tools`）

- `MOCK_ALLOW_FAULT_HEADERS=true docker compose up -d --build --wait db es redis mock_core` 启动成功，模拟业务镜像为 `linux/arm64`，六个运行服务均 healthy。MySQL 合成种子两次生成和数据库导出的指纹一致，覆盖 300 个客户、20 个坐席及六种指定业务边界。
- 联调五个只读接口、越权拦截、坐席缓存隔离和字段白名单。420 期样本保留 `total=420`，裁剪至 5 期，离线编码从 21,626 降为 318 token。注入超时和 5xx 返回安全的失败状态，本机分别耗时 2,002.32 和 11.96 毫秒。
- `uv run --locked poe check` 通过 471 项，覆盖率 92.29%；`uv run --locked poe test-int` 通过 40 项；`mock_core` 独立测试 10 项通过。逐项证据见[阶段 33](build/phase-33-tools.md#记录)。

### 2026-11-18 · 阶段 34 双泳道验收（分支 `2026-11-18-dual-orchestration`）

- `uv run --locked alembic upgrade head` 将开发库迁移到 0007，旧表行数为 0。官方 Postgres checkpointer 在被终止的进程之后由新进程恢复最新状态。新图替换实际 API、MCP 和评测适配，旧编排和专用测试归档，原严格模式评审提示词保留。
- 本机小模型 JSON 分类与函数调用实测成功，`logprobs` HTTP 400，调用侧省略该参数。本机 `.env` 改用同一网关，密钥与预算沿用。
- 最终 `uv run --locked python -m scripts.phase_34_smoke` 发 20 条合成请求，主意图 20/20，整段 P95 3,875.82 毫秒，生成 P95 3,625.99 毫秒，账本增量 ¥0.26423971。节点分解见[阶段 34](build/phase-34-orchestration.md#记录)，本机详情为 `.cache/phase-34-orchestration-smoke.json`。
- `uv run --locked poe check` 通过 450 项，覆盖率 91.36%；`uv run --locked poe test-int` 通过 39 项。锁文件增加四个会话持久化依赖，未改动全局 uv 配置。

### 2026-11-18 · 阶段 35 流式与护栏验收（分支 `2026-11-18-streaming-guards`）

- 真实 HTTP 在第 5 个事件断开，同一个响应随后续推到终态，客户端拼接逐字一致。Redis 集成验证 50 个伪随机断点、重叠去重、心跳和 120 秒终态保留策略，HTTP 验证过期返回 410。
- 入口以日文占位符遮蔽个人信息并拦截注入，模型片段发出后检查完整答复，失败时发撤回事件。定向用例验证了无来源金额、无效引用、违规承诺的拦截与替换。
- `uv run --locked python -m scripts.phase_35_smoke --port 18080` 在 Mac 上预热后串行取得 20 条样例。HTTP 首字 P95 2,346.03 毫秒，整段 P95 4,253.60 毫秒，11 条实际生成，0 次撤回，账本增量 ¥0.26378352。冷态样例和节点分解见[阶段 35](build/phase-35-streaming-guard.md#记录)。
- `uv run --locked poe check` 通过 530 项，覆盖率 91.56%；`uv run --locked poe test-int` 通过 46 项。本机流式 API 用于后续评测。
