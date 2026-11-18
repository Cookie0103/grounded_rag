# 阶段 30：清场与基础设施

状态：已批准，执行中（本地分支 `2026-11-18-local-infra`）

> 这是计划和记录，不是完成证据；进度以 [build-log](../build-log.md) 为准。设计依据见 [PLANS.md](../../PLANS.md) §1、§2、§4.6。

## 需求

### 目标

1. 把第一版（Dify 文档问答）专属的内容归档或删除，让仓库里不再有两套互相矛盾的说明。
2. 本地基础设施一条命令起齐：PostgreSQL（已有）、Elasticsearch（带 kuromoji）、Redis、MySQL、模型网关。
3. 选定并跑通小模型档，确认问答服务能经网关调用大小两档模型。

### 非目标

- 任何业务逻辑改动（语料、检索、编排都在后面的阶段）。
- 启动 Dify（阶段 37 才起）。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | 第一版专属文档已归档到 `harness/archive/v1-dify-docs/`，根目录与 `docs/` 不再出现 Dify 文档问答的说明 | `git status`、目录清单 |
| AC2 | `docker compose up -d` 后五个服务全部 healthy | `docker compose ps` 输出 |
| AC3 | ES 能用 kuromoji 分词日文 | `_analyze` 一句日文，输出词元 |
| AC4 | 经网关各调用一次小模型和大模型，返回正常且有 token 用量 | 脚本输出 |
| AC5 | 小模型的意图分类单次耗时有实测值 | 20 次调用的中位数与 P95 |
| AC6 | `uv run poe check` 通过 | 命令输出摘要 |
| AC7 | 嵌入和精排经现有提供方在 MPS 实际完成推理；原生 arm64 容器通过集成测试 | 本机推理输出、镜像实际架构、`uv run poe test-int` |

## 任务

- [x] T1 归档：`导学-grounded-rag.md`、`面经-grounded-rag.md`、`docs/eval/`、`docs/final-report-template.md`、`backend/eval/reports/` 用 `git mv` 移到 `harness/archive/v1-dify-docs/`。同时归档旧 README，根目录写当前定位和基础设施启动步骤；完整运行手册留到阶段 38。
- [x] T2 标记待替换代码：`scripts/fetch_docs.py`、`scripts/export_for_gemini.py`、`ingest/fetch.py`、`eval/smoke_retrieval.jsonl` 等只服务 Dify 语料的文件，本阶段只在记录里列清单，不删；删除放到替代实现落地的阶段。
- [ ] T3 compose：新增 `es`（自建镜像，装 `analysis-kuromoji`，单节点、关安全认证、堆内存设 1g）、`redis`、`mysql`、`gateway`（LiteLLM Proxy，配置文件入库、密钥走 `.env`）。全部带 healthcheck，端口可用环境变量覆盖。
- [x] T4 配置：`core/config.py` 与 `.env.example` 增加 ES、Redis、MySQL、网关地址与 key、大小模型名。
- [ ] T5 小模型：在 Mac 上用 Ollama 测两款 4B～8B 候选。两款用同一提示词、同一组 20 条合成日文冒烟题、相同预热与串行请求方式，按准确率和耗时定稿，记录 GPU 与内存占用。
- [ ] T6 `providers/`：新增走网关的对话客户端（先只要非流式 `complete`，流式放阶段 35），假实现同步；工厂按档位（`small` / `large`）取模型。预算与记账沿用现有逻辑。代码和单测已通过，待真实连接验证。
- [x] T7 文档：`PROMPTS.md` 里与 Dify 文档强绑定的段落标注「第一版，待阶段 36 更新」。

## 需要作者做的

无。若 DeepSeek 网关真实调用失败，记录实际错误和待补输入后暂停。运行主机变更见[阶段 30 环境记录](../context/phase-30-mac-context.md)。

## 记录

- AC1：`git status --short` 确认归档迁移；根 README 改为住宅贷款 Copilot 定位和基础设施启动说明。
- AC6：在 `backend/` 执行 `UV_NO_CONFIG=1 UV_OFFLINE=1 UV_CACHE_DIR=../.cache/uv uv run --locked poe check`，格式、lint、分层和类型通过；465 个测试通过，覆盖率 94.93%。本机全局 uv 配置和锁文件保持原样。
- AC7 部分：按阶段环境记录完成 MPS 嵌入、精排推理。相同 uv 环境运行 `uv run --locked poe test-int`，独立测试库 32 个测试通过。用 `docker buildx imagetools inspect` 确认阶段 30 的五个基础镜像均发布原生 `linux/arm64`，待验证实际启动架构。
- 待替换的第一版语料代码为 `backend/scripts/fetch_docs.py`、`backend/scripts/export_for_gemini.py`、`backend/app/ingest/fetch.py`、`backend/eval/smoke_retrieval.jsonl` 及旧语料命令入口。保留到阶段 31 或 32 的替代路径通过后处理。
- 按作者确认更新 GOALS 和 PLANS 的运行环境及第 37 阶段对照范围。开发在本地当天分支，历史 Windows 延迟只作背景。

## 阻塞

（无）
