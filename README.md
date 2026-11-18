# grounded_rag

正在把现有问答后端改造成索尼银行住宅贷款坐席 Copilot 的概念验证。项目在本机运行，使用合成的客户与业务数据。项目目标、实现顺序和已验证进度分别见 [GOALS.md](GOALS.md)、[PLANS.md](PLANS.md) 和 [开发日志](harness/build-log.md)。

## 阶段 30 基础设施

需要 Python 3.12、uv、Docker Desktop 和 Ollama。首次运行时以 `.env.example` 为模板创建仓库根目录的 `.env`，填入 `DEEPSEEK_API_KEY` 和自行生成的 `GATEWAY_API_KEY`。有现成配置时补齐对应字段即可。Apple Silicon 上用 `EMBED_DEVICE=mps`。

```bash
ollama pull qwen3:4b-instruct
docker compose up -d --build --wait
cd backend
uv sync --locked --extra gpu
uv run poe check
```

执行前在另一个终端用 `OLLAMA_CONTEXT_LENGTH=4096 ollama serve` 启动本机 Ollama，监听 11434 端口。网关启用方式为 `CHAT_MODEL=gateway`，大模型用 DeepSeek，小模型用 Ollama 的本机模型。容器端口、模型别名及覆盖方式见 [.env.example](.env.example)。

在 `backend/` 执行 `uv run python -m scripts.phase_30_models --gateway` 可验证两个档位及 token 用量。这会调用一次 DeepSeek，沿用本地每日预算。

## 阶段 31 语料

公开页面、清单和哈希位于本机 `data/raw/public/`。用已保存的本地资料生成日文合成规程，在 `backend/` 执行以下命令。

```bash
uv run alembic upgrade head
uv run poe build-policies --as-of 2026-11-18
uv run poe ingest
```

入库在 PostgreSQL 写入向量和版本元数据，并同步 kuromoji 索引。出题用语料包写入 `.cache/policy-question-pack.zip`，数据报告写入 `.cache/policy-corpus-report.json`。发布草稿规程时用 `uv run poe ingest --publish <文档ID>`。

## 阶段 32 检索

`POST /retrieve` 用 pgvector 和 Elasticsearch 混合检索。查询日期默认取当天，语料档默认 L，精排默认关闭。请求中可指定 `filter.product_line`、`filter.policy_type`、`filter.as_of`、`filter.corpus_tier` 和 `rerank`。响应返回子块元数据和 `degraded` 标记。

```bash
uv run poe retrieve-demo --corpus-tier S --as-of 2026-11-18 '繰上返済の手続を確認したいです。'
uv run poe compare-retrieval
```

## 阶段 33 模拟业务与只读工具

`mock_core` 启动时会为独立的 MySQL 数据库建表并灌入合成种子。对照测试经 HTTP 复用同一合成业务系统。用下列命令启动联调服务并在 `backend/` 跑集成测试。

```bash
MOCK_ALLOW_FAULT_HEADERS=true docker compose up -d --build --wait db es redis mock_core
docker compose exec -T mock_core python -m mock_core.seed verify
cd backend
uv run poe test-int
```

日常运行时按默认配置启动 Compose，故障注入请求头会关闭。模拟坐席、接口和注入方式见 [模拟业务系统说明](mock_core/README.md)。

## 阶段 34 坐席／客户双泳道

在 `backend/` 执行 `uv run alembic upgrade head` 和 `uv run poe serve`。`POST /chat` 默认为客户泳道。坐席调用传 `channel: "agent"`，通过 `agent_id` 和 `customer_id` 指定本机合成工作台上下文。规程检索支持与 `/retrieve` 相同的 `filter`，连续对话传同一个 `session_id`。

```json
{
  "question": "契約L0001の次回の返済予定額を照会してください。",
  "channel": "agent",
  "agent_id": "A001",
  "customer_id": "C0001",
  "session_id": "synthetic-demo"
}
```

响应包含 `intent`、脱敏 `tool_calls`、`citations`、节点耗时和网关用量。配置 `STRICT_ANSWER_CHECKS=true` 可打开证据评分和忠实度校验。用 `uv run python -m scripts.phase_34_smoke` 跑 20 条合成日文样例，DeepSeek 用量计入原每日预算。

第一版的运行与评测说明见 [归档 README](harness/archive/v1-dify-docs/README.md)。
