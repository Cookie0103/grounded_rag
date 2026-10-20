# 开发日志（build-log）

> **进度的唯一依据**：只记观察到的事实（命令、输出、提交），不记计划。计划在 [build/](build/)，决策原因在 [context/](context/)。
> 追加规则：下面「活动记录」只追加、不改写旧条目；阶段状态表可以改。每个阶段完成时必须有验收证据才能标「完成」。

## 当前状态（先读这里）

最后更新：2026-10-20（phase-20结项：三套完成、严格审计通过、作者复核预标18/20＝90%达标）

- **代码**：phase-00～09 全部完成，分支 `2026-10-16-framework-build`，CI 绿；没有 PR，没合并 main（作者说之后再说）。
- **当前任务**：[phase-20](build/phase-20-judge-v2.md) 已按既定范围结项：代码复审、三套70/20/30重评、原函数复算、Windows严格审计与全量核查均完成。作者完成固定20条复核并明确dev089=true，五字段整题18/20＝90%达到85%门槛；方法为复核预标，非盲标。原Codex80%预标、旧36条标签、18条历史错误与全部原始结果保留。见[作者校准结项](code_review/2026-10-20-judge-v2-author-calibration.md)。
- **题集交接**：[phase-17](build/phase-17-dataset-repair-test30.md) 已完成交付。70题已按Claude报告和独立复核修订，四批副本同步；[全70当前稿](../docs/eval/dev70/review-70.md)。新编30题在仓库外，入口和压缩包位置见[交接清单](context/phase-17-test30-handoff.json)；开发者参与出题的边界已说明，待作者/Claude最终审定冻结。
- **本轮**：沿用当天分支`2026-10-20-dataset-repair`，保留开工前评测、题集与审核材料的未提交修改；本任务只交付运行核验文档。实际配置、命令和输出摘要见[核验报告](context/phase-18-readiness-report.json)。
- **评测准备**：[phase-12](build/phase-12-evaluation-dataset.md) 完成。作者确认的五项能力指标在 [metrics-v1](../docs/eval/metrics-v1.md)，指定Notion已整理为唯一表格化方案。[20道开发题草案](../docs/eval/dev20/README.md) 及51个要点已执行首轮试评，118条事实逐项核验。当前结果属于agent辅助诊断，作者金标审核、人工校准和通用E/F/C自动评审仍未完成。
- **本机配置**：当前主机为Windows/RTX 5070 Ti，原有Docker数据库已恢复在5432，Qwen3嵌入与精排使用CUDA，DeepSeek真实调用成功；两套向量数量与语料数量见核验报告。根`.env`、模型、batch和预算未修改；此前Mac/MPS结果属于另一台主机。
- **旧20结果**：[phase-13首轮档案](../docs/eval/results/runs/2026-10-19_1855_dev20_full-service/README.md)及Langfuse核验保留，不改冻结快照。作者新口径为20回归 + 70新开发 + 30测试，共120题；旧20不计入新70，原初评数字不作新70对外成绩。
- **下一步**：不再跑系统或真实评审；准备简历和复盘时引用本轮分题集结果与“作者复核预标、20条样本90%一致”口径，不混称RAG准确率，不把评审版本差异称系统性能提升，不称独立盲测或120条全量人工验收。
- **当前手动试跑**：`http://127.0.0.1:8000`保持运行，`/health`数据库正常；服务无reload、离线加载本地模型。真实单题及暖检索探针均通过；单题耗时不能代表正式性能。进程与日志位置见核验报告。
- **继续开发的话**：从当前分支建 `YYYY-MM-DD-xxx-yyy`；优先做 PLANS §8.2 里不依赖外部输入的项（如 `traces` 保留期清理、HTTP 模式 MCP 验证）；改提示词只对比开发集，不碰测试集。

## 阶段状态

状态取值：未开始 / 进行中 / 阻塞 / 完成。「完成」表示验收标准已观察到，不是计划。

| 阶段 | 状态 | 说明 |
|---|---|---|
| [phase-00 骨架](build/phase-00-skeleton.md) | 完成 | `poe check` 38 passed，覆盖率 95%；CI 两个 job 绿 |
| [phase-01 数据管线](build/phase-01-ingest.md) | 完成 | 182 篇 / 2090 子块入库；重复运行无重复块 |
| [phase-02 检索](build/phase-02-retrieval.md) | 完成 | 混合检索 + 精排 + `/retrieve`；冒烟集 Recall@5 92.9% |
| [phase-03 评测](build/phase-03-evaluation.md) | 完成（真实评审待作者提供后端） | 评测框架可用；只在 28 题冒烟集上验证过 |
| [phase-04 基线](build/phase-04-baselines.md) | 完成（真实分数待密钥） | 无检索、naive RAG 两条基线 |
| [phase-05 编排](build/phase-05-orchestration.md) | 完成（假模型；真实效果待密钥） | 五路路由、重检索、校验全在假模型上跑通 |
| [phase-06 记忆](build/phase-06-memory.md) | 完成 | 追问独立化、摘要、版本记忆 |
| [phase-07 服务](build/phase-07-service.md) | 完成 | SSE、MCP（仅验证 stdio）、缓存、降级、限流、压测 |
| [phase-08 观测](build/phase-08-observability.md) | 完成 | trace、反馈、干预库、后处理、坏例导出 |
| [phase-09 收尾](build/phase-09-wrapup.md) | 完成（真实数字待作者） | README、运行手册、最终报告模板、已知缺口 |
| [phase-10 实验记录](build/phase-10-evidence-tracing.md) | 完成 | 逐轮检索、缺失项和实际生成上下文进入 trace 与评测 JSONL |
| [phase-11 云端观测](build/phase-11-cloud-tracing.md) | 完成 | 本地、真实云端读回和作者指定 5432 均验证通过 |
| [phase-12 评测与开发题](build/phase-12-evaluation-dataset.md) | 完成 | 指标与 Notion 已记录；20 题草案及真实证据核验通过，待作者审题，尚无正式效果分数 |
| [phase-13 首批20题试评](build/phase-13-dev20-first-evaluation.md) | 完成 | 20/20真实运行、逐题初评、云端过程和107项分数核验、完整本地归档；待人工校准 |
| [phase-14 新70题首批](build/phase-14-dev70-batch01.md) | 本批完成、待审 | 仅交12题与来源，不代表70题完成；未执行系统或读取封存题 |
| [phase-15 首批修订与第二批](build/phase-15-dev70-repair-batch02.md) | 本批完成、待审 | 修订12+新增12；静态条件通过，语义独立审核与OR评分适配待做 |
| [phase-16 修订与补齐新70](build/phase-16-dev70-completion.md) | 本轮完成、待外部审定 | 指定12修复+新增46；70原样检索完成，独立初审问题已闭环，正式效果未跑 |
| [phase-17 复审修复与测试草案](build/phase-17-dataset-repair-test30.md) | 完成、待作者冻结 | 修复开发题、OR与语义问题，仓库外30题审阅包完成；未跑系统效果 |
| [phase-18 Windows连接核验](build/phase-18-windows-readiness.md) | 完成 | 本机REST、数据库、真实模型与Langfuse读回通过，服务保持运行 |
| [phase-19 三套初步评测](build/phase-19-final-evaluation.md) | 完成、待人工校准 | 三套全完成且无错；开发/回归云端核验，测试仓库外存储，校准样本交付，未提交Git |
| [phase-20 v2缓存重评](build/phase-20-judge-v2.md) | 完成 | 三套、严格审计和作者样本复核完成；18/20＝90%达标，非盲标；原记录与分歧保留 |

最终检查状态见下方2026-10-19活动记录。上次GPU pytest（2026-10-16）为3 passed；本轮真实试评调用Qwen3嵌入/精排与DeepSeek，未执行封存测试或已校准的正式效果评测。

## 活动记录（追加）

> 第一部分（2026-10-16）是 2026-10-17 根据 git 历史和旧日志**回溯补写**的，不是当时的实时记录；提交号可核对（`git log`）。当天的完整过程、困难与解决、查阅资料在 [archive/2026-10-16/README.md](archive/2026-10-16/README.md)，阅读笔记在同目录。

### 2026-10-16 · 分支 `2026-10-16-framework-build`（回溯）

模型分工：Claude Opus 5.5 写规范和计划；Claude Sonnet 5.5 实现。

**开发前准备**（12:35～14:06）
- 开发规范、调研笔记、M0 / M1 计划（`3f3b692`）；BM25 方案三次调整，最终定为 bm25s + jieba3（`b164f76`、`e5a091f`）；补充分块依据（`43c587a`）；计划改为已批准（`b10d7ed`）。

**phase-00 骨架**（14:08～14:17）
- `de5d83d` T1 core；`ae3df31` T2 质量门禁；`0c00d57` T3 providers 与假实现；`e649e9e` T4 数据库；`d4295b2` T5 API；`5ed8083` T6 CI；`4c4818e` 收尾。
- 验证：`poe check` → lint-imports 1 kept 0 broken、mypy no issues、38 passed、覆盖率 95.02%；`poe test-int` 3 passed；GitHub Actions `check`、`integration` 两个 job 成功。

