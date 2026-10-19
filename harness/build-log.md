# 开发日志（build-log）

> **进度的唯一依据**：只记观察到的事实（命令、输出、提交），不记计划。计划在 [build/](build/)，决策原因在 [context/](context/)。
> 追加规则：下面「活动记录」只追加、不改写旧条目；阶段状态表可以改。每个阶段完成时必须有验收证据才能标「完成」。

## 当前状态（先读这里）

最后更新：2026-10-19（云端接入与真实运行核验）

- **代码**：phase-00～09 全部完成，分支 `2026-10-16-framework-build`，CI 绿；没有 PR，没合并 main（作者说之后再说）。
- **本轮**：分支 `2026-10-19-cloud-tracing` 完成 [phase-11](build/phase-11-cloud-tracing.md) 的 T1～T3：补齐粗召回/精排候选、各次生成和后处理；API/MCP/CLI 与评测接可选 Langfuse。代码和本地验证已完成，真实云端尚未验证，未推送或运行远程 CI。
- **本机配置**：作者已填 DeepSeek 密钥，真实调用通过；四个 GPU 模型实际推理通过。原数据库容器已启动，根目录 `.env` 的 DATABASE_URL / DB_PORT 已对齐 15432，语料和双模型向量完整。Langfuse 两项项目密钥仍缺，作者表示会配置；不要在日志或聊天暴露值。
- **没有的**：真实正式评测效果数字、作者题集及人工评审标注、Langfuse 真正接收记录的证据、最终静态站点。单题真实问答只是运行冒烟，不代表评测分数。清单见 [PLANS.md §8](../PLANS.md)，操作见 [runbook](../docs/eval/runbook.md)。
- **下一步**：作者填好 Langfuse 后验证真实上传，再准备首批 20 道开发题 → 补足 70 题 → 校准评审 → 冻结系统 → 作者只运行封存 30 题。最终静态报告选 GitHub Pages；测试结束前不公开封存题。
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
| [phase-11 云端观测](build/phase-11-cloud-tracing.md) | 阻塞（仅真实云端验证） | 本地实现与运行核验完成；Langfuse 凭据待作者填写 |

最终检查状态见下方 2026-10-19 活动记录。上次 GPU pytest（2026-10-16）为 3 passed；本轮另行真实离线加载四个 GPU 模型执行推理，未运行正式效果评测。

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
