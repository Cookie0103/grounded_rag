# 开发日志（build-log）

> **进度的唯一依据**：只记观察到的事实（命令、输出、提交），不记计划。计划在 [build/](build/)，决策原因在 [context/](context/)。
> 追加规则：下面「活动记录」只追加、不改写旧条目；阶段状态表可以改。每个阶段完成时必须有验收证据才能标「完成」。

## 当前状态（先读这里）

最后更新：2026-10-19（phase-16进行中：修订24题并补齐剩余46题）

- **代码**：phase-00～09 全部完成，分支 `2026-10-16-framework-build`，CI 绿；没有 PR，没合并 main（作者说之后再说）。
- **当前任务**：[phase-16](build/phase-16-dev70-completion.md) 进行中。作者已转交Claude复审并授权自主修订指定旧题、先校验46题蓝图后一次补齐dev045～090；不再每12题停审。固定182篇语料已在本机恢复并核对Git blob，现有模型在Mac MPS通过冒烟，数据库向量恢复进行中。旧题修订、蓝图和机械校验正在独立核验；尚未完成新增46题或检索自测。
- **本轮**：分支 `2026-10-19-cloud-tracing` 完成 [phase-11](build/phase-11-cloud-tracing.md) 的 T1～T4：补齐过程记录，真实本地问答、Langfuse 日本区上传及云端 API 读回均成功。作者要求汇总推送后，既有4项未提交修改已提交为`433ae94`，该分支首次推送到origin成功并建立跟踪；未检查远程CI结果。
- **评测准备**：[phase-12](build/phase-12-evaluation-dataset.md) 完成。作者确认的五项能力指标在 [metrics-v1](../docs/eval/metrics-v1.md)，指定Notion已整理为唯一表格化方案。[20道开发题草案](../docs/eval/dev20/README.md) 及51个要点已执行首轮试评，118条事实逐项核验。当前结果属于agent辅助诊断，作者金标审核、人工校准和通用E/F/C自动评审仍未完成。
- **本机配置**：当前Mac已恢复锁定Python依赖与原定Qwen3嵌入/精排，MPS真实冒烟通过。本项目PostgreSQL/pgvector在5432，182篇/1252父块/2090子块及2090条Qwen3向量已恢复并与源全量比对；未补本轮不需要的BGE向量。`.env`保留作者设置，任务命令临时使用MPS和batch=4。旧Windows/RTX5070Ti及Langfuse结果为另一台电脑的历史证据。
- **旧20结果**：[phase-13首轮档案](../docs/eval/results/runs/2026-10-19_1855_dev20_full-service/README.md)及Langfuse核验保留，不改冻结快照。作者新口径为20回归 + 70新开发 + 30测试，共120题；旧20不计入新70，原初评数字不作新70对外成绩。
- **下一步**：统一校验46题蓝图，替换薄弱链式候选 → 两组各23题及证据 → 原题不传edition单次检索 → 完整70题独立复核与交审。正式评分的OR来源适配和作者/Claude审定仍是后续步骤。
- **当前手动试跑**：已按作者要求保持 `poe serve` 在 http://127.0.0.1:8000 运行，`/health` 与 `/chat` 已真实验证。后续先检查 8000 是否已有服务，避免重复启动。作者可在 `/docs` 用独立 session_id 手动检查完整步骤，再准备首批开发题。
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