**phase-01 数据管线**（14:19～14:50）
- `1958271` T1 语料下载；`254b72d` T2 mdx 清洗；`882ce7a` T3 父子切块；`615fec7` T4 四张表与迁移 0002；`7169dfd` T5 GPU 嵌入；`f502b9f` T6 入库；`3fbc5f2`、`5b8672d` 修 CI 两个问题；`18543d1` 收尾。
- 验证：`fetch-docs` 第一次下载 182 篇（6 秒，1.6MB），第二次跳过；`ingest` 第一次新增 182 篇、嵌入 2090 子块（18.4 秒），第二次未变 182、嵌入 0；`poe check` 152 passed，覆盖率 92%；`poe test-int` 19 passed；`poe test-gpu` 3 passed（torch 2.14.1+cu130，RTX 5070 Ti）。

**phase-02 检索**（15:54）
- `95da68b`：分词 + bm25s、RRF、检索器、`POST /retrieve`、两个精排模型、第二个嵌入模型补向量（迁移 0003）、`compare-retrieval`（9 种方案）。
- 验证：28 题冒烟集 Recall@5 92.9%，MRR 0.857；近义用词 100%、远义用词 77.8%。结论只是暂定，待开发集。

**phase-03 评测**（15:59～16:07）
- `0056a5f` wip：数据、打分、评审、评测器；`0ddce4e` 完成：测试、报告、归因、命令、Gemini 出题提示词。
- 验证：`poe check` 279 passed，覆盖率 92%；`poe test-int` 23 passed；`export-for-gemini` 导出 2 份。

**phase-04 基线**（16:11）：`e9f5cc0` DeepSeek 客户端与每日预算、两条基线、`eval-dev` 选项。没有密钥，无真实分数。

**phase-05 编排**（16:15）：`2343892` 护栏、路由、改写分解、证据评分重检索、带引用生成、忠实度校验，LangGraph 组装，9 个版本化提示词，`eval-dev --system full`。全部在假模型上验证。

**phase-06 记忆**（16:17）：`29b1892` 追问独立化、摘要、版本记忆、内存与 PostgreSQL 存储（迁移 0004）。

**phase-07 服务**（16:22～16:26）：`8499c44` `/chat`（JSON 与 SSE）、缓存、熔断与降级、限流、预热；`2cd33e2` MCP（stdio）、压测脚本。压测（假对话模型 + 真实检索）：`/retrieve` 冷查询 QPS 4.8，P95 870 毫秒。

**phase-08 观测**（16:31）：`bcb68c7` trace 持久化与复盘、反馈、干预库、输出后处理、坏例导出（迁移 0005）。

**phase-09 收尾**（16:34）：`722bab7` README、评测运行手册、最终报告模板、已知缺口、消融系统入口（`hybrid-rag`、`routed`）。

### 2026-10-17 · 文档整理为 harness 结构

- 把 `docs/` 下的计划、规范、决策、日志按「根目录规则 + `harness/` 阶段文档」重新组织（全部用 `git mv` 保留历史）：
  - `docs/proposal-2026-10-15.md` → `PLANS.md`（目标与非目标拆出到 `GOALS.md`，待办与阻塞并入 §8）
  - `docs/specs/M*.md` → `harness/build/phase-NN-*.md`
  - `docs/decisions.md` → 按阶段拆成 `harness/context/phase-NN-*-context.md`
  - `docs/implementation-log/` → `harness/archive/`（原样归档）
  - `docs/coding-standards.md`、`workflow.md` → 根目录 `CODING-STANDARDS.md`、`WORKFLOW.md`
  - `docs/HANDOFF.md`、`known-gaps.md` → 并入本文件和 `PLANS.md §8`、`AGENTS.md`
  - `docs/eval/gemini-question-prompt.md` → `PROMPTS.md §6`
  - 新建 `harness/code_review/`（空，放 review 输出）
- `docs/` 只剩给人看的：`eval/runbook.md`、`final-report-template.md`。

### 2026-10-18 · 实验过程记录（分支 `2026-10-18-evidence-tracing`）

- 作者要求补齐每轮查询、召回 chunk、缺失信息和最终实际交给生成模型的上下文。先查找并复用 `Step`、`RetrievalResult`、`SystemAnswer.to_json/from_json`、`PostgresTraceStore`；新增可选 `StepDetails`，没有重复定义 chunk 或新建日志系统。
- 编排在每个检索步骤保存各 query 的返回结果、候选文本/分数/排名与父块，在评分步骤保存充分性和缺失信息，在每次生成步骤保存实际资料字符串（保留引用编号及截断结果）。服务降级保留已完成步骤。
- 无检索、只检索、朴素/混合基线及完整系统的步骤由已有 JSONL 缓存落盘；旧缓存仍可读。trace 沿用 `steps` JSONB，无迁移；REST/SSE 的步骤详情同步可见。
- 红灯：新增两条编排回归测试先运行，均因缺少 `Step.details` 失败。实现后定向测试 70 passed；追加生成后期失败的降级回归，由下述完整检查覆盖。
- 验证：`uv --cache-dir ../.cache/uv run --no-sync poe check` → 格式、lint、分层、mypy 全通过，426 passed，覆盖率 94.97%。`poe test-int` → 32 passed（独立 `grounded_rag_test` 库，含嵌套详情 JSON 往返与 MCP stdio）。
- 环境处理：沙箱无法启动 uv 管理的 Python，验证在已批准的沙箱外运行；首次集成测试因本机 `DATABASE_URL` 格式错误失败。启动已有 compose 数据库后，按容器实际端口 15432 临时覆盖测试连接地址并通过，未修改 `.env` 或安装依赖。
- 已读作者公开的 Notion 进度和评测第 7 节；已确认现有 `.cache/gemini-pack/part-01.md`、`part-02.md` 合计 182 篇文档。运行手册补充“语料/导出/开发题/测试题”解释与 20+50+30 的关系，以及过程字段查看方式、旧缓存隔离要求。
- 自查：[phase-10 Codex](code_review/2026-10-18-phase-10-codex.md)；决定见 [phase-10 context](context/phase-10-evidence-tracing-context.md)。本轮未运行真实模型、未读封存测试题、未改评分规则或评审 Prompt。
- 边界：记录检索器最终返回候选；未完成节点的部分状态不保证保存。旧缓存不能自动追补过程。首次记录后仍需作者准备正式题集、确认模型配置并校准评审。

### 2026-10-19 · 云端观测与真实运行核验（分支 `2026-10-19-cloud-tracing`）

- 作者授权使用 Langfuse 免费云端观测，并要求逐步复盘、终端启动和配置核验。先读当前状态、规范和已有模块；沿用 Step / RetrievalResult / TraceRecord / SystemAnswer，不建新表、不改题集、评分或 Prompt。
- 新增 `langfuse>=5,<6`，锁到 5.0.2；`uv --cache-dir ../.cache/uv sync --extra gpu --locked --quiet` 成功，保留 GPU 环境。检查锁文件仅新增 SDK 与其依赖，没有升级旧包。配置和 `.env.example` 同步三项 Langfuse 参数，缺密钥不启用 SDK。
- 检索保留融合后的完整召回候选（含两路来源/分数）、精排全部候选、最终 top-k；查询改写/分解/补查询有结构化列表，保留合并父块、每次实际上下文和原始生成输出、校验输出、正常/拦截后处理和降级原因。回答缓存只记命中且费用归零；检索缓存明确 cached，避免误判为重复生成或重复 GPU 执行。
- API / MCP ask_docs / 新终端 `uv run python -m scripts.ask "问题"` 共用服务，节点完成后发往 Langfuse 后台队列；评测包装已有 System，发送原题、gold_docs、nuggets、预期路由、结果与步骤，评分逻辑不变。旧缓存不自动补传，裸检索和自动评审分数不在本轮云端范围。
- 红灯：候选保留回归先运行，因缺少 recall_candidates 失败。实现后定向回归检查；基线原测试更新新增 output 断言；新增云端故障隔离和参考答案记录测试。真实 SDK + InMemorySpanExporter 离线检查观察到两个同 trace 的父子记录；发现 event 自动结束，移除重复 end，未把离线验证当云端成功。
- `uv --cache-dir ../.cache/uv run --no-sync poe check` → 格式、ruff、分层、mypy 通过，433 passed，覆盖率 94.85%。首次完整检查发现测试替身缺新 close，补齐关闭断言后通过；未加忽略/跳过或降低门槛。最终 `poe test-int` → 32 passed，使用独立 grounded_rag_test 库。
- 本机核验：`.env` 的 DeepSeek 密钥已填，`deepseek-flash` 真实请求成功，费用经原 BudgetLedger 记录；没有打印或提交密钥。GPU 为 RTX 5070 Ti，设置 HF_HUB_OFFLINE=1，Qwen3 / BGE-M3 各实际生成 1024 维向量，Qwen3 / BGE 重排各实际输出两条分数。证据保存在忽略目录 `.cache/runtime-audit-2026-10-19.json`。
- 数据库：发现已有 grounded_rag-db-1 停止且映射 15432，而作者修正后的合法 DATABASE_URL 指向 5432。启动原容器，确认连接成功后把根 `.env` 的 DATABASE_URL / DB_PORT 对齐 15432，保留其余配置。实读为 documents=182、parent_chunks=1252、chunks=2090、chunk_embeddings=4180；两套模型缺失向量均为 0。没有重下语料或重建索引。
- 真实链路：`uv ... python -m scripts.ask "知识库单次最多上传几个文件？" --edition self_host --json` → SINGLE、回答最多 5 个并引用；过程在 `.cache/chat-smoke-2026-10-19.json`。从 PostgresTraceStore 读回 trace `123a91b1f91b46668d9ab05b44eab9bf`，确认 8 步含 postprocess，候选数 50 / 20 / 5，实际生成输出与上下文落库。该调用只是冒烟，不作正式性能结论。
- 实际启动 `uvicorn app.api.main:create_app --factory --host 127.0.0.1 --port 8000`（PREWARM=true）成功；PowerShell 请求 `/health` → HTTP 200、status=ok、database=ok。验证后已停止本轮创建的 HTTP 进程，数据库保持运行，作者可自行 `poe serve`。
- 运行手册补齐第一批 20 题的出题步骤、五路与改写区别、chunk 检查边界、语料固定 GitHub 来源和父子切分、CLI / REST 命令、云端配置和长期保存。核对官方价格与静态托管资料后选 GitHub Pages；正式题集完成前未发布站点。决定见 [phase-11 context](context/phase-11-cloud-tracing-context.md)，自查见 [phase-11 Codex](code_review/2026-10-19-phase-11-codex.md)。
- 剩余外部输入：Langfuse PUBLIC_KEY / SECRET_KEY 最后核验仍缺，作者已答复会配置；本轮不能宣称真正上传云端。作者填好并重启后需验证云端接收，才能完成 AC4。正式开发/测试题和人工评审标注也未提供。代码本地提交，暂不推送/开 PR/合并。

