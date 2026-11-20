# 换机复现与工程复盘

这份手册面向接手第二版的开发者。先核对冻结版本、挑选复现路径，再逐层验证本机服务。历史指标见 [Mac 本机实测报告](../eval/mac-poc-report.md)，每次启动或变更的证据见 [开发日志](../../harness/build-log.md)。

## 换机先准备什么

| 内容 | 在哪里 | 换机处理 |
| --- | --- | --- |
| 工程代码、提示词、评分实现、容器配置和阶段证据 | Git，交接分支 `2026-11-20-project-handoff`；冻结标签 `copilot-freeze-2026-11-20` 指向 `fdd5a5eb16e9fb1e7a4e10e9fba9f7e6881cb4c0` | 通过作者授权的代码传输途径取得分支和标签。保留交接分支阅读文档，使用冻结标签选定被测版本 |
| 依赖与打包 | `backend/pyproject.toml`、`backend/uv.lock`、`docker-compose.yml`、`infra/` | 在目标电脑重新同步锁定依赖、下载目标架构镜像。本地 `.venv/`、uv 的缓存和下载目录由目标电脑重建 |
| 密钥及环境 | `.env.example` 只列字段，实际值在本机忽略的 `.env` | 用目标机上的专用凭据填写 `DEEPSEEK_API_KEY`、`GATEWAY_API_KEY`，Dify 启用后再填本机 `DIFY_API_KEY`。端口、数据库地址、模型设备按目标机核对。Dify 管理员和模型表单凭据只放本地 |
| S/L 完整语料 | `data/raw/public/` 中的原始快照与清单，生成后的清单 `data/policy_index.jsonl`，出题材料包 `.cache/policy-question-pack.zip` | 作者按使用条件在自己控制的设备上恢复原有快照和文件指纹，然后重建索引。代码交接包不附公开原文、派生资料包或数据库卷 |
| 实测原始证据 | `.cache/copilot-eval/`、`.cache/copilot-dev/`、`.cache/dify-evidence/` 和 `.cache/litellm-usage/` | 聚合报告可以用于交接。原始观察含逐题内容，Dify 实例导出和截图也可能含本机配置，留在作者控制的本地环境。运行所需的配对校准文件见 [作者手册](../eval/copilot-author.md) |
| 付费账本和封存数据 | `.cache/budget/`；封存题与封存运行目录在仓库之外 | 同日使用同一个付费账户换机时，保持账本和账户当日用量连续，停止旧机付费运行。封存材料由作者独自保管，向开发者交付聚合结果 |

目标机运行前，可用以下命令核对版本。冻结标签保留在本地的场景，由作者通过私有 Git 交接或在核对完整提交号后在新机重建该标签。

```bash
git status --short --branch
git rev-parse 'copilot-freeze-2026-11-20^{commit}'
git diff --name-only copilot-freeze-2026-11-20 -- backend mock_core infra docker-compose.yml .env.example
```

冻结标签应解析到上表的 40 位值。最后一条不会因交接文档更新产生输出，出现程序差异时先核对使用的检出版本。使用未公开的私有交接包时，可以在独立目录用 `git clone <私有Git交接包路径> <新工作目录>`，并检查本地分支和标签是否齐全。 [阶段 38 验收](../../harness/build/phase-38-wrapup.md)

## 先用纯合成模式验证新电脑

