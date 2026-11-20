# 开发日志（build-log）

> **进度的唯一依据**：只记观察到的事实（命令、输出、提交），不记计划。计划在 [build/](build/)，决策原因在 [context/](context/)。
> 追加规则：下面「活动记录」只追加、不改写旧条目；阶段状态表可以改。每个阶段完成时必须有验收证据才能标「完成」。
> 第一版（Dify 文档问答，阶段 00～21）的日志在 [archive/v1-dify-docs/build-log.md](archive/v1-dify-docs/build-log.md)。

## 当前状态（先读这里）

最后更新：2026-11-20（作者委托的一次封存回放已完成，汇总已记录）

- **方向**：项目改为「索尼银行住宅贷款坐席 Copilot」概念验证，见 [GOALS.md](../GOALS.md)、[PLANS.md](../PLANS.md)。
- **代码**：第一版文档已归档。本机六个 Compose 服务原生 arm64 并 healthy，kuromoji 已实测，网关的本机 Ollama 和 DeepSeek 两档都返回非零 token 用量。
- **冻结**：本地标签 `copilot-freeze-2026-11-20` 指向 `fdd5a5eb16e9fb1e7a4e10e9fba9f7e6881cb4c0`。交接分支 `2026-11-20-project-handoff`。原调优候选 `f01605e`、还款修复 `4ea922b`。
- **第一版遗留**：阶段 21 的消融还有 251 份回答没评审，随第一版一起归档，不再继续。
- **模型**：意图档用 Qwen3 4B Instruct，20 条合成日文短题 19/20，P95 95.2 毫秒；嵌入和精排用 MPS；生成档用 DeepSeek V4 Pro。测量口径见[阶段 30](build/phase-30-cleanup-infra.md#小模型冒烟ac5)。
- **语料**：在可见 Chrome 中保存 54 份 HTML，53 份用于住宅贷款语料。S 档 185 篇、L 档 3,000 篇，两个存储均有 3,213 个规程块。出题包已校验，作者可以用本机 `.cache/policy-question-pack.zip` 开始准备阶段 36 的规程题。
- **检索**：`/retrieve` 已接通 ES 和 pgvector 的共同硬过滤，30 条日文冒烟的默认混合检索 S/L 均命中 30 条，P95 分别为 38.62/41.88 毫秒。默认关闭精排，仍可通过请求开关启用。
- **工具**：模拟业务已经以 MySQL 合成数据跑通，五个只读工具走同一鉴权、Redis、超时和裁剪链。真实联调保持坐席隔离，420 期返回 5 期并保留总数。
- **编排**：REST 与 MCP 已接入双泳道，客户查数转人工，坐席工具可与规程检索并行。Postgres 会话跨进程恢复已验证。阶段 34 的整段冒烟主意图 20/20。
- **流式**：SSE 已接入真实模型与 Redis 续推，入口日文脱敏和出口数字、引用检查均通过。预热串行 20 条合成冒烟，HTTP 首字 P95 2.346 秒，整段 P95 4.254 秒，撤回 0 条。冷态断线样例服务首字 5.231 秒，详见阶段 35。
- **评测**：阶段 36 合成开发 192 条已跑完。无注入 185 条首字 P95 2.217 秒，整段 4.290 秒；意图 124/128，已评分回归 175/185。附加 5% 条件 21 条，完整报告在 `.cache/copilot-eval/runs/mac-baseline/report.md`。
- **收尾**：纯合成干净目录从空库跑通迁移、生成、入库、API 和离线回归。最终本机 `poe check` 568 项、`poe test-int` 46 项，详见[阶段 38](build/phase-38-wrapup.md#记录)。现有数字汇总在 [Mac 本机实测报告](../docs/eval/mac-poc-report.md)。
- **Dify**：本机应用接口、模型、185 篇索引与 37 节点已验收。真实 API 串行配对 213 条，故障证据与网关用量完整。Dify 无注入意图 93.75%、首字 P95 4.841 秒、整段 P95 4.880 秒、平均 token 成本 ¥0.003356、回归 83.24%。对照与逐题分层证据见[阶段 37](build/phase-37-dify-compare.md#记录)。
- **规程校准**：20 条标签为「出题模型代标、作者确认」，与本机 Qwen2.5 7B Instruct 一致 16/20（80%），规程回答通过率及离线可采纳率为未测。原版 LangGraph 两档 Top5 为 22/37、过期命中 0/8，Dify S 档 42/42 同题配对，Top5 13/37，过期候选 4/8。
- **调优候选**：本地提交 `f01605e` 用新版日文分类和规程生成提示。S/L Top5 30/37、31/37，仍低于 85%。无注入合成回归维持 175/185，意图 124/128 降至 122/128。Dify 同一 42 条观察已与调优版 S 档重新离线配对。 [本机实测报告](../docs/eval/mac-poc-report.md)
- **转介修复**：`11ba76a` 的原三道还款困难题也是 0/3；`4ea922b` 修复后原题 3/3、新题 6/6、反向 6/6。最终候选实测回归 176/185、意图 122/128、规程 S/L 各 42 条，Top5 为 30/37、31/37。 [并排指标](../docs/eval/mac-poc-report.md#还款困难专门转介复测)
- **减税修复**：`fdd5a5e` 原题 9/9、新说法 18/18、一般减税规程 18/18，上一轮全部还款原题、新说法、反向对照也都通过三遍。
- **全量同日续跑**：同一候选合成 185/185、规程 S/L 各 42。合成回归 177/185、意图 122/128，规程 S/L Top5 为 30/37、31/37，过期命中均 0/8。 [并排实测](../docs/eval/mac-poc-report.md#个人减税修复后的全量回归)
- **交接**：冻结代码在[草稿 PR #3](https://github.com/Cookie0103/grounded_rag/pull/3)，复盘文档在[草稿 PR #4](https://github.com/Cookie0103/grounded_rag/pull/4)。代码 PR 的 Linux 常规与集成检查均已通过。文件索引、实测和换机资料见 [交接与复盘](../docs/retrospective/README.md)。
- **封存**：作者委托独立出题、审题与执行。固定版 S/L 各 16 条，共 32 条，Top5 均 6/13，过期候选或引用均 0/2。首字 P95 分别 4.858 和 1.432 秒。账本增加 ¥1.08514771，累计 ¥12.88240589。临时上限已撤回，默认 ¥10。 [封存实测和口径](../docs/eval/mac-poc-report.md#冻结版一次封存回放)
- **未测**：评审校准为 16/20，正式规程回答通过率、离线可采纳率仍为未测。线上业务指标仍为未测。
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
| [36 评测与回归门禁](build/phase-36-evaluation.md) | 阻塞 | 一轮开发调优及一次封存回放已实测，正式答复评分校准未达门槛 |
| [37 Dify 对照](build/phase-37-dify-compare.md) | 阻塞 | 213 条合成、42 条规程配对均完成；正式规程回答评分未测 |
| [38 收尾](build/phase-38-wrapup.md) | 完成 | 已冻结并记录四项实测退步、一次封存汇总和已知限制 |

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

### 2026-11-18 · 阶段 36 合成评测（分支 `2026-11-18-copilot-evaluation`）

- 生成 240 条日文合成用例，分 192 开发、48 保留，校验 0 个错误；查数金标来自现有种子程序。已向作者提请独立规程开发集，校准说明和封存运行手册已写好。
- 预热后真实串行回放 192 条，另跑 21 条固定种子 5% 超时。`evaluate_copilot --resume --merge-fault-run` 复用已有观察汇总 213 条。无注入意图准确率 96.88%，首字 P95 2.217 秒、整段 P95 4.290 秒，回归 94.59%，失败归因见[阶段 36](build/phase-36-evaluation.md#记录)。
- 离线 CI 假模型门禁 14/14；`poe check` 552 项与 `poe test-int` 46 项通过。正式规程评分、S/L 召回对照、人工校准和封存均待作者，继续部署 Dify 的独立工作。

### 2026-11-18 · 阶段 37 本机 Dify 部署（分支 `2026-11-18-dify-comparison`）

- 官方 Dify 1.19.0 以独立 `grounded_dify` 启动，容器实际架构原生 arm64，安装页 HTTP 200。Dify 代理访问同一网关和 mock 服务通过，拦截了未经许可的端口及模拟业务 POST。Docker 和节点证据见[阶段 37](build/phase-37-dify-compare.md#记录)。
- 统一 MPS 嵌入和网关用量实际通过，两条 1024 维向量和非零 token。37 节点 YAML 通过官方模型校验和 6 条替身执行，Dify 回放适配的 213 条 LangGraph 基线已能匹配。
- 已把本机专用测试管理员初始化表单留在 Chrome。自动审批拒绝通过临时网页传递 `.env` 凭据，未执行该动作。按要求等待本机登录后继续知识库、画布、截图与真实对照，不填 Dify 未测数据。
- `poe check` 565 项通过，`poe test-int` 46 项通过。回放脚本、原生 Compose 覆写和节点说明就绪；继续可独立完成的收尾工作。

### 2026-11-18 · 阶段 38 本机复现与收尾（分支 `2026-11-18-local-wrapup`）

- 在干净临时目录用独立 Compose 从空库开始。合成 S 档 3 篇、L 档 12 篇，双库各 12 个块。实际 API 能按日期在 v1/v2 间切换，规程 SSE 引用有效，坐席工具从 420 期裁到 5 期，离线样例 14/14。完整命令与本机日志见[阶段 38](build/phase-38-wrapup.md#记录)。
- `uv run --locked poe check` 568 项通过，覆盖率 90.18%；`uv run --locked poe test-int` 46 项通过。本机验证了离线 CI 评测命令。手册与规范已更新，7 对旧上游 MDX 夹具已改为带标记的合成样例，清洗与切块定向检查均为 71 项通过。
- `uv run --locked python -m scripts.audit_release` 核对了 109 条相对链接、29 个配置字段和 518 个跟踪路径，检查规则命中 0 项。临时复现栈已停止，主 Compose 六服务 healthy，正常模式 Copilot API `/health` 返回应用、数据库均正常。
- [Mac 本机实测报告](../docs/eval/mac-poc-report.md) 中 7 组数字已回查原始观察。合成开发回归为 94.59%，Dify 真实回放和正式 S/L 配对未测。Dify 本机安装仍为 `not_started`，等待作者初始化测试管理员；封存测试集及原始输出由作者保管。

### 2026-11-19 · 阶段 37 本机控制台续办（分支 `2026-11-19-dify-console`）

- 作者已完成测试管理员初始化。`GET /console/api/setup` 为 `finished`，主 Compose 六服务仍 healthy。Chrome 显示官方兼容模型插件 0.0.84 安装完成。
- Chrome 通过 macOS 原生选择器导入 37 节点模板，页面显示「应用已创建」。Dify 整图导出保存在 `.cache/dify-evidence/imported-workflow.png`。
- 185 篇 S 档文件经本机页面上传，进入分段表单，首文档实际预览 6 个块。高质量索引和混合检索 Top 5 已选，尚未开始嵌入处理。两个 Chrome 页面保留给后续配置。真实回放仍未测。
- `uv run --locked poe check` 568 项通过，覆盖率 90.18%；`uv run --locked poe test-int` 46 项通过。模拟服务的故障开关已恢复默认值。

### 2026-11-19 · 阶段 37 网关表单预填

- `docker exec grounded_dify-plugin_daemon-1 …` 核对官方插件 0.0.84 的嵌入接口追加 `/embeddings`。三个 Chrome 表单已统一填 `http://gateway:4000/v1`，按 `small`、`deepseek-v4-pro`、`qwen3-embedding-0.6b` 分别准备。
- 本机粘贴在自动化端未进入密码栏，三个表单均未提交。已请作者只在实际本机 Dify 表单填写。今日预算检查结果为已记账 ¥0、上限 ¥10，没有触发 DeepSeek 配置验证调用。

### 2026-11-19 · 阶段 37 Dify 索引、画布和真实冒烟

- 作者配置好三档网关模型。官方 OpenAI 兼容插件已启用，网关回调验证两档聊天用量。Chrome 观察到 185/185 篇完成索引，失败 0。知识库及两个节点持久化 0.7/0.3 的混合权重与 Top 5。
- 修复编辑器拒绝的分类条件和知识库占位引用。Chrome 发布检查无问题，应用已在本机发布。应用包核对 37 节点、同一知识库和五个正确聊天模型节点。本机证据 ZIP 包含 37 张逐节点截图、其余界面截图和配置差异，共 44 项。
- 用 Chrome 真实运行合成坐席查数与规程问答。查数结果吻合金标，规程答案有引用。配置验证及两项预览共计 ¥0.01492128，完整对照仍待本机应用服务 API 开通。
- `uv run --locked poe check` 568 项通过，覆盖率 90.18%；`uv run --locked poe test-int` 46 项通过；本机模拟服务恢复默认故障开关。

### 2026-11-19 · 阶段 37 创建本机回放密钥

- 作者确认创建，在本机 Dify 应用控制台生成一把专用 API 密钥，弹窗仍开着。浏览器复制后的项目剪贴板指纹核对未通过，自动审批拒绝从数据库直接提取。项目 `.env` 没有被修改，已请作者从实际弹窗复制到项目配置。
- 对照回放参数已和 `scripts.compare_dify --help` 核对，LangGraph 两个运行目录分别有 192 与 21 条观察，运行手册补齐串行同题、随机故障和合并报告步骤。

### 2026-11-19 · 阶段 37 Dify API 和同题回放验收

- 作者把本机应用密钥加到 `.env`，指纹一致，应用 API 返回 HTTP 200。修正 Dify 在 `message_end` 后交付 `workflow_finished` 时漏读终态的问题，仍用答复结束事件计整段耗时。定向 12 项通过，问候和规程真实 API 验证的终态、分类与网关用量均完整。
- 首轮代理日志两条 `TCP_REFRESH_FAIL_OLD/200`，随后限定在模拟业务域名及端口禁用代理缓存。同一 GET 路径探查 200、503、200，POST 403。第二轮代理日志未新增缓存命中或重验证。故障模拟已恢复默认。
- 第二轮 `scripts.compare_dify --resume` 与 `--report-only --merge-fault-run` 实际配对 213/213 条，其中无注入 185、指定故障 7、随机超时 21。Dify 无注入首字 P95 4.841 秒，回归 154/185。无注入平均成本 ¥0.003356，整组实记 ¥0.72425232，当日账本 ¥1.50703027。详见[同题结果](../docs/eval/mac-poc-report.md#s-档同题对照)。
- `uv run --locked poe check` 571 项通过，覆盖率 90.21%；`uv run --locked poe test-int` 46 项通过。真实合成断线探查同会话返回新消息，API 历史读取 200。正式题、作者校准及封存结果保留未测。

### 2026-11-19 · 阶段 36 正式规程开发题与盲标（分支 `2026-11-19-policy-calibration`）

- `validate_cases(scope="policy-dev")` 再核对 42 题和出题包文档 ID，8 道版本陷阱、5 道不可回答，问题 0。出题 Claude Fable 5.2，审题 Claude Sonnet 5.5，同厂商不同模型。
- 恢复并实测 Ollama 4096 token 上下文后，`scripts.evaluate_copilot --policy-dev … --prepare-calibration --warmup 2` 实际跑完 S/L 共 84 条，费用 ¥1.39892227。两档 Top5 均为 22/37，过期命中均为 0/8。先前默认长上下文的 35 条留作诊断，未用于汇总。
- 评审命令待指定。使用现有脚本的抽样口径独立生成 20 条盲标和空白标注文件，并与原始答复逐条核验。作者交接汇总在本机 `.cache/copilot-dev/calibration-summary.md`。按作者要求暂停评测，等待其人工标注。 [阶段 36](build/phase-36-evaluation.md#记录)
- `uv run --locked poe check` 为 571 项通过，覆盖率 90.21%。文档审计检查 121 条相对链接，问题 0 项，盲标与空表各 20 行。本次提交只改报告与日志。

### 2026-11-19 · 阶段 36 本机独立评审（分支 `2026-11-19-policy-calibration`）

- 作者指定本机 Ollama Qwen2.5 7B Instruct（`qwen2.5:7b`，权重指纹 `845dbda0ea48`）。`scripts.evaluate_copilot --resume --prepare-calibration --judge-command …` 读取 84 条既有答复，从 S 档抽取 20 条规程样本。首轮普通 JSON 在第 12 条返回非法要点标签，11 条已输出的诊断记录另存。改用 Ollama JSON Schema 约束字段类型、允许的标签和要点标签数后，原样传入既有评审提示，沿用既有评分规则，重跑 20 条。
- 核对 20/20 条机器标签合法并与原盲标的题目、日期、金标文档和回答逐条对应。原盲标 SHA-256 一致，84 条缓存答复逐字节一致。没有读取或修改人工标注表。DeepSeek 当日账本仍为 ¥3.45690893，本轮增加 ¥0。机器标签与人工作业分别保存在本机，汇总已更新。
- `uv run --locked poe check` 571 项通过，覆盖率 90.21%。`uv run --locked python -m scripts.audit_release` 核查 121 条相对链接，问题 0 项。等待作者独立标注，正式评审一致率和离线可采纳率仍为未测。

### 2026-11-19 · 规程校准与 Dify 回放（分支 `2026-11-19-policy-tuning`）

- 将作者确认的盲标与机器标签按 ID 一一配对。来源为「出题模型代标、作者确认」。`load_calibration` 为 16/20（80%），其中双方都判可采纳 7 条、都判不可采纳 9 条，两个分歧方向各 2 条。正式规程回答通过率和离线可采纳率为未测。复核 11 条拒答的原始轨迹得到 8 条个人业务转人工、3 条数字溯源护栏拦截。分歧分析见[阶段 36](build/phase-36-evaluation.md)。
- 启动本机 MPS 嵌入后，`scripts.compare_dify --policy-dev … --warmup 2` 输出 Dify 42/42 条同题配对，网关记录无缺失。S 档 Dify Top5 13/37，过期候选 4/8，首字 P95 6.626 秒，整段 6.664 秒。42 条实记 ¥0.23384592，含预热账本增量 ¥0.24142061。 [阶段 37](build/phase-37-dify-compare.md)

### 2026-11-19 · 一轮开发集调优验收（分支 `2026-11-19-policy-tuning`）

- 保存日文 `intent_v2.md` 与 `generate_policy_v2.md`，受测内容固定为 `f01605e`。`scripts.evaluate_copilot --policy-dev … --port 18083` 实测 84 条；两档 Top5 从各 22/37 变为 30/37、31/37，过期命中仍各 0/8。S 档旧校准中 8 条误转人工有 5 条改为带引用回答。旧 3 条数字护栏拒答仍拦截。规程回放成本为 ¥1.97708861。
- 无注入合成开发回放遇到 HTTP 429 后，按原限流以 2.05 秒请求间隔续跑，最终取得 185 条，费用 ¥2.36967034。回归仍是 175/185，意图降到 122/128，调优版首字/整段 P95 为 1.975/4.734 秒。用 `scripts.compare_dify --report-only --langgraph-run …/policy-v2` 复用 Dify 原始观察得到 42/42 配对。所有回放和预热的当日累计账本为 ¥8.04508848，本轮增量 ¥4.58817955。 [调优与对照表](../docs/eval/mac-poc-report.md#langgraph-一轮开发集调优)
- `uv run --locked poe check` 571 项通过，覆盖率 90.22%；`uv run --locked poe test-int` 46 项通过，模拟故障头恢复默认关闭；离线回归 14/14。静态审查发现专门窗口转介仍待核验，保留为本地候选。封存由作者在版本冻结后运行。
- `uv run --locked python -m scripts.audit_release` 核对 135 条相对链接和 520 个跟踪路径，发现 0 项。临时调优 API 已停止，原 API 的健康检查为 HTTP 200，六个主 Compose 服务均 healthy。

### 2026-11-20 · 冻结前实测（分支 `2026-11-20-freeze-review`）

- 受测运行文件与 `f01605e` 一致，`.cache/copilot-dev/pre-freeze-check/run.py` 在真实本机 SSE 回放 8 条日文合成样例。个人减税 3/3 引导专业税务渠道；还款困难 0/3 到达专门咨询路径，其中两条给通用联系渠道、一条按投诉升级。两条一般规程对照完成检索。八条均有终态，工具调用或撤回均为 0，本轮账本增量 ¥0.16197667。
- `uv run --locked poe check` 571 项通过，覆盖率 90.22%。停止临时候选 API 后，原 API HTTP 200 和六个 Compose 服务 healthy。冻结条件未满足，保留候选且封存未运行。 [阶段 38](build/phase-38-wrapup.md#记录)

### 2026-11-20 · 还款困难转介修复与全量回归

- 隔离的 `11ba76a` 重跑原还款困难三题得到 0/3，与 `f01605e` 的两条规程、一条投诉路径一致。还款困难为原有合规缺口。保留原有意图和生成提示及检索设置，在输入护栏后加专门转介。独立代码审查提出的 4 个误转和漏转反例补入单元测试，在 `4ea922b` 验证通过。本轮是合规修复。
- `smoke.py fixed 18083 --reviewed` 原还款题 3/3、修正前固定的另一批新说法 6/6、反向对照 6/6。个人减税仍为 1/3，三条均未进入新增分支；未改动的 `f01605e` 同日隔离复跑为 2/3。按要求保留减税原逻辑，未创建冻结标签，未运行封存集。
- `run-full.zsh` 完整回放 84 条规程与 185 条合成开发观察。合成回归 175/185 → 176/185，意图 122/128 保持；规程 S/L Top5 30/37、31/37 保持，L 档首字和平均成本较旧实测上升。详细证据在本机 `.cache/copilot-dev/repayment-fix/`。当日累计账本 ¥5.91292310，低于 ¥10。 [本机指标](../docs/eval/mac-poc-report.md#还款困难专门转介复测)
- `uv run --locked poe check` 587 项通过，覆盖率 90.24%；`uv run --locked poe test-int` 46 项通过。故障设置恢复，原 API HTTP 200，主 Compose 六服务 healthy，临时 API 已停止。

### 2026-11-20 · 个人减税最后一项合规修复

- 逐条核对 3 个旧失败，2 条漏专业渠道，1 条因 `missing_citation` 撤回成通用拒答，未出现替客户判定的资格或金额。S 档本机资料仅核实税务署，新的个案转介和撤回兜底共用固定日文话术。首候选 `5716cfb` 在独立审查后按问句收紧边界，阶段文件保留两次锁题摘要和四个反例修复记录。 [阶段 38](build/phase-38-wrapup.md#记录)
- 候选 `fdd5a5e` 取得 132 条三遍专项观测，75/75 触发相应的固定转介，57/57 一般手续或投诉按原路径处理。`poe check` 602 项、`poe test-int` 46 项通过。完整开发回放按限流和已有日预算账本进行。
- 当日账本增至 ¥9.40424602 时，开发回放按预留安全余量退出，合成 163/185 观察已落盘，规程尚未开始。临时候选 API 已停，原 API HTTP 200，模拟故障头为 `false`。复用 `.cache/copilot-dev/tax-referral/` 下的已落盘观察跨日续跑；本次没有读取或运行封存集。

### 2026-11-20 · 作者授权同日完成全量回放

- 2026-11-20 作者授权当日上限临时放宽到 ¥25。已取消等待换日的进程。临时上限仅作用于本机候选 API 和回放进程，账本继续记录。续跑 22 条合成和 84 条规程，首 163 条已保存结果的 SHA-256 一致。起始账本 ¥9.40424602、实际续跑增加 ¥2.39301216（22 条 ¥0.41635123、84 条 ¥1.97666093），当日合计 ¥11.79725818。进程退出后核验默认上限 ¥10，`.env` 指纹一致。
- 合成回归 176/185 至 177/185，意图、规程 S/L Top5 和过期命中持平。合成整段 P95 与平均成本升高，S 档首字和整段 P95 升高。按作者条件保留候选，不打冻结标签，等待确认。 [完整实测](../docs/eval/mac-poc-report.md#个人减税修复后的全量回归)

### 2026-11-20 · 作者确认冻结

- 作者接受四项实测变化，停止调优。`git rev-parse 'copilot-freeze-2026-11-20^{commit}'` 核对本地标签精确指向 `fdd5a5eb16e9fb1e7a4e10e9fba9f7e6881cb4c0`。受测代码保持该版本，后继提交记录交接资料。 [并排实测](../docs/eval/mac-poc-report.md#个人减税修复后的全量回归)
- 独立读取应用配置与预算账本，默认上限为 ¥10，当日已记 ¥11.79725818。作者授权 2026-11-20 封存运行的临时上限为 ¥20。该覆盖由作者运行时设置，到当日东京时间午夜失效。实际封存花费待作者发回汇总；本次冻结没有付费调用。

### 2026-11-20 · 冻结代码 PR 与换机资料

- 作者授权分开提交代码和资料。`2026-11-20-project-handoff` 推至 `origin`，以 `main` 为目标创建[草稿 PR #3](https://github.com/Cookie0103/grounded_rag/pull/3)。冻结标签留在本机。复盘资料分支基于该远程分支，方便单独审查文档差异。
- 冻结时重跑 `UV_NO_CONFIG=1 UV_OFFLINE=1 uv run --locked poe check`，602 项通过，覆盖率 90.47%。46 项集成测试及 132 条专项是同一受测提交的实测记录。
- GitHub 首轮 `check` 和 `integration` 均发现普通依赖环境缺 NumPy。`bd1c826` 仅修 CI 的安装步骤，使用锁文件已有的 NumPy 2.5.4，保留原检查。在干净无 GPU 环境执行 `uv run --locked --no-sync poe check` 602 项通过，离线回归 14/14。用 `git diff --exit-code fdd5a5e -- backend mock_core infra docker-compose.yml .env.example` 确认受测文件一致。 [首轮 CI 证据](https://github.com/Cookie0103/grounded_rag/actions/runs/44668864803)
- 将同题指标、模型和节点耗时、踩坑记录、换机流程、历史阶段索引与作者封存命令汇到 [交接与复盘](../docs/retrospective/README.md)。本机 `.cache/handoff-2026-11-20/development-metrics.zip` 收拢 8 份聚合结果，文件哈希和 ZIP 完整性均已核对。原始证据保留原路径，未读取封存题，未追加评测调用。
- GitHub 核对代码 PR 的 `check` 和 `integration` 均成功，后者 46 项通过。另创建交接草稿 PR，比较基线为 `2026-11-20-project-handoff`，GitHub 文件列表共 6 份 Markdown。 [代码 PR 的 Linux CI](https://github.com/Cookie0103/grounded_rag/actions/runs/44669384106) · [交接文档 PR #4](https://github.com/Cookie0103/grounded_rag/pull/4)

### 2026-11-20 · 作者委托完成封存

- 作者委托在新建的仓库外私有目录准备题目并代跑。独立出题和审题后，16 道题通过 `policy-test` 校验，其中 10 道公开规程、6 道合成、3 道不可回答、2 道版本陷阱。初稿曾因场景重复退回，所有调整都在首次回放前完成。题目和逐题答复留在本机私有目录。 [题集来源和摘要](context/phase-36-evaluation-context.md#2026-11-20--作者委托一次封存回放)
- 从 `backend/` 执行 `uv run --locked --no-sync python -m scripts.evaluate_copilot --sealed-test … --run-dir … --port 18083 --commit fdd5a5eb16e9fb1e7a4e10e9fba9f7e6881cb4c0 --calibration ../.cache/copilot-dev/author-calibration-paired.jsonl`，退出码 0。S/L 两档各 16 条终态，观测和评分记录分别共 32 条，无续跑。两档 Top5 均 6/13、过期均 0/2。S/L 首字 P95 为 4.858/1.432 秒、整段 P95 为 8.118/4.494 秒。答复正式评分和离线可采纳率因校准未达门槛保留未测。 [封存聚合指标](../docs/eval/mac-poc-report.md#冻结版一次封存回放)
- 2026-11-20 封存按作者授权使用 ¥20 进程临时上限。原预算账本由 ¥11.79725818 增至 ¥12.88240589，增量 ¥1.08514771。退出临时 API，验证 `18083` 无监听，独立进程读取默认 ¥10。`git diff --exit-code` 核对受测文件与冻结版一致。`UV_NO_CONFIG=1 UV_OFFLINE=1 uv run --locked --no-sync poe check` 602 项通过，覆盖率 90.47%。本次交付汇总在本地 `2026-11-20-sealed-results`。
