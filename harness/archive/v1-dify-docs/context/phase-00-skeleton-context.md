# 阶段 00 决策记录：工程骨架与全局约定

> 对应计划：[phase-00-skeleton](../build/phase-00-skeleton.md)。只记「为什么这样定」，已定的事不要重新讨论；推翻时直接改那一行，写上日期和原因。

| 日期 | 决策 | 理由 |
|---|---|---|
| 2026-10-15 | 只做 RAG，不做 Agent runtime、多智能体、多模态 | 聚焦范围，评测故事讲得清 |
| 2026-10-15 | 对外只提供 REST + MCP，不做 SDK | YAGNI |
| 2026-10-15 | 嵌入和精排在本机 GPU 运行，只有 DeepSeek 走 API | 成本低，可做模型对比 |
| 2026-10-16 | 不做前端；演示用 FastAPI 的 `/docs` 和在 Claude Code 中调用 MCP | YAGNI |
| 2026-10-16 | 数据库访问用 SQLAlchemy 2.0（async，Core 风格）+ asyncpg + Alembic | 迁移可追溯，不用 ORM 的隐式行为 |
| 2026-10-16 | 静态检查用 ruff + mypy --strict + import-linter | 分层和风格交给工具检查 |
| 2026-10-16 | 只支持 Python 3.12，CI 不跑多版本矩阵 | 一个版本就够 |
| 2026-10-16 | 任务清单写在各里程碑的 Spec 里，不单独维护 TASKS.md | 避免两处不同步 |
| 2026-10-16 | API 不加版本前缀 | 只有一个版本 |
| 2026-10-16 | agent 调用 DeepSeek 每天不超过 ¥10；作者手动测试不限 | 控制夜间无人值守的成本 |
| 2026-10-16 | 仓库根目录放 `backend/`（含 app、tests、eval、scripts、migrations、pyproject）、`docs/`、docker-compose；将来前端放 `frontend/`；不用 src layout，包名 `app` | 归属清晰，加前端不用移动文件；Python 一切共用一套环境 |
| 2026-10-16 | 每天一个分支 `<日期>-<两个英文单词>`，从前一天的分支创建；PR 用 merge commit 按日期顺序合并 | 作者要求按天追溯；squash 会让叠起来的分支重复提交、产生冲突 |
| 2026-10-16 | 开发过程按天记在 `harness/archive/<日期>/`（2026-10-17 起改为追加到 `harness/build-log.md`） | 出问题可回溯；不在 docs 里到处散落带日期的文件 |
| 2026-10-16 | 不单独建 `docs/progress/`，里程碑总结写在其 Spec 的「记录」 | 少一处要同步的文档 |
| 2026-10-16 | 集成测试使用独立的测试库 `grounded_rag_test` | 不清空开发库里已入库的语料 |
| 2026-10-16 | LLM 默认用 `deepseek-flash`；预算按高峰价折算人民币 | 当前主力的便宜模型；估算偏保守 |
| 2026-10-16 | 开发由 Claude Sonnet 负责（Codex 可选），Opus 负责写规范和 Spec | 作者安排；Opus 用量贵 |
| 2026-10-16 | 暂不合并到 main、不开 PR；只提交到当天分支；CI 对任何分支 push 都运行 | 作者决定；GitHub 的合并设置之后再说 |
| 2026-10-16 | 本机 5432 被 Windows PostgreSQL 占用，compose 用 `DB_PORT=15432`（5433 也被本机的另一个 PostgreSQL 占用）（只在本机 `.env`） | 不动用户已有的服务 |
| 2026-10-16 | PyTorch 用 cu130（torch 2.14.1），不是 cu128 | cu128 最高只到 2.11；驱动支持 CUDA 13.3；RTX 5070 Ti 已验证可用 |
| 2026-10-16 | 取消「Spec 批准」和「先问」关口：agent 自己写 Spec、自己批准、按里程碑连续做到最后；只有缺外部输入（API 密钥、Gemini 出的题、真实评审）时才停，先把能做的做完、最后一起报告 | 作者要求长程任务不要再问；见 AGENTS.md 权限表 |
| 2026-10-16 | 回答、文档、日志一律用中文 | 作者要求 |

## 本机环境（接手前先确认）


- 仓库：`D:\项目\秋招项目\SONY\grounded_rag`，分支 `2026-10-16-framework-build`（按天开分支：明天从这个分支创建 `2026-10-17-xxx-yyy`）。没有开 PR、没有合并 main（作者说之后再说）。
- 开发库是 docker 里的 `grounded_rag-db-1`（`pgvector/pgvector:pg16`），端口 **15432**（5432 / 5433 被 Windows 上的 PostgreSQL 占了，别动它）。端口写在仓库根目录的 `.env`（不提交）：`DB_PORT=15432`、`DATABASE_URL=...:15432/...`。Docker Desktop 没开就先启动它：`docker compose up -d db`。
- 在 `backend/` 下执行所有命令：`uv run poe check`（格式、lint、分层、类型、单元测试）、`uv run poe test-int`（集成测试，自动建测试库 `grounded_rag_test`）、`uv run poe test-gpu`（本机 GPU）。
- GPU：RTX 5070 Ti，torch 2.14.1+cu130；模型缓存在 `.cache/models/`（Qwen3-Embedding、Qwen3-Reranker、bge-m3、bge-reranker-v2-m3 都已下载）。
- 语料：`data/raw/dify-docs/<commit>/zh/...` 已下载；开发库里已入库 182 篇（Qwen3 和 bge-m3 两套向量）。重新下载 `poe fetch-docs`，重新入库 `poe ingest`。
- 常用命令：`poe retrieve-demo`（真实模型的检索演示）、`poe compare-retrieval`（9 种检索方案对比）。

### 已知的坑

- 终端工具会吃掉 heredoc 里一层反斜杠（`"\\n"` 会变成换行），**别用 Python heredoc 改带反斜杠的代码**，用 Edit / Write 工具；一次写很多大 heredoc 也可能整条命令不执行。
- `ruff format` 会格式化 Markdown 里的 Python 代码块：pre-commit 里已限制只处理 `.py`，但手动在仓库根目录跑 `ruff format .` 会改动 docs。
- 修改 `app/core/config.py` 里的 `Settings` 字段要同步 `.env.example`（有测试检查）。
- 有两处故意的 `noqa: BLE001`（评测里被测系统 / 评审出任何错都不能让整轮评测中断），其余地方不要加 `noqa` / `type: ignore`。
- pytest 临时目录在 `.cache/pytest-tmp`（系统临时目录有权限问题）；`tests/conftest.py` 会先建好上级目录。