按 [README 的纯合成启动步骤](../../README.md#用纯合成语料启动) 操作。使用新克隆或独立副本，尤其要避免覆盖用于完整评测的 `data/policy_index.jsonl` 和已入库语料。如果完整服务也在运行，给独立副本配置独立 Compose 项目及宿主机端口。

此模式跑 PostgreSQL、pgvector、Elasticsearch、Redis、MySQL 和模拟业务，使用假嵌入及假对话模型。验证顺序为 Docker 健康、迁移、合成语料入库、`/health`、带日期的 `/retrieve`、普通 `/chat`、离线回归。离线回归不访问外部模型。原机从空库迁移到 `0007`，样例为 S 档 3 篇、L 档 12 篇，旧规程和现行规程分别命中 v1、v2；坐席工具将 420 期裁成 5 期，离线回归 14/14。 [空目录复现记录](../../harness/build/phase-38-wrapup.md#记录)

## 恢复 Mac 上的完整链路

1. 安装原生 arm64 的 Docker Desktop、uv 和 Ollama。Docker Desktop 的 Resources 内存上限设约 24 GiB，这是 64 GB M4 Max 原机实测配置，其他设备按物理内存调整并重新核对。Redis、PostgreSQL、ES 和 MySQL 都由 Compose 提供。记录 `uname -m`、`docker info` 和实际镜像架构。 [Mac 环境记录](../../harness/context/phase-30-mac-context.md)
2. 在仓库根目录用 `cp -n .env.example .env` 建立配置，确认 `CHAT_MODEL=gateway`、`EMBEDDING_MODEL=qwen3`、`EMBED_DEVICE=mps`，然后填写本机密钥。保留 `DAILY_BUDGET_CNY=10` 默认值，正常运行时关闭故障注入，按需启用 `PREWARM`。检查 `.env.example` 中注释列出的端口。5432 冲突时同时按同一值调整 `DB_PORT` 和 `DATABASE_URL`，例如 `15432`。 [配置样例](../../.env.example)
3. 在 Ollama 服务进程环境设置 `OLLAMA_CONTEXT_LENGTH=4096`，启动 `ollama serve` 并下载 `qwen3:4b-instruct`。如果系统已经有 Ollama 服务，修改该服务后重启，以 `ollama ps` 核对活动模型和设备。Qwen3 嵌入和精排由 macOS 主机 MPS 提供，小模型由 Ollama Metal 执行，DeepSeek V4 Pro 经 LiteLLM 网关调用。只有复现既有校准需要本机 Qwen2.5 7B Instruct。 [模型与设备](../../harness/context/phase-30-mac-context.md)
4. 在根目录执行 `docker compose up -d --build --wait`。用 `docker compose ps` 验证六服务 healthy，确认当前 Elasticsearch 镜像实际加载 kuromoji，避免把容器健康等同于分词器可用。内部容器走网关 `http://gateway:4000/v1`，Mac 主机端应用默认走 `http://127.0.0.1:4000/v1`。原机 24 GiB 设置下虚拟机报告约 23.43 GiB，可用容器镜像实测为 `linux/arm64`。 [基础设施验收](../../harness/build/phase-30-cleanup-infra.md#记录)
5. 按 [规程语料验收](../../harness/build/phase-31-corpus.md#记录) 恢复原有公开快照，校验清单与原件指纹后再生成、入库。若快照无法恢复，用纯合成模式验证代码；若补采现有清单，须在有界面的 Chrome 逐页保存，每页至少间隔 5 秒，最多 200 页，遇 403、频率提示或验证码立即停。用于历史指标同题复现的评估使用原快照及固定日期 `2026-11-18`。 [公开素材规则](../../PLANS.md#31-知识库语料)

在 `backend/` 从依赖到 HTTP 启动的命令如下。首次同步需要所锁定的包及模型权重，缓存齐全后可以离线校验。`poe serve` 用于开发，固定住被测提交并使用作者手册中的独立端口执行封存评测。

```bash
UV_NO_CONFIG=1 uv lock --check
UV_NO_CONFIG=1 uv sync --locked --extra gpu
UV_NO_CONFIG=1 uv run --locked alembic upgrade head
UV_NO_CONFIG=1 uv run --locked poe build-policies --as-of 2026-11-18
UV_NO_CONFIG=1 uv run --locked poe ingest
UV_NO_CONFIG=1 uv run --locked poe serve
```

另开终端访问 `http://127.0.0.1:8000/health`，应收到 `status=ok` 和 `database=ok`。按语料阶段验收，恢复完整数据后的参考值是 S 档 185 篇、L 档 3,000 篇，pgvector 和 ES 各有 3,213 个规程块。再执行 `UV_NO_CONFIG=1 uv run --locked poe check`，可在模拟业务和数据库 healthy 后执行 `UV_NO_CONFIG=1 uv run --locked poe test-int`。最后复现真实网关链路前先核对日账本。账本按运行进程的本地日期记录，写入为单文件读改写，两侧付费回放宜串行。 [检索验收](../../harness/build/phase-32-retrieval.md#记录) · [作者封存手册](../eval/copilot-author.md)

## 恢复 Dify 工作流

- 按 [Dify 本机手册](../eval/dify-local.md) 固定 1.19.0 和独立的 `grounded_dify` Compose 项目，通过本机 Docker 网络连接同一网关与模拟业务。Mac 的 MPS 嵌入桥先在 18082 启动，Dify 控制台默认端口 18090。用专用测试账号完成安装、插件安装与验收。原机检查包含一次性初始化的 16 个镜像均是 `linux/arm64`，带 healthcheck 的 5 个容器均 healthy。
- 在 Dify 绑定 `small`、`deepseek-v4-pro`、`qwen3-embedding-0.6b` 三个别名，公开的可移植 Chatflow 模板在 `infra/dify/copilot-chatflow.yml`。按原文件名导入 S 档 185 篇，绑定同一知识库到两个检索节点。保留通用分段 1,024 字符、重叠 50 字符、语义／关键词 0.7／0.3、Top 5。核对 37 节点、发布和导出实际画布，再确认本机 Chatflow API Key。 [Dify 节点验收](../../harness/build/phase-37-dify-compare.md#记录)
- 对照测量时，两侧使用当前同一物理机器、同一网关、相同模拟业务和相同用例，分别预热并串行。记录模型、语料指纹和真实画布版本，区分无注入、明确注入和 5% 随机超时。做完故障测试恢复默认开关。报告应明确 Dify S 档及同机配对的实际受测提交。 [同题对照配置](../eval/dify-local.md#回放证据)

## 已踩过的坑和对应改进

| 现象 | 当时查明及处理 | 下一轮可继续改善 |
| --- | --- | --- |
| 新机 `uv --locked` 起不来，或 `--offline` 缺 wheel | 原机全局 `exclude-newer` 干扰已锁依赖，命令加 `UV_NO_CONFIG=1`。干净目录第一次缺 wheel，按锁文件联网补齐后再离线 | 换机先执行锁文件校验，再同步正式依赖，记录 Python、uv 和缓存状态。`uv.lock` 留在 Git，`uv-*` 本地产物在新机按需重建 |
| GitHub Actions 的普通依赖环境缺 NumPy | 本机 `--extra gpu` 已间接安装 NumPy，默认 CI 同步未安装它。`check` 的 mypy 找不到 NumPy，`integration` 在收集测试时报相同依赖错误。CI 单独安装锁文件已有的 `2.5.4`，保留原检查命令及门槛 | 后续单列评测依赖组，让评测用的 NumPy 成为显式依赖，并以干净的无 GPU 环境验证安装 |
| Ollama 首次加载占内存过大，冷态延迟高 | 自动分配 262,144 token 上下文时约 42 GB，设为 4,096 后约 3.2 GB。阶段 35 一条冷态重连首字 5.231 秒，其中意图节点 4.141 秒 | 保留热态与冷态独立监测，记录上下文、进程设备及预热状态。macOS MPS 单次含加载、节点毫秒与全链路秒数分开读 |
| 有精排的档位不一定更好 | 阶段 32 的 30 条冒烟默认混合两档均命中 30/30，带精排两档均 27/30，P95 各约 1.96／1.99 秒，冻结流程默认关闭该请求开关 | 在后续独立评测中分层看短查询、跨规程和版本陷阱的收益，并连同延迟计量 |
| Dify 导入后有知识库引用、变量和剪贴板问题 | 模板改为空知识库占位，用户在界面重新绑定；混合分支改用 `class_label`。Chrome 自动化无法取得黏贴内容，作者在本机手动填密钥 | 把导入、手动凭据、引用绑定、发布后的导出以及五个模型节点别名核对作为重建清单 |
| Dify 指定故障读到旧的成功结果 | 首轮看到 2 条代理缓存响应 `TCP_REFRESH_FAIL_OLD/200`，仅在模拟业务 GET 路径禁缓存。用正常 200、故障 503、恢复 200 验证，POST 保持拒绝；用新目录重跑全部配对，实际缓存响应为 0 | 故障前先验上游状态、代理缓存和恢复，再观察安全降级与最终失败率 |
| Dify 客户端先收到消息结束事件，或误把会话历史当断点续推 | 回放等待工作流终态及实际网关用量，顺序保留在记录中；断线后测试得到新消息，探查 SSE 没有事件 ID。LangGraph Redis 断点续推独立验证过 | 集成回放继续校验终态和 token 关联，以相同断点协议验证不同实现。两侧首字时间按客户端可见输出记录 |
| 重跑整批费钱，深夜断点容易重复观测 | 同日续跑保留 163 条已有记录，续跑前后前缀哈希一致。观测按题和档逐行落盘，续跑用原路径。评测前检查东京时区日期、账本和运行进程 | 同一批评测使用稳定的运行目录、题集和配置，保留同次运行清单。接近当日上限时给下一次请求留余量，记录实际账本增量 |
| 合规场景单次看到通过，重跑仍会缺转介 | 还款困难和个人减税增加固定分流与专业转介；站内知识只提供有证据的渠道。专项观察逐题重复，与投诉、一般还款及一般减税规程做反向对照 | 后续扩大独立口语化和混合问句覆盖，沿用多遍和反向测试；记录每次观察通过的分子及分母 |
| 规程召回与答复质量容易混看 | S/L 回放观察 Top5、过期命中、两类延迟与成本；20 条校准仅一致 16 条，低于 17 条门槛，正式答复质量及离线可采纳率为未测 | 下次由作者另行授权新的独立校准，在看不到机器标签的条件下完成，并在新报告中保留当前校准的来源。真实 AHT、采纳率、办结率需业务试点 |

表中的后续改进留给新分支。冻结结果应保留 Mac 的设备、样本量、版本与计费口径；旧 Windows 18～32 秒和其他设备的后续数字作为各自设备的观测。 [阶段 30 环境](../../harness/context/phase-30-mac-context.md) · [阶段 35 流式](../../harness/build/phase-35-streaming-guard.md#记录) · [阶段 38 收尾](../../harness/build/phase-38-wrapup.md#记录) · [实测报告](../eval/mac-poc-report.md)
