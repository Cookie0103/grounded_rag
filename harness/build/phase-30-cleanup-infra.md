# 阶段 30：清场与基础设施

状态：完成（本地分支 `2026-11-18-local-infra`）

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
- [x] T3 compose：新增 `es`（自建镜像，装 `analysis-kuromoji`，单节点、关安全认证、堆内存设 1g）、`redis`、`mysql`、`gateway`（LiteLLM Proxy，配置文件入库、密钥走 `.env`）。全部带 healthcheck，端口可用环境变量覆盖。
- [x] T4 配置：`core/config.py` 与 `.env.example` 增加 ES、Redis、MySQL、网关地址与 key、大小模型名。
- [x] T5 小模型：在 Mac 上用 Ollama 测两款 4B～8B 候选。两款用同一提示词、同一组 20 条合成日文冒烟题、相同预热与串行请求方式，按准确率和耗时定稿，记录 GPU 与内存占用。
- [x] T6 `providers/`：新增走网关的对话客户端（先只要非流式 `complete`，流式放阶段 35），假实现同步；工厂按档位（`small` / `large`）取模型。预算与记账沿用现有逻辑。
- [x] T7 文档：`PROMPTS.md` 里与 Dify 文档强绑定的段落标注「第一版，待阶段 36 更新」。

## 需要作者做的

无。若 DeepSeek 网关真实调用失败，记录实际错误和待补输入后暂停。运行主机变更见[阶段 30 环境记录](../context/phase-30-mac-context.md)。

## 记录

- AC1 经 `git status --short` 确认归档迁移，根 README 改为住宅贷款 Copilot 定位和基础设施启动说明。
- AC2 执行 `docker compose up -d --build --wait --wait-timeout 120` 成功，`docker compose ps` 显示 DB、ES、Redis、MySQL、网关全部 healthy。`docker stats --no-stream` 的单次内存快照依次为 82.29 MiB、1.549 GiB、11.13 MiB、431.3 MiB、625.9 MiB。
- AC3 在 ES 容器运行 `bin/elasticsearch-plugin list` 得到 `analysis-kuromoji`。向本机 ES 的 `/_analyze` 发送 `{"analyzer":"kuromoji","text":"住宅ローンの繰上返済を確認します。"}`，返回词元 `住宅 | ローン | 繰上 | 返済 | 確認`。
- AC4 在 `backend/` 运行 `uv run --locked python -m scripts.phase_30_models --gateway`，两个请求均 HTTP 200 且返回文本。Ollama 输入 19、输出 4 token，DeepSeek V4 Pro 输入 14、输出 3 token，按高峰单价保守记账 ¥0.000219。无凭据访问网关模型列表得到 HTTP 401。
- AC6 在 `backend/` 执行 `UV_NO_CONFIG=1 UV_OFFLINE=1 UV_CACHE_DIR=../.cache/uv uv run --locked poe check`，格式、lint、分层和类型通过，465 个测试通过，覆盖率 94.93%。本机全局 uv 配置和锁文件保持原样。
- AC7 按阶段环境记录完成 MPS 嵌入、精排推理。相同 uv 环境运行 `uv run --locked poe test-int`，独立测试库 32 个测试通过。`docker buildx imagetools inspect` 与 `docker image inspect` 分别核对发布清单和运行镜像，五个服务均为原生 `linux/arm64`。
- 待替换的第一版语料代码为 `backend/scripts/fetch_docs.py`、`backend/scripts/export_for_gemini.py`、`backend/app/ingest/fetch.py`、`backend/eval/smoke_retrieval.jsonl` 及旧语料命令入口。保留到阶段 31 或 32 的替代路径通过后处理。
- 按作者确认更新 GOALS 和 PLANS 的运行环境及第 37 阶段对照范围。开发在本地当天分支，历史 Windows 延迟只作背景。

### 小模型冒烟（AC5）

用 `OLLAMA_CONTEXT_LENGTH=4096 ollama serve` 启动主机端 Ollama。在 `backend/` 各运行一次 `uv run --locked python -m scripts.phase_30_models --ollama-model <模型标签>`，每款模型预热一次后串行测试同一组 20 条 `synthetic` 日文短题。P95 取最近秩，GPU 和内存读自 `ollama ps`。

| Ollama 模型 | 准确率 | 延迟中位数 | P95 | 模型占用 | GPU |
|---|---:|---:|---:|---:|---:|
| `qwen3:4b-instruct` | 19/20（95%） | 91.4 ms | 95.2 ms | 3.2 GB | 100% |
| `qwen2.5:7b` | 18/20（90%） | 126.9 ms | 128.4 ms | 4.8 GB | 100% |

选用 `qwen3:4b-instruct`，本次正确数更多、耗时和内存占用更低。全部样本输出保存在本机 `.cache/ollama/benchmark-4k-*.log`，网关和容器输出在 `.cache/phase-30-gateway.log` 与 `.cache/phase-30-runtime.log`。官方权重 CDN 曾短暂 DNS 失败，恢复后断点重试完成。

## 阻塞

（无）