### 2026-10-19 · 续：真实云端验收与固定 5432

- 作者填好 Langfuse 日本区凭据并把连接端口改成 5432 后，报 PostgreSQL 密码认证失败。只输出配置是否匹配，确认用户名/密码与 compose 一致；容器内部读取 documents=182 成功，本机 5432 连接失败。查 Windows 服务与进程，确认监听 PID 7976 属于 `postgresql-x64-18` 的子进程（服务 PID 6088），不是 RAG / Travel Agent 容器。
- 实读容器版本：RAG `postgres --version` → PostgreSQL 16.15，镜像 pgvector/pgvector:pg16；Travel Agent → PostgreSQL 17.11，镜像 postgres:17，映射 5434。原生 PostgreSQL 17 服务的子进程 PID 8024 使用 5433；原生 PostgreSQL 18 原为 Auto、使用 5432。四者独立，不按端口推断版本。
- 原先临时恢复 15432 验证成功；作者随后明确要求“就要 5432”，并授权关闭 Windows PostgreSQL 18。普通权限 Stop-Service 被 Windows 拒绝后，经 UAC 管理员操作执行 Stop-Service 和 Set-Service -StartupType Manual；复核 State=Stopped、StartMode=Manual，未删除安装或数据，未改 Travel Agent 和原生 PostgreSQL 17。
- 仅更新根 `.env` 的 DATABASE_URL 端口与 DB_PORT 为 5432，保留所有密钥及其他配置。`docker compose up -d db` 沿用原持久卷重建容器；`docker compose port db 5432` → 0.0.0.0:5432。本机通过 app.db.engine.ping 与 table_counts 实读 documents=182、parent_chunks=1252、chunks=2090、chunk_embeddings=4180。
- `uv --cache-dir ../.cache/uv run --no-sync python -m scripts.ask "知识库单次最多上传几个文件？" --edition self_host --json` 在 5432 下真实成功，回答最多 5 个并附引用，8 步齐全；输出在忽略目录 `.cache/chat-5432-smoke-2026-10-19.json`，应用 trace_id=`5e422450547c4b80bebf1e0fef17407a`。
- Langfuse auth_check=True。SDK v5 使用 observations.get_many，按云端 trace_id=`6087e6c7a7a48073197a66fe958a430f` 实读到 9 条记录：根 grounded-rag 与 guard/route/rewrite/retrieve/grade/generate/verify/postprocess。云端原始响应在 `.cache/langfuse-5432-smoke-2026-10-19.json`。此前另一真实请求也核对了云端候选 50/20/5、实际 context 和 output 与本地完全一致；AC4 据真实服务端读回完成。
- 本续任务没有修改业务代码、依赖、表或评测。更新阶段状态、端口决定和参数解释；手册说明 edition、session_id、python -m、PowerShell 末尾反斜杠和 /docs 与 /health 的区别。当前 HTTP 8000 没有监听，作者需要常驻接口时运行 poe serve；CLI 已实际验证。
- 端口切换后的提交前复核：`uv --cache-dir ../.cache/uv run --no-sync poe check` → 格式、lint、分层、mypy 通过，433 passed、覆盖率 94.85%；`poe test-int` → 32 passed（5432 上的独立测试库）。文档差异 `git diff --check` 通过，未暂存 `.env` 或缓存。

### 2026-10-19 · 续：关闭原生 PostgreSQL 17 自启并解释配置

- 作者要求关闭原生 PostgreSQL 17 自动启动并释放 5433。沿用上一轮管理员脚本流程，经 UAC 执行 Stop-Service 和 StartupType Manual；查询确认 Windows 17、18 两项均为 Stopped / Manual，5433 无监听。Docker RAG 仍为 5432，Travel Agent 仍为 5434，未改容器版本或数据。
- 安全核对 `.env`：DB_PORT 已由作者删除，DATABASE_URL 端口为 5432；`docker compose port db 5432` 实际输出 0.0.0.0:5432。保留作者删除决定，Compose 的 `${DB_PORT:-5432}` 默认已满足当前要求，无需重新加 DB_PORT。
- 解释并记录：DATABASE_URL 给 Python 选择数据库地址，DB_PORT 给 Compose 设置宿主机映射，两者消费者不同。RAG 的 16.15 来自仓库既定 pgvector:pg16 镜像，不是只能用 16；官方有 pg17 镜像，升级大版本需要迁移已有数据并验证，不因作者询问原因而擅自升级。本续仅系统服务操作和文档更新，未改业务代码、检查配置或题集；git diff --check 通过。

### 2026-10-19 · 续：保持服务运行供作者手动检查

- 作者决定保持 PostgreSQL 16，并要求先把现有系统启动试跑。启动前确认数据库容器 healthy、映射 5432，8000 无监听；在 backend 执行 `uv --cache-dir ../.cache/uv run --no-sync poe serve`，预热成功并保持运行，未在验证后停止。启动日志进程为 reloader=33852、server=43568，供本次会话追溯，不作为以后固定 PID。
- PowerShell 请求 GET /health → HTTP 200、status=ok、database=ok；POST /chat，问题“知识库单次最多上传几个文件？”，edition=self_host → HTTP 200、SINGLE、回答最多 5 个并引用，degraded=false、abstained=false。结果在 `.cache/manual-api-smoke-2026-10-19.json`。
- 本次实际出现 10 个步骤：guard / route / rewrite / retrieve / grade / generate / verify / generate / verify / postprocess。校验器认为初稿中的“默认”缺少明确依据而触发一次重生成，第二次校验通过；这只是观察到的行为，尚未由正式题集和人工评审判断其收益。
- 应用 trace_id=`f8bd0d8c3c5d47108c8c58e2a70bb37f`；Langfuse 云端读回 11 个观测（根 + 10 步），其中 generate=2。云端 trace_id=`1debd6a47334a82539d61059567c91f7`，原始响应在 `.cache/manual-api-cloud-2026-10-19.json`。本地接口文档通过 open_in_codex 请求打开，服务日志确认 /docs、/openapi.json 均 200。
- 建议作者先在 Swagger 用 session_id=demo-001 手动检查回答/引用/步骤/云端；有 session_id 不走整答缓存，避免重复原题时只看到 answer_cache。独立对话换新 ID，之后再准备正式开发题。本次未改业务代码或题库，不重复运行单元测试。

### 2026-10-19 · phase-12 T1～T2：固定评测方案与 Notion

