# 开发日志（build-log）

> **进度的唯一依据**：只记观察到的事实（命令、输出、提交），不记计划。计划在 [build/](build/)，决策原因在 [context/](context/)。
> 追加规则：下面「活动记录」只追加、不改写旧条目；阶段状态表可以改。每个阶段完成时必须有验收证据才能标「完成」。
> 第一版（Dify 文档问答，阶段 00～21）的日志在 [archive/v1-dify-docs/build-log.md](archive/v1-dify-docs/build-log.md)。

## 当前状态（先读这里）

最后更新：2026-11-19（Dify 回放密钥已创建，等待从实际界面保存到本机配置）

- **方向**：项目改为「索尼银行住宅贷款坐席 Copilot」概念验证，见 [GOALS.md](../GOALS.md)、[PLANS.md](../PLANS.md)。
- **代码**：第一版文档已归档。本机六个 Compose 服务原生 arm64 并 healthy，kuromoji 已实测，网关的本机 Ollama 和 DeepSeek 两档都返回非零 token 用量。
- **分支**：当前本地 `2026-11-19-dify-console`，从阶段 38 本机收尾提交 `7377675` 建立。阶段提交留在本机。
- **第一版遗留**：阶段 21 的消融还有 251 份回答没评审，随第一版一起归档，不再继续。
- **模型**：意图档用 Qwen3 4B Instruct，20 条合成日文短题 19/20，P95 95.2 毫秒；嵌入和精排用 MPS；生成档用 DeepSeek V4 Pro。测量口径见[阶段 30](build/phase-30-cleanup-infra.md#小模型冒烟ac5)。
- **语料**：在可见 Chrome 中保存 54 份 HTML，53 份用于住宅贷款语料。S 档 185 篇、L 档 3,000 篇，两个存储均有 3,213 个规程块。出题包已校验，作者可以用本机 `.cache/policy-question-pack.zip` 开始准备阶段 36 的规程题。
- **检索**：`/retrieve` 已接通 ES 和 pgvector 的共同硬过滤，30 条日文冒烟的默认混合检索 S/L 均命中 30 条，P95 分别为 38.62/41.88 毫秒。默认关闭精排，仍可通过请求开关启用。
- **工具**：模拟业务已经以 MySQL 合成数据跑通，五个只读工具走同一鉴权、Redis、超时和裁剪链。真实联调保持坐席隔离，420 期返回 5 期并保留总数。
- **编排**：REST 与 MCP 已接入双泳道，客户查数转人工，坐席工具可与规程检索并行。Postgres 会话跨进程恢复已验证。阶段 34 的整段冒烟主意图 20/20。
- **流式**：SSE 已接入真实模型与 Redis 续推，入口日文脱敏和出口数字、引用检查均通过。预热串行 20 条合成冒烟，HTTP 首字 P95 2.346 秒，整段 P95 4.254 秒，撤回 0 条。冷态断线样例服务首字 5.231 秒，详见阶段 35。
- **评测**：阶段 36 合成开发 192 条已跑完。无注入 185 条首字 P95 2.217 秒，整段 4.290 秒；意图 124/128，已评分回归 175/185。附加 5% 条件 21 条，完整报告在 `.cache/copilot-eval/runs/mac-baseline/report.md`。
- **收尾**：纯合成干净目录从空库跑通迁移、生成、入库、API 和离线回归。最终本机 `poe check` 568 项、`poe test-int` 46 项，详见[阶段 38](build/phase-38-wrapup.md#记录)。现有数字汇总在 [Mac 本机实测报告](../docs/eval/mac-poc-report.md)。
- **Dify**：三档模型已用同一网关验证，185/185 篇 S 档文档完成索引。37 节点均已留证且通过编辑器检查，工作流已发布到本机。合成坐席查数与客户规程预览实际成功。详见[阶段 37](build/phase-37-dify-compare.md#记录)。
- **下一步**：本机 `.env` 具备应用密钥后先验证 API 单条请求，再执行同一批合成题和 5% 故障回放。规程开发题到位后再跑正式 S/L 配对和同题评测。
- **阻塞**：回放密钥已获授权创建。系统剪贴板未收到 Dify 界面复制值，改用数据库读取被自动审批拒绝。等作者从实际 Chrome 弹窗直接保存到 `.env`。正式规程开发题、20 条人工校准和一次封存测试仍待作者输入。
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
| [36 评测与回归门禁](build/phase-36-evaluation.md) | 阻塞 | 合成回放、报告和门禁已验收；待作者规程题、校准和封存 |
| [37 Dify 对照](build/phase-37-dify-compare.md) | 阻塞 | 本机发布、索引和两条真实冒烟已验收；批量回放待应用服务 API 密钥 |
| [38 收尾](build/phase-38-wrapup.md) | 阻塞 | 纯合成复现和本机检查已通过；待阶段 36、37 完成终稿 |

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
