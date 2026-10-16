# 交接记录（给下一个接手的模型或人）

> **这份文件是「现在做到哪了、下一步做什么」的唯一入口。** 每完成一个任务就更新并提交；用量快到上限（95% 以上）或要停下时，先把这里写完整再停。
> 接手的人：先读本文件，再读 `AGENTS.md`、`docs/workflow.md`、当前里程碑的 `docs/specs/Mx-*.md`，最后看 `docs/implementation-log/<今天>/README.md`。

最后更新：2026-10-16（M5 完成，M6 未开始）

## 一、总体进度

| 里程碑 | 状态 | 说明 |
|---|---|---|
| M0 工程骨架 | ✅ 完成 | `docs/specs/M0-skeleton.md` |
| M1 数据管线 | ✅ 完成 | 182 篇入库，2090 个子块；`docs/specs/M1-ingest.md` |
| M2 检索 | ✅ 完成 | 混合检索 + 精排 + `/retrieve`；`docs/specs/M2-retrieval.md` |
| M3 评测 | ✅ 完成（真实评审待作者提供后端） | `docs/specs/M3-evaluation.md` |
| M4 基线（无检索、朴素 RAG） | ✅ 完成（真实分数待密钥） | `docs/specs/M4-baselines.md` |
| M5 编排（路由、改写、分解、证据评分、生成、校验） | ✅ 完成（假模型；真实效果待密钥） | `docs/specs/M5-orchestration.md` |
| M6 记忆 | ⬜ 未开始 | |
| M7 服务与可靠性（SSE、MCP、缓存、降级、限流、压测） | ⬜ 未开始 | |
| M8 观测与坏例 | ⬜ 未开始 | |
| M9 收尾（README、一键复现、最终报告） | ⬜ 未开始 | 测试集由作者手动跑一次 |

完整计划见 `docs/proposal-2026-10-15.md` 第 7 节。每个里程碑开始前先在 `docs/specs/` 写 Spec（作者已授权自己批准），做完在 Spec 的「记录」里写验收结果和偏离。

## 二、下一步：M6 记忆

M5 完成。M6：先写 `docs/specs/M6-memory.md`（自批）。内容：多轮会话——短期记忆（最近几轮，超长时用模型摘要）、问题独立化（追问里的指代改写成完整问题）、用户偏好（自部署 / 云版本记在会话里并作为检索过滤）、会话存储（数据库表 + 迁移 0004，会话 ID，过期清理）；`ChatRequest` 加 `session_id`；`ChatPipeline` 在 guard 之后加 `standalone` 节点；评测里支持多轮题（先不做数据集，只做单元测试）。

## 三、阻塞项（需要作者提供，不要自己编）

1. **评测题**：作者用 Gemini 网页端出 100 题（开发集 70 / 测试集 30），放 `backend/eval/data/dev.jsonl`（只读）；测试集放仓库外。没有它，正式指标和模型对比结论都出不了。冒烟集只验证流程。
2. **DeepSeek API 密钥**：M4 起真实生成和 LLM 评审要用。放 `.env` 的 `DEEPSEEK_API_KEY`（M4 加这个配置项），不要提交。预算：agent 每天 ¥10，由代码统计强制（`providers/` 里记账，超了抛 `BudgetExceededError`）。
3. **评审后端**：Gemini 主评、Claude 复评。本机没有 `gemini` / `codex` / `cursor-agent`，只有 `claude`（`CommandPromptRunner(["claude", "-p"])` 可用，但会消耗作者的 Claude 用量，不要自动大量跑）。
4. **校准**：第一次跑完开发集后，作者人工标 20 条回答，评审一致率要 ≥ 85% 才能用自动评审比较方案。

没有这些时：把代码、假实现和测试做完，把阻塞写进当天日志和最终报告，**不要停下来等**，接着做下一个不依赖它们的任务。

## 四、本机环境（接手前先确认）

- 仓库：`D:\项目\秋招项目\SONY\grounded_rag`，分支 `2026-10-16-framework-build`（按天开分支：明天从这个分支创建 `2026-10-17-xxx-yyy`）。没有开 PR、没有合并 main（作者说之后再说）。
- 开发库是 docker 里的 `grounded_rag-db-1`（`pgvector/pgvector:pg16`），端口 **15432**（5432 / 5433 被 Windows 上的 PostgreSQL 占了，别动它）。端口写在仓库根目录的 `.env`（不提交）：`DB_PORT=15432`、`DATABASE_URL=...:15432/...`。Docker Desktop 没开就先启动它：`docker compose up -d db`。
- 在 `backend/` 下执行所有命令：`uv run poe check`（格式、lint、分层、类型、单元测试）、`uv run poe test-int`（集成测试，自动建测试库 `grounded_rag_test`）、`uv run poe test-gpu`（本机 GPU）。
- GPU：RTX 5070 Ti，torch 2.14.1+cu130；模型缓存在 `.cache/models/`（Qwen3-Embedding、Qwen3-Reranker、bge-m3、bge-reranker-v2-m3 都已下载）。
- 语料：`data/raw/dify-docs/<commit>/zh/...` 已下载；开发库里已入库 182 篇（Qwen3 和 bge-m3 两套向量）。重新下载 `poe fetch-docs`，重新入库 `poe ingest`。
- 常用命令：`poe retrieve-demo`（真实模型的检索演示）、`poe compare-retrieval`（9 种检索方案对比）。

## 四点五、已知的坑

- 终端工具会吃掉 heredoc 里一层反斜杠（`"\\n"` 会变成换行），**别用 Python heredoc 改带反斜杠的代码**，用 Edit / Write 工具；一次写很多大 heredoc 也可能整条命令不执行。
- `ruff format` 会格式化 Markdown 里的 Python 代码块：pre-commit 里已限制只处理 `.py`，但手动在仓库根目录跑 `ruff format .` 会改动 docs。
- 修改 `app/core/config.py` 里的 `Settings` 字段要同步 `.env.example`（有测试检查）。
- 有两处故意的 `noqa: BLE001`（评测里被测系统 / 评审出任何错都不能让整轮评测中断），其余地方不要加 `noqa` / `type: ignore`。
- pytest 临时目录在 `.cache/pytest-tmp`（系统临时目录有权限问题）；`tests/conftest.py` 会先建好上级目录。

## 五、给接手模型的建议

- 每个任务：先写测试 → 实现 → `uv run poe check` → 提交（提交信息结尾带 `Co-Authored-By`，见 AGENTS.md 开头的说明）→ 更新本文件 → 推送。
- 里程碑做完：Spec 勾选 + 写「记录」，在 `docs/implementation-log/<日期>/README.md` 补「做了什么 / 困难与解决 / 查阅资料 / 验收证据 / 遗留」，`docs/decisions.md` 记新决定，必要时更新 `docs/proposal-2026-10-15.md`。
- Notion「开发计划_Polish」页面是给作者看的，里程碑完成时在页首的绿色进度框里更新一行。
- 回答、文档、日志都用中文。