- 作者确认五项能力指标，要求在仓库记录并由两个 Sub Agent 分别负责 Notion、出首批开发题。新增 [metrics-v1](../docs/eval/metrics-v1.md) 与 [phase-12 context](context/phase-12-evaluation-dataset-context.md)，runbook 链接统一口径；原有评分代码、评审 Prompt、正式只读题库未改。
- 分工实际设置：Notion 为 GPT-6.1 Sol high，出题为 GPT-6.1 Sol xhigh，主 agent 复核。开发题由 agent 制作是作者本轮明确授权，不放开封存测试题。题目制作仍进行中。
- Notion「测评」页 `3fed513271c1806dad8ee0a14f952899` 顶部增加当前 V1 提示，底部追加五项分子/分母、原总分、N/A/异常、宏平均、20/70/30 用法与已有/待实现；刷新后读回核验，保留旧草案作背景。截图在本机 visualizations 的 `notion-eval-v1-2026-10-19.png`，未发布额外站点。
- 首次 `uv --cache-dir ../.cache/uv run --no-sync poe check`：格式、lint、分层、mypy 通过；432 passed / 1 failed，唯一失败是本轮前已有 `.env.example` 的 RATE_LIMIT_PER_MINUTE 键名夹入中文。作者收到说明后自行修复，未由 agent 覆盖配置。
- 重新运行同一完整检查：格式、lint、分层、mypy 全通过，433 passed / 35 deselected，覆盖率 94.85%。首次沙箱内 uv 无法启动其外部 Python，实际验证在批准的沙箱外运行，无安装或升级。
- `.env` 没有 RATE_LIMIT_PER_MINUTE 时 Settings 默认每 IP 每分钟 30 次；示例文件字段检查与实际默认读取是两回事。本轮未改业务代码/数据库，未运行付费评测、未读封存测试题。

### 2026-10-19 · phase-12 T3：首批开发题草案与真实证据

- GPT-6.1 Sol xhigh 出题 agent 交付 [dev20](../docs/eval/dev20/README.md)：20 道全部 split=dev，7 事实 / 3 归纳 / 4 跨篇 / 2 版本 / 4 边界。可阅读题卡含问题、参考答案、关键点和来源；JSONL 复用 Question，JSON 证据附表不冒充已有自动评分输入。作者审核与跨模型独立审核尚未完成。
- 从冻结 MDX 提取 51 个必答点，覆盖 18 篇金标文档。复用 clean_mdx、chunk_document 重建语料；只读事务调用 load_chunks / load_parents / document_hashes 与实库核对，182 文档 / 1252 父块 / 2090 子块的 ID、正文、标题路径、父子关系及内容哈希全部一致。临时导出在忽略目录 .cache/dev20-authoring，未改数据库或重算向量。
- 实际执行 `uv --cache-dir ../.cache/uv run --no-sync poe eval-validate ../docs/eval/dev20/questions.jsonl` → 0 错误、0 提醒。主 agent 逐题审阅并另用临时 root_audit.py 复用现有校验器、清洗和切块：51 要点、69 条含边界的证据条目通过原文行号 / 子块 / 父块 / 标题 / 冻结链接核对；必要摘录均在实际 gold_document_text 截断范围内，缺依据题关键词扫描可复现，本地 Markdown 链接有效。报告在 .cache/dev20-authoring/root-audit.json，不作为效果分数。
- 修正两类潜在金标偏差：dev015 不把文档所列上传上限扩写成“默认配置”；dev011 的扩展名和 MIME 筛选接受等价方案。dev017 允许正确按版本 / 套餐完整回答；现有 Judge 不读附表，条件答案数值须人工复核。dev020 允许检索后拒答，不能据缺资料断言产品没有 SLA。
- 初批题目偏自部署、操作场景和长问法；README 明示扩到 70 时补短问、云端、错误前提等覆盖，不能据 20 题推断全部场景。未读取测试题、调用 DeepSeek、运行被测 RAG 或生成正式效果数字。

### 2026-10-19 · phase-12 T4：最终审计与草案交付

- T1～T2 的指标与 Notion 已提交 `914413a`，T3 的题目与证据已提交 `5ba9712`。主 agent 最后复核分工交付，写入 [phase-12 自查](code_review/2026-10-19-phase-12-codex.md)，阶段验收 AC1～AC4 完成；“完成”仅指本阶段要求的文档与待审题目，不包括后续自动评分实现或正式实验。
- 最终 `poe eval-validate ../docs/eval/dev20/questions.jsonl` 仍为 0 错误 / 0 提醒，root_audit.py 通过。当前阶段完整 `poe check` 已在 T1～T2 记录通过，之后仅有文档和开发题新增；未改业务代码或数据库，不重复运行无关集成检查。最终 `git diff --check` 与文档提交密钥 / 大文件钩子通过。
- 复核保留清晰边界：20 题全是 dev 草案，参考答案来自固定原文；作者审核、跨模型独立复核和评分校准未完成；没有付费正式作答、效果提升结论或 E/F/C 自动分数。Notion 保存核验截图路径已记录，作者可先看题卡与指标文档，再冻结题集推进评测。
- 任务只本地提交，未推送、创建 PR 或合并。没有暂存 `.env` / 原始语料 / 缓存，没有修改只读正式题库、评分代码或评审 Prompt。

### 2026-10-19 · phase-12 续：Notion 整理为单一表格化方案

- 作者要求用当前方案覆盖前面的草案，不再保留两套正文。已通过已登录 Notion 页面清空重复正文，写入一份完整方案，保留页面标题「测评」、属性和原 URL；没有改共享权限。刷新后读回确认旧标题与“旧草案仅供背景”均不存在，当前方案只有一份，包含 10 张原生表格。
- 题型表逐项对应 dev001～dev020，明确预期 SINGLE=12、MULTI=4、CLARIFY=1、REFUSE=2，另 1 题不固定首路由但最终应说明资料不足；DIRECT 闲聊另做手工检查，不占 20 题。路由是诊断信息，不替代最终内容评分。五项指标、分母 / N/A、总分、保存项、20→70 / 30 用法、实现状态和三篇论文对应均统一整理，评分契约未改。
- 状态已更新为 20 题草案和真实证据已完成、待作者审题，删除“还未开始出题”等过时表述。保存后的题量表截图在 visualizations 的 `notion-eval-single-version-2026-10-19.png`；浏览器页已标记保留。正文替换前快照和编辑 HTML 放忽略目录 .cache，未提交。
- 作者明确其当前 `.env` 已包含 RATE_LIMIT_PER_MINUTE=30、PREWARM=false；此前“未填写时使用默认值”只是条件说明，不代表作者当前没填。本轮未读取或修改 `.env`，未改业务代码、评分、题目或数据库；仅检查文档差异，不重复运行代码测试或付费评测。

### 2026-10-19 · phase-13 T1：独立试评入口与归档

- 作者批准真实运行20题，完整保留步骤、答案、题目、评分依据、单轮报告及版本；跨轮次总览暂缓。新增 scripts/eval_round.py，复用生产服务工厂、run_system、Question、Trace和BudgetLedger；独立目录拒绝覆盖，固定单并发、无会话、空整答缓存，复制题集/证据/指标和哈希，不改旧缓存或金标。
- 核对当前已配置deepseek-flash、Qwen3嵌入/精排及cuda，每日预算10元，既有账本约0.10元；Langfuse auth_check=True，已核对SDK的过程/分数读回接口，未输出密钥。
- 规定检查实际通过：格式、lint、分层、mypy均成功，433 passed / 35 deselected，覆盖率94.85%。最初入口的同步git子进程和预算常量触发规范检查，改用已有异步子进程写法及明确上限后通过，未加忽略或降低门槛。

### 2026-10-19 · phase-13 T2～T4：20题真实运行、逐题初评及云端核验完成

- 使用T1提交bd4a312的full-service入口实际运行dev001～020，18:56～19:02（日本时间）全部完成、无系统错误；不改题集、模型、参数或Prompt，没有重跑挑选。原BudgetLedger从¥0.09982656到¥1.00320984，本轮按固定单价估算¥0.90338328，不含当前评审会话费用。
- 当前会话对51个必答点及118条去重事实核对冻结原文和最终上下文；复用score_question/summarize。E/A/F/C/B宏平均96.88%/92.19%/99.52%/98.48%/100%，适用题数16/16/16/16/4；可答题完全正确13、基本正确1、未答1、无依据扩写1，边界4/4。可信平均0.825，bootstrap区间[0.575,1.000]；文档全命中Recall@5=13/16，P95=42.74秒。20题为开发草案、agent初评未人工校准，不能当已确认的正式成绩。
- 主要诊断：预期路由一致8/19，单篇题经常被分解；dev008初次分解偏向FAQ、缺未命中处理证据，两次生成/校验后误拒答。dev012额外“只能删除重建”按原规则扣分但唯一性判断待复核；dev013冻结金标要求明确排除Chatflow，可能过细；dev011文本型PDF条件也标记复核。未为改善分数修改金标。
- Langfuse过程、题目、最终答案及每步note/details服务端读回20/20一致；附加20份含参考标准的评审记录，107项适用数值分数全部读回一致。首次上传后短暂入库延迟通过只读重查解决，未重复上传评审。云端核验回执在本轮cloud-verification.json。
- [独立归档](../docs/eval/results/runs/2026-10-19_1855_dev20_full-service/README.md) 包含题集/标准快照、独立答案、完整步骤、分数与理由、单轮HTML/Markdown报告、代码/语料/权重版本。原始大文件本地保留；四个ZIP随Git保存、单包小于现有1000KB门槛，全部还原逐字节一致，SHA256校验通过。未创建跨轮次index、部署站点或触碰封存题。
- 浏览器实际检查搜索、逐题展开、三阶段chunk和报告版式，控制台无错误；截图为visualizations内dev20-evaluation-report-2026-10-19.png。最终档案审计20题/51要点/118声明、快照原件一致、20个唯一trace、云端分数一致均通过。T1完整poe check已经433 passed，此后无业务代码改动；本轮仅本地提交、不推送或合并。

### 2026-10-19 · phase-14：新70题首批12题与审题证据

- 作者提供新的严格出题Prompt，要求先交12题供Claude审，题量改为20回归+70新开发+30封存测试。已保存原始Prompt、分批配额与约束；仅制作dev021～dev032，不把旧20计入，不自动继续58题。
- 材料在docs/eval/dev70/batch-01：questions.jsonl、evidence.json、README题卡、validation.json。先读固定Dify原文再选事实出题，包含4事实、2归纳、3跨篇、1版本、2边界；26个必答点、40条来源记录，有原文路径/行号、真实chunk/父块、小问数、难点、参考答案和可能失败点。
- 复用原export.py只读重建对照：182篇/2090子块/1252父块一致，未嵌入或重建索引；复用既有ev/nugget定位来源。落盘反向核验原文哈希、行号、清洗全文、chunk、父块、Judge截断范围均通过；11/12题不超过40字符，部署/云版前缀2/12，12篇金标及18篇含边界/干扰来源，四大目录覆盖，同篇最多2题。全70至少50篇的目标仍待后续完成。
- 自查修正：原归纳选点只有2个H2，已换成3章节3子块；移除题干没问的类型、替代API等强制评分项；表单题接受必要偏序而非要求不必要的全顺序。链式题显式记录第9课→模板转换→default用法；缺答案题扫描全182篇原文/清洗文、复核所有相关命中与触发器/配置页，未把词汇零命中当不存在功能的证明。
- 既有poe eval-validate通过，0错误/0提醒；完整poe check通过：格式、lint、分层、mypy、433 passed/35 deselected、覆盖率94.85%。本任务未改业务代码或评分，未运行RAG、基线、付费评审或读取系统作答。source/难度判断由同一agent制作和自查，不冒充Claude或作者独立审题。
- 作者/Claude在工作区对eval_round.py、metrics-v1、runbook、dev20 README的4项修改保留，不混入本任务提交；旧20冻结档案未改。下一步仅审本批12题，重点看dev026字段粒度、dev027链式真实性、dev031缺答案核查；审核后再继续。
### 2026-10-19 · phase-15：首批12题修订与第二批12题交付

- 按作者本次审核附件重写dev026/027/029/030/032，修正dev021/024/028的重复计分、dev023的等价来源、dev031的缺答案核查。所有guessable_without_docs统一为null；不以主观判断代替无检索基线。
- 新增dev033～044，严格5单跳/5多跳（2链式）/1注入/1模糊；首批保持4单跳/6多跳（1链式）/2边界。合并审阅稿、两批独立题目/证据/校验、修订记录、事实台账、6对孪生逐字比较均在docs/eval/dev70。正式100=70开发+30封存，旧20另作回归；目前只到24题，不继续剩余46。
- 实际执行（backend目录）：`uv --cache-dir ../.cache/uv run --no-sync python ../.cache/dev20-authoring/export.py`，只读核对182篇、2090子块、1252父块与数据库ID/正文/路径/哈希一致。没有改库、重建索引或调用模型。
- 实际执行`.cache/dev70-authoring/repair_and_batch02.py`和`review_24.py`：24题通过既有Question格式校验；86条来源记录的原文行号、字节哈希、子块/父块/标题及Judge截断范围逐条核验。每批11题≤40字符，最长58/43；每篇金标含等价来源在批内仅1题；累计34篇金标、31个不同来源组，四大目录都有，最终50篇覆盖仍待全70验收。四道分散题均有3个不同代表父块，三道链式均≥5关键词且题干无泄漏。以上是静态结果，不是效果分数。
- dev031对182篇原文与清洗文本分别执行10组去重/幂等关键词全文搜索，全部0命中；另登记最接近3篇无答案原因。孪生原文字节/字符差异及清洗后差异完整留存，不将路径差异冒充答案差异。dev037及dev044保留版本差异原句。
- 明确运行前缺口：当前加载器忽略gold_doc_groups，正式Recall@5须先支持等价来源组内OR；dev032 route=null只能评纠正前提行为，不能算路由正确；dev043可拒绝恶意部分后回答正常部分，dev044接受条件答案。未改评分规则、Prompt、业务代码、受保护题集或旧20档案。
- 完整`uv --cache-dir ../.cache/uv run --no-sync poe check`通过：格式、lint、分层、mypy成功，433 passed、35 deselected、覆盖率94.85%；`git diff --check`通过。数据库未改，不跑集成写库检查。未运行RAG、付费评审或无检索基线，未读取任何系统作答或封存题。
- 作者原有4个未提交文件保留，不纳入本次提交。当前出题和自查为同一agent，独立Claude/作者审题未完成；尤其复核桥接必要性、vital原子性及语义查重。无出题阻塞，按本次两批交审范围停止。
### 2026-10-19 · 作者要求汇总当前分支全部修改并推送

- 核对当前分支为2026-10-19-cloud-tracing；工作区仅4个既有修改：eval_round.py隐藏edition开关，以及dev20 README、metrics-v1、runbook的20回归+70开发+30测试口径。无其他未跟踪文件；未纳入.env、原始语料或缓存。
- 提交前完整`uv --cache-dir ../.cache/uv run --no-sync poe check`通过：格式、lint、分层、mypy通过，433 passed、35 deselected、覆盖率94.85%；git diff --check通过，提交密钥/大文件钩子通过。
- 已提交为433ae94（feat(eval): 提交隐藏版本选项并统一评测题量口径）。先fetch并确认远端无同名分支，再执行`git push -u origin 2026-10-19-cloud-tracing`，返回new branch成功，建立origin同名跟踪；此前24题及观测等本地提交随整条分支同步推送。没有合并main、强推或创建PR。
- 本条为推送后的交接记录，随日志提交同步到同名分支；远端最终HEAD与本地HEAD核对见Git引用。未运行RAG、付费评测或检查远程CI。


### 2026-10-19 · 新70题补齐启动（phase-16）

- 作者提供Claude复审，明确本轮修订12个点名ID并自主补剩余46题，两半各23题；旧20独立回归、去重覆盖90题。需求与任务记录于phase-16，阶段审批按作者长程授权处理。
- 本机为Mac新checkout，无data/.cache/.venv，Docker仅有Travel Agent数据库；已恢复固定commit的182篇公开语料，全部Git blob SHA匹配。已有Compose启动本项目新数据库并执行既有0001～0005迁移。未改schema或迁移源文件。
- 现有uv全局exclude-newer与锁文件版本冲突，直接uv sync --frozen恢复已有锁定依赖和gpu extra，未升级依赖、未改锁文件。子进程uv缓存曾访问沙箱外，改用项目UV_CACHE_DIR及UV_NO_SYNC后运行规定检查。
- 初始poe check：格式/lint/分层/mypy通过，433 passed、35 deselected，覆盖率94.85%，原始输出.cache/dev70-completion/check.log。
- 作者选择允许MPS/CPU适配。原定Qwen3嵌入/精排在MPS真实冒烟成功：1024维，相关片段得分0.99995、无关片段0.00060。只对命令覆盖设备和batch，未更改.env、预算配置或业务代码；未调DeepSeek。入库正在执行，尚不能声称检索环境完全恢复。

### 2026-10-19 · phase-16 T1/T2：语料恢复与12题复审修订

- T1完成：MPS入库182篇、2090子块，随后只读比对全部文档内容哈希、1252父块和2090子块的ID/文本/父子关系一致。只恢复Qwen3向量，不把另一台电脑的BGE向量数量当作本机事实。
- T2完成：修订dev021/024/029/030/031/033/034/035/036/037/041/043，其余12题问题行与证据对象原样。独立snapshot校验无硬失败（旧题局限单列legacy_observation）。dev030换OAuth差异，dev041采用字段名字符集合保住3父块；批量字段候选因落同父块被拒并替换。
- 证据重建47处、4对孪生逐字差异归档；本机全量数据库比对后修订来源标记verified。题干、参考答案、JSONL、evidence和24题审阅稿同步。未跑完整系统/无检索基线/付费评分；新46蓝图仍在设计，尚未声称完成。

### 2026-10-19 · phase-16运行与蓝图复核中间记录

- T1/T2已提交`bd407df`。原样单次检索已完成修订24题，所有调用均不传edition、不改写分解，未发生精排降级；9道单跳命中8道，先保留诊断，最终按新70全量统计并列加难建议。仅候选检索，不是完整系统或无检索基线。
- 因恢复本机数据库，追加既有poe test-int：32 passed、436 deselected，使用独立grounded_rag_test库；开发语料库保留。
- 蓝图尚未通过：初稿4道导航式弱链被拒并替换；dev062/085事实与行号错位已退回重定位。独立审题继续核查逐事实来源、版本真差异、题干意图和必答点是否一致，以及跨块需all_of而非最长重合映射。未开始写新增正式题。

### 2026-10-19 · phase-16 T3：46题蓝图通过内部核验

- 蓝图正式文件blueprint.json，逐题一行；细分配额与两半23题目标精确。23对孪生独立逐字比较。机械118通过/0失败，两项全70范围由现24+规划46补充核验：95篇金标、每篇最多2次。剩46节点目录7篇，低覆盖目录至少12篇；具体实数见blueprint-validation.json。
- 独立审题46 accept/0 reject，实际核对113事实、123原文行段、182原文文件SHA；被拒导航式链、错误行号、虚弱版本差异等均已替换。审查和guardrails保存在blueprint-review.json/.md，不冒称作者/Claude已审。
- 在新增正式题数量仍为0时通过并提交本蓝图。候选35处source映射明确pending，正式题需要严格短摘录或多个all_of，不能复用最长重合chunk作为精确证据。后续开始两组23题写作。

### 2026-10-19 · phase-16 T4：新增前23题草稿

- 蓝图已先提交f764325/6f4dad3后，正式生成dev045～067，当前47/70。行为与细分配额精确；独立重跑snapshot 239通过/0硬失败，99处raw/hash/chunk/parent来源核对；18全量待项未冒充完成。项目Question格式验证无错误。
- 21题不超过40字符，最长51；前半仅dev053单vital，其他可答题满足单跳≥2/多跳≥3。Windows源码命令补齐原文队列消费配置；Cloud未知Q&A不作同义来源。
- 后23题仍由另一agent制作；T6会在全70合并后做fresh语义审查、原样单次检索和最终验证。未运行完整系统/无检索基线/付费评审。

### 2026-10-19 · phase-16 T5：后23合并，全70草稿齐备

- 后半dev068～090共23题，9单跳/9多跳（3链式）/3拒答纠正/2模糊；16题≤40字符，最长61。逐字来源76叶，仍标数据库核验待同步，未假称语义已审定。
- canonical新70已齐备，并更新review-70、两批题卡与事实台账。全量validate_completion.py completion实际564 pass、141 legacy_observation_pass、8旧题保留局限，0 fail、0范围待项。
- 独立逐事实审查发现OR漏标、主题跨度、重复事实与版本差异依据不足等问题；T6将核原文集中修复，修后再做新增46原样单次检索，不把静态通过当作语义通过。

### 2026-10-19 · phase-16 T6：新70交审稿、最终核验与检索诊断

- 新70（dev021～090）已齐，旧20仅用于90题事实查重。独立最终审查39 accept/7 reject，旧12修复逐项通过、另12行与evidence对象原样。主agent依据原文集中修复049 OR、051主题跨度、059重复事实、061命令口径、072 API跨层、076版本依据与088邻域场景；原审查及闭环保留，不冒称第二轮全量独立审查或Claude已审。
- 完整validate_completion.py completion：564 pass、141 legacy_observation_pass、8已保留旧题局限，0 fail/0范围待项；机械语义标记仍false，脚本不自行判语义，独立审题与主agent处理单独记录。新增每篇金标含OR最多一次、nodes7、少覆盖目录29；7链覆盖7种实质桥接，教程→节点仅1；场景/条件独立明确例子至少22/16。
- 原题各一次检索，不传edition、不分解：70条、无降级。单跳25/28（89.3%），新增17/19（89.5%）；超过70%后在retrieval-diagnostics列13道候选，其中新增8优先加难。保留真实首轮结果，未运行完整系统/无检索基线或付费模型，不作正式效果成绩。
- 最终poe check：433 passed、35 deselected、覆盖率94.85%；题库工具8 passed；既有Question loader70题0 issues；本轮集成测试此前32 passed、436 deselected，未改业务或schema。最终真实DB只读再核182篇hash/2090子块/1252父块完全一致。
- 交付入口：docs/eval/dev70/review-70.md；两半23各有question/evidence/review/validation；root validation含目标实际、逐题机械与语义条件、14项reject替换历史、70次检索及加难清单。原版蓝图及后续差异、孪生逐字比较、source/DB核验均保存。作者/Claude最终审定、OR正式加载器适配与正式效果评测属于下一步，未触碰封存30或backend/eval/data、评分、Prompt、.env及依赖版本。

### 2026-10-20 · phase-17 T1：开发题复审修复

- 保留作者两份Claude报告原样；在2026-10-20-dataset-repair分支修复H1～H6及题型、风险占位、镜像必答点、澄清轴和题级OR过宽问题。额外来源冲突通过替换048/070/077题点解决，067调整以维持nodes上限；030恢复真实跨篇。原因见phase-17 context及repair-2026-10-20.json。
- 复用生产清洗/切块定位，逐点all_of/any_of和文档组一致；总表及四批JSONL、证据、审阅稿、事实账本和验证清单已同步。历史检索/实库/语义审查档案保留，当前README明确不把旧成绩套给修订版。
- 实际执行validate_completion.py --mode completion --old20 docs/eval/dev20/questions.jsonl：0硬失败；既有旧题局限仍列观察，不降低门槛。test_tools.py通过；poe check格式/lint/分层/类型及单元测试通过，实际数值见phase-17自查报告。
- source_index.py按字符串排序修复Windows排序差异；仅向.cache/dataset-repair输出，182篇/1252父块/2090子块重建与旧索引全部文档对象一致，分布JSON与已提交版相同；未动数据库或重算向量。
- 本任务没有修改backend/eval/data、评分、评审Prompt、业务代码或预算；没有运行检索/完整系统/无检索或付费评测。T2仓库外测试草案与最终交接另记。

### 2026-10-20 · phase-17 T2～T3：30题草案与最终交接

- 作者明确要求的30题在仓库外新编：12单跳、12多跳、4拒答纠正、2缺槽位。提供JSONL、逐点证据、审阅稿、孪生逐字比较、验证、审查闭环、生成脚本与文件清单；ZIP校验通过。位置和hash见phase-17-test30-handoff.json，仓库不收题干或金标。
- 独立agent全量审阅30题并对照旧90事实，随后针对已知退回项作短复核；未发现仍需整题退回项。补006/008/011/013/030等价来源，明确014并行条件、011/017必答点索取、023拦截动作、029合理澄清边界。最后文本建议已同步；没有把开发agent参与制作的题冒充独立盲测。
- 实际运行仓库外author_test30.py：126条来源叶子行号/hash/子块/父块验证通过；4道分散题最少均3父块；Question格式无错误；同范围同事实的独立去重未发现明确重复，机械完全同文查重也无重复。完整数据见仓库外validation.json；未用被测系统答案做金标。
- T1已提交a029657。第一次提交钩子规范化工具并发现旧未使用变量，修复后工具测试、开发题静态核验重跑通过；再次ruff/格式/私钥/大文件钩子全部通过。当前修改仅数据、证据、出题工具和交接，无业务代码/数据库变化。
- 所有历史检索与运行档案保留。本轮没有检索、系统、无检索或付费评测；正式OR评分加载器、作者最终审定和后续实验仍是后续步骤，不冒充本轮已完成。当前任务的制作与修复工作已完成。

### 2026-10-20 · phase-18：Windows评测前运行恢复与连接核验

- 作者要求保证当前本机连接可用，为后续RAG评测做准备。先读当前状态和运行规范，保留既有未提交修改；未读封存题、未改题集/评分/Prompt、未安装依赖或调整预算。
- 初查Docker引擎未启动，本机REST不可达。Docker启动先后被遗留的dockerInference与engine.sock阻塞；经绝对路径校验，将临时运行目录可恢复备份，结束本轮失败实例后同时备份两处再启动成功。仅启动原有grounded_rag-db-1，未重置Docker或数据库卷。决定和恢复边界见[context](context/phase-18-windows-readiness-context.md)。
- AC1：`backend/.venv/Scripts/python.exe .cache/readiness-2026-10-20/environment.py`及`database.py`成功；读取了CUDA、依赖、配置、数据库版本、迁移和语料/向量数量。Langfuse认证成功，密钥只经Settings使用。
- AC2/AC3：后台启动既有uvicorn工厂，绑定本机8000并保留服务；`smoke.py`经HTTP发起真实知识库问答，健康检查、问答和本地trace读取均为200。完整检索与生成未降级、非缓存、非拒答；首次生成被忠实度校验拦下，重生成后通过。云端读回根输出与本地回答一致，并包含全部步骤；链接、耗时、费用及观测数见[实测报告](context/phase-18-readiness-report.json)。
- 额外只检索探针通过，所有返回候选有精排分数。暖检索和首题含模型加载/重生成的耗时分开记录，未据此宣称正式性能。独立Langfuse连接记录明确标注不运行RAG。
- AC4：在backend执行`.venv/Scripts/python.exe -m poethepoet check`全部通过；`.venv/Scripts/python.exe -m poethepoet test-int`在独立测试库通过。实际通过数量与覆盖率见实测报告；本轮只更新本任务阶段文件、context、报告和本日志。
- 原始输出和服务日志：`.cache/readiness-2026-10-20/`；凭据、缓存、原始模型输出未提交。最终再次请求`/health`返回status=ok、database=ok。无外部输入阻塞；下一步由作者指定正式评测。

### 2026-10-20 · phase-19 T1：三套评测启动

- 作者明确授权按70开发、20回归、30测试依次跑完整系统与Claude评审，保持题集、评分、Prompt、业务代码和预算，先每套前三题；本轮明确不提交Git。
- 已读Claude复审第7节与runbook正式运行说明；`claude --version`返回2.1.304，`claude -p`连接探针返回合法JSON。数据库/DeepSeek已由phase-18真实验证，当前预算沿用原设置。
- 实际入口没有limit和仓库外输出参数；使用仓库外临时编排脚本调用原`scripts.eval_run.run`，只增加切片、缓存续跑、错误计数停机、输出位置和每进程云端开关。没有修改现有评测或业务源文件。开发题run-id为final-dev70，已开始前三题系统与Claude评审；原始状态在该轮status.json。
- 校准样本预先固定种子20261020：可回答、预期拒答、预期反问、预期纠正各先随机两题，再从剩余题随机十二题；抽样只来自开发/回归，名单在查看评审分数前写入仓库外calibration-plan.json。
- 测试题仅在指定执行进程加载；云端关闭、原始日志/回答/标签/报告存仓库外。仓库内最终只可放聚合指标与ID错误清单，不放测试题干或回答。三套结果互不合并，全部标初步结果，等待作者人工校准。

### 2026-10-20 · phase-19：开发70完成，进入回归20

- final-dev70已完成全部系统调用、Claude标签和错误归因；系统/评审/归因均无错误，输入与源文件哈希复核通过。指标、分母与费用见[开发报告](../.cache/eval/runs/final-dev70/full/report.md)及同目录metrics.json；均为未人工校准的初步结果。
- 原始入口报告另存raw-report.md，正式report.md补充完成计数、分母和已知限制；只读调用原评分函数整理，没有增加一轮评审。开发云端原始回答/步骤与Claude标签分数正在逐条上传读回核验。
- 按顺序启动final-reg20，前三题作答完成，Claude试跑评审进行中；缓存目录独立。测试集尚未执行，未产生测试云端记录。没有提交Git。

### 2026-10-20 · phase-19：回归20完成，校准样本交付，测试开始

- final-reg20全部作答、Claude评审与归因完成，无错误，源文件/题集哈希未变；报告在`.cache/eval/runs/final-reg20/full/`。开发70的回答、全部步骤和Claude初步分数已全部云端读回，回执在该轮cloud-verification.json；回归云端核验随后也全部通过。
- 仓库外`eval-final-20261020/calibration-sample.md`已生成并打开。固定种子20261020、预先冻结的20个ID，预期类别为可回答14、拒答/反问/纠正前提各2；只转录原题、要点、实际回答及Claude原始标签，人工栏留空。
- 测试执行前已告知作者关闭云端；独立进程清空Langfuse两项凭据并断言客户端未启用，manifest中cloud_enabled=false。原始输出实际位于本聊天仓库外`eval-final-20261020/test-storage/eval/runs/final-test30/full/`，不写测试题干或答案到仓库。
- 测试前三题首次作答与评审均通过，续跑只处理其余题，试跑缓存复用；不重跑测试、不据结果调整系统。所有分数仍为初步结果，未提交Git。

### 2026-10-20 · phase-19 T2/T3完成：三套初步结果与交付核对

- 三套均完成系统作答、Claude逐点/行为评审与原入口归因，无系统、评审或归因错误；原始输入与全部源文件哈希复核未变。每套report.md、raw-report.md、metrics.json、manifest.json独立保留，具体数字只见各套报告与仓库外overview.json。
- 实际运行`eval-final-20261020/deliver.py`整理三套报告、overview.md、lowest-10.md、旧20逐题对照及此前冻结的校准样本；没有重新调用系统或评审。校准文件已打开给作者，之后不覆盖可能填写的人工备注。
- 实际运行`eval-final-20261020/audit.py`全部通过：每套回答/标签数量与唯一ID完整、源文件/题集哈希未变、原报告汇总行一致、测试云端关闭且原始输出仓库外、仓库内测试输出不含题干或回答、校准样本名单与原始转录一致。audit.json在统一交付目录。
- 云端：cloud_publish.py分别核验开发和回归所有回答/步骤与分数；verify_cloud_labels.py使用scores.get_many的details字段批量读回标签元数据，与本地逐字段一致。测试未创建云端客户端或映射文件，不上传测试内容。
- 最终再次`GET http://127.0.0.1:8000/health`成功，数据库正常；没有更改预算或业务配置。Git HEAD与运行前一致、无暂存项，按作者要求没有提交。阶段决策、目录和方法限制见[context](context/phase-19-final-evaluation-context.md)。
- 当前工作已交付；下一步是作者人工抽查校准，不据测试结果重跑或调整系统。所有数值均保持“初步结果”，不冒充已校准成绩。

### 2026-10-20 · phase-20 T1/T2：judge v2与只读重评入口

- 作者明确批准评审输入/Prompt改动；已读Claude校准预标，只用开发/回归分歧确定v2。新增judge_v2.md，v1原文件未改；contexts按原父块顺序拼接，含截断标记的总长受限，无资料时明确标记。标签定义与输出结构其余不变。
- Judge/evaluate新增可选contexts与模板参数，默认仍走v1；回归测试用改动前提示词SHA验证默认逐字一致，也覆盖回答含字面量占位符的兼容边界。原评分规则、题集、evidence、业务和预算均未改。
- 新增scripts.rejudge：只读旧answers及v1标签；原子创建新输出目录，已存在则拒绝，测试产物不得位于仓库内；前三题成功后复用标签评整套。完整列出两向矛盾翻转与其他标签变化，错误单列，不初始化系统/检索/云端或DeepSeek。
- 红灯：新增Judge/evaluate测试因缺参数失败；脚本测试因入口缺失失败。实现后定向测试通过；首次静态检查发现异步文件I/O、合成测试类型与断言问题，按要求修复，没有加忽略或降低门槛。随后完整poe check通过；最终数字与模板冻结摘要在仓库外eval-rejudge-v2-20261020的交付证据中记录。
- 已冻结v2模板和实现哈希、保护v1三套结果/评分/题集/业务/预算哈希；新种子20261021校准名单已在看v2标签前确定。执行uv run --no-sync python -m scripts.rejudge的final-dev70-v2命令开始真实重评，日志在仓库外dev70.log。--no-sync保留当前依赖，不执行依赖安装或升级。
- 未提交Git；测试原文和产物保持仓库外。v2校准由作者/Claude完成，本任务不宣称已通过。

### 2026-10-20 · phase-20：Claude CLI额度阻塞与可恢复断点

- 开发前三题v2试评无技术错误后复用标签继续；dev057起连续JudgeError。错误超过10%后停止仅本轮rejudge及其Claude子进程，没有启动回归/测试，也没有换模型。
- 不含题目的CLI探针明确返回会话用量限制，提示2026-10-20东京23:50恢复；原文保存在仓库外claude-diagnostic.txt。不是数据库、系统或评分代码失败，不通过改Prompt、降低门槛或换评审绕过。
- 实际运行断点整理脚本：成功36条、日志确认错误18条、无已落盘标签16条（含中断时可能在途题）。已将部分report.md、flips.md、metrics.json及错误清单更新到新v2目录；v1三套文件不改。当前不是完整三套结果，校准样本v2及全量原回答spot-check仍待全部重评完成。
- 仓库外checkpoint.json/checkpoint.md保存ID、计数与恢复说明；resume_dev70.py已做语法检查但未运行，恢复后只续评缺失标签，保存初始限额错误，不重复成功标签。正式rejudge入口仍拒绝已存在目录。
- checkpoint-audit.json实际核验通过：v1回答/标签/报告、scoring、业务、题集/evidence、DeepSeek预算均未变，v2冻结实现/模板也未变。未提交Git。已向作者询问23:50后自动续评还是稍后手动继续，等待偏好回复。

### 2026-10-20 · phase-20：作者选择手动续评，暂停

- 作者明确回复“稍后手动继续”；已保存手动恢复偏好，不创建自动续评或定时任务。当前36条成功v2标签与部分报告保留，回归/测试尚未启动。
- 暂停期间不再调用Claude或更改实现。恢复前先核验额度和冻结哈希；最终仍需完成全部三套、完整双向翻转、校准样本与spot-check，并保留初次额度错误记录。外部审计脚本还需将模板摘要检查改为明确的冻结值比较，作为交付核对待办。

### 2026-10-20 · 跨电脑提交与审查交接

- 作者明确要求将现有工作提交并推送到 GitHub，供换电脑拉取后由 Claude 检查；此授权取代此前“不提交 Git”，不改变“稍后手动继续”评测的选择。本次没有调用真实评审或系统。
- 汇入现有开发题修复、评测接线、v2实现及单元测试，补齐此前被通用 build/ 规则忽略的 phase-19/20 阶段文件；新增 `harness/context/phase-20-cross-computer-review.md`，说明暂停断点、审查入口及外部脚本尚待修复之处。
- 本次重新运行 `backend/.venv/Scripts/python.exe -m poethepoet check`：ruff格式与lint通过、lint-imports 1 kept / 0 broken、mypy 158源文件通过、449 passed / 35 deselected、覆盖率94.93%；`git diff --check`通过。
- 仓库外生成 `grounded-rag-eval-handoff-20261020.zip`，83个既有文件，5310342字节，SHA-256 `7997b2acd4097ce48b70ea118a008364e925ff754e691935811bcffa4c6f8674`；ZIP完整性及每文件哈希均核验。包含原始缓存和仓库外测试文件，供作者单独复制，不加入Git。包内含路径映射说明与清单，不含.env、密钥、模型和数据库。
- Git只迁移代码与允许入库的文档。开发v2仅有36条成功标签，18条明确错误及16条无标签，回归/测试v2未启动；完整新校准样本和spot-check尚未完成。单独pull不能取得这些本地缓存，不能据此视作评测已完成。

### 2026-10-20 · phase-20审查后修复（未真实续评）

- 根据作者要求修复并准备推送，真实评审交另一台电脑Claude。本机真实评审调用0，未启动系统/检索，未读取测试结果调提示词。作者原指令二/1/d明确批准support说明，保留模板和36条标签，不能照转述审查把它记为越权。
- rejudge增加finally保护文件复核、冻结清单起止核验与自身防改、逐题错误落盘、独立历史错误、完整阶段超过10%停机、经哈希验证的--seed-run向全新目录迁移。旧v1/v2目录不覆盖。flips单列所有nuggets变化，不能把混合改动的分差全部归因于contexts。
- 新增scripts.rejudge_artifacts与scripts.audit_rejudge，完整清单显式核验；缺键、多键、重名或哈希不等均失败。对应失败单测通过。新版外部audit_v2委托该审计，原错误表达式仅在历史原件中保留，旧脚本不再执行。
- 最终 backend/.venv/Scripts/python.exe -m poethepoet check：ruff格式/lint通过、lint-imports 1 kept / 0 broken、mypy 162文件通过；463 passed / 35 deselected，覆盖率94.93%。实际dev缓存只读迁移预检：70题输入、36条成功标签逐字节保留、18条历史错误保留，禁止创建评审器的断言未触发。新版全量交付脚本仅做语法检查，尚未执行完整交付审计，因为三套未完成。
- 原受保护文件逐项哈希未变，Judge/evaluate/模板与旧v2冻结一致。新冻结清单记录159ab99来源基础及旧清单SHA，不篡改旧HEAD或原冻结。
- 新版仓库外迁移包 grounded-rag-eval-handoff-20261020-repaired.zip：96文件，5457105字节，SHA-256 87fae93feb1f0f179ae6c1d2ae5d0340a4c3977d34ce0e88bee20bd01da33ad9，逐文件哈希与ZIP完整性通过。旧包只读。新版运行工具在eval-rejudge-v2-repaired-20261020，Git存完整源码审查副本及交接说明，不含缓存、密钥和测试原文。
- 当前仍未收尾：Claude先复审；真实评审时dev缺失34条→reg20→仓库外test30；然后三套报告/对照、完整双向flips和nuggets变化、固定种子20261021的20条dev/reg校准样本、全部true→false原回答核查。历史18条错误必须保留，整题校准至少17/20一致才达到85%。下一台电脑所需提示词见harness/context/phase-20-claude-recheck-prompt.md。

### 2026-10-20 · phase-20真实结果接收与Windows收尾核验

- 已fast-forward拉取Claude的97623e6，仅新增两份审查文档。确认原修复迁移包不含Mac新增结果后，作者提供D:/Chrome_Downloads/grounded-rag-v2-results-mac-20261020.zip。包41文件，SHA-256 bd6bfa8e4fa55a733001719ea7b9fc6356ca09751615180ba23018a653b8da06，CRC/安全路径/重复项/符号链接检查通过；解压在仓库外。
- 使用原scoring/summarize从三套120条原标签重算v1/v2六行全部汇总及95%区间，与comparison.json逐字段相等；各套metrics.json和等价来源Recall@5也一致。当前错误均0；36条旧标签保持一致，开发新增34条；18条历史限额错误原文保留。
- Windows原保护文件82/82原始SHA精确匹配，6个冻结实现文件匹配，无需放宽CRLF。原版audit_v2.py源码字节不改；仅在派生manifest副本做Mac路径映射，所有预期哈希原值不改，原包/manifest/标签保留。实际运行退出0，all_passed:true：三套完整、26题标签变化、10条true→false及1条反向、固定20条样本完整性、来源关系和历史错误均通过。完整日志和路径映射证明留在仓库外eval-closeout-20261020。
- 全部10条正向翻转和1条反向翻转已逐题核查，15个逐点变化已单列；发现仍有概括性冲突和partial/support边界，原标签/分数均未改，未据测试调系统。含测试的原回答和核查只写仓库外。
- 在读取Mac最终v2标签前冻结20条dev/reg独立预标，种子20261021，SHA-256 e319bd11aa2078e1cac86251c670543fbb199c07c42bcb4f6b0314aa82061aeb。五字段整题16/20一致＝80%，未达85%；分数20/20一致仅作诊断，不替代门槛。四分歧为dev054/dev089/dev030/dev008。Codex参与实现，这只是agent预标，不是独立人类校准，未改预标或重抽样本。
- 实际收尾质量检查：backend/.venv/Scripts/python.exe -m poethepoet check → ruff格式/lint通过，lint-imports 1 kept / 0 broken，mypy162文件通过，463 passed / 35 deselected，覆盖率94.93%。本轮真实模型调用0，系统/检索调用0，业务/评分/模板/题集/evidence未变。
- 仓库外封存grounded-rag-v2-closeout-20261020.zip：60个文件，5778891字节，SHA-256 184666976126900cd9b215fc0692040b9bef8f09360edcc539d15057fd29c62f，ZIP及每文件哈希核验通过。含两份未经修改的来源包、重算/审计、盲预标、人工空白表和逐题核查；不加入Git。
- 技术交付可以归档；正式人工校准未完成，不能将v2标成最终成绩。作者/独立标注者用仓库外calibration-human-blank.md标固定20条，按事先整题口径至少17/20一致才达到85%。当前唯一剩余外部输入是参考标注/裁决，不需要再跑系统或真实评审。详情见harness/code_review/2026-10-20-judge-v2-windows-closeout.md。

### 2026-10-20 · phase-20作者复核样本校准与结项

- 作者完成仓库外calibration-prelabel-v2.md全部20条人工裁决。dev089原写“算啊，同意Codex”，经明确字段询问，作者在聊天确认“true：算纠正前提，同意 Claude”；最终按该澄清转录，原标注文档逐字节另存不改。方法为作者复核预标，非盲标，不称独立人工盲标。
- 仓库外finalize_human_calibration.py逐题核对固定种子20261021的原20条顺序、冻结预标SHA、原Claude标签；与人审前归档比较，除人工裁决行外正文及两版标签没有变化。按nuggets/contradiction/behavior/corrects_premise/covers_interpretations五字段整题一致计算18/20＝90%，达到既定85%门槛；未重抽、未删字段、未修改原标签。剩余dev054与dev008分歧保留，20条原规则分数一致仅作诊断，不替代整题门槛。
- 新增结构化作者参考及原标注、human-calibration-result.md、final-report.md；参考SHA-256为b235d3075bee1352a947cc16a66a53aefc82449c86080247db2c2607cb3636aa。原独立预标80%、旧36条、首次18条错误、三套v1/v2原始结果和全部核查风险均保留。该90%是评审样本与作者参考一致率，不是RAG准确率，也不是120条全量人工验收。
- 实际执行python package_final_calibration.py，新建仓库外grounded-rag-v2-final-20261020.zip：11文件、5796279字节，SHA-256 7694907f0c8205c084c09dffc8537d4505a71b5d3e9be6e55bde961ae25fe438；CRC及清单中每文件SHA全部通过。内嵌此前技术归档原字节，保留全部原始证据；包与含测试原文的材料均不进Git。
- 本次只做作者裁决转录和文档归档，真实模型/系统/检索调用均0，业务/评分/模板/题集/evidence均未变。最近完整代码质量检查仍为463 passed / 35 deselected、覆盖率94.93%，不重复运行无改动的代码测试。代码复审、三套真实重评、原函数复算、Windows严格审计、完整核查及约定样本校准均完成，本轮按既定范围结项。
