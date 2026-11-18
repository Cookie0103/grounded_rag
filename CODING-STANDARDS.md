# 代码规范

适用于 `backend/` 下全部代码：`app/`、`tests/`、`eval/`、`scripts/`、`migrations/`。命令都在 `backend/` 目录下执行；文中路径除 `harness/`、`docs/`、`data/`、`.cache/` 外都相对于 `backend/`。
标 **[自动]** 的条目由 `uv run poe check` 或 CI 检查，违反直接失败；其余靠自查和评审。

## 1. 原则

- **KISS**：选最直白的写法，能一行说清就不写三行。
- **YAGNI**：不写当前 Spec 用不到的参数、分支、抽象、配置项和目录。
- **DRY**：写之前先搜仓库；同样的逻辑出现第二次就抽公共函数。只是长得像、变化原因不同的代码不强行合并。
- 每次变更都要让代码库更健康，不能更差。

## 2. 风格

- Python 3.12（`requires-python = ">=3.12,<3.13"`），所有函数写类型标注。[自动 mypy --strict]
- `ruff format`，行宽 100。[自动]
- 命名直白：函数用动词（`split_chunks`），布尔用 `is_` / `has_`，不用缩写（`id`、`url`、`llm` 这类通用词除外）。
- 函数只做一件事：圈复杂度 ≤ 10，语句数 ≤ 40。[自动 C901 / PLR0915]
- 注释只写“为什么”；公共函数写一行 docstring，内部函数不写。
- 不留 `print`、死代码、注释掉的代码。[自动 T20 / ERA]；日志用 `logging`，带 `trace_id`。
- 阈值和参数放 `core/config.py`，不写魔法数字。[自动 PLR2004]
- 自定义异常放 `core/errors.py`；不吞异常，不写宽泛的 `except`。[自动 BLE001 / S110]

## 3. 架构与分层

依赖方向只能向下 [自动 import-linter]：

```text
api → orchestration → retrieval / ingest / tools → providers / db → core
scripts 可调用各层，提供 MCP 和评测等命令入口。应用模块不得 import scripts。
```

- 调用大模型、嵌入、精排只能经过 `providers/`。`openai`、`httpx`、`torch`、`transformers`、`sentence_transformers` 只允许在 `providers/` 中 import。[自动 TID251]
- 环境变量只在 `core/config.py`（pydantic-settings）读取。[自动 TID251 禁用 `os.environ` / `os.getenv`]
- 模块之间传 pydantic 模型，不传裸 dict。
- 所有外部调用必须设超时。工具调用的重试和熔断集中在 `tools/middleware.py`，检索降级集中在 `retrieval/resilient.py`。
- I/O 一律 `async`；GPU 推理等阻塞操作用 `asyncio.to_thread`，不堵事件循环。
- 运行时 Prompt 放 `app/prompts/`，文件名带版本（如 `intent_v1.md`）。修改 Prompt 时新建版本并保留旧版。
- 目录按需创建：到用它的里程碑再建，不提前建空模块。

## 4. API

- 契约以 pydantic 模型为准，由 FastAPI 生成 OpenAPI（`/docs`），不另写接口文档。
- 路径用小写短横线，JSON 字段用 snake_case。只有一个版本，不加 `/v1` 前缀。
- 响应头用 `X-Trace-Id` 关联请求。问答终态、检索和错误等 JSON 响应中使用 `trace_id`。
- 错误格式统一（包括 FastAPI 的参数校验错误）：

  ```json
  {"error": {"code": "DEPENDENCY_UNAVAILABLE", "message": "依赖不可用"}, "trace_id": "..."}
  ```

  `code` 用大写下划线，应用异常定义在 `core/errors.py`。常见状态包括 404 未找到、410 SSE 缓冲过期、422 校验失败、429 限流或预算用尽、500 内部错误和 503 依赖不可用。
- SSE 事件为 `step`、`delta`、`retract`、`answer`、`error`，`data` 一律为 JSON。数据事件用 `id` 和 `response_id` 续推，由 `answer` 或 `error` 结束。
- MCP 工具和 REST 接口调用同一个服务函数，不重复实现。
- 列表接口暂不做分页，真需要时再定。

## 5. 数据库

- PostgreSQL 16 + pgvector；SQLAlchemy 2.0（async，Core 风格表定义）+ asyncpg；迁移用 Alembic。
- 表结构只能通过 Alembic 迁移修改；自动生成的迁移要人工检查；已合并的迁移不再改，有问题就新建迁移修正。
- 迁移必须能在空库上从头跑通。[自动 CI 集成测试]
- 表名用复数 snake_case；每张表有 `id` 和 `created_at timestamptz`；外键列命名为 `<单数表名>_id`。
- 表在用到它的里程碑才建，列和索引写进该里程碑的 Spec。
- 稳定 ID：文档和块的 ID 由“相对路径 + 内容哈希”生成，不用绝对路径，也不用随机数。
- 向量维度写在配置里，与嵌入模型绑定；换模型要走迁移并重建索引。
- SQL 只写在 `db/`，业务代码通过仓储函数访问；只用参数化查询。[自动 S608]

## 6. 测试

- `tests/unit/`：不联网、不用 GPU、不调 DeepSeek、不连数据库，外部依赖用 `providers/` 里的假实现。
- `tests/integration/` 标记 `@pytest.mark.integration`。PostgreSQL 使用夹具自动创建并迁移的**测试库** `grounded_rag_test`。按用例接入 Elasticsearch、Redis 和模拟业务服务。
- `tests/gpu/`：标记 `@pytest.mark.gpu`，需要本机 GPU 和模型权重，只在本机用 `poe test-gpu` 跑，不进 CI。
- 测试文件与源文件一一对应：`app/retrieval/fusion.py` → `tests/unit/retrieval/test_fusion.py`。
- 测行为，不测实现细节；每个测试只验证一件事，名字写清预期（`test_rrf_merges_duplicate_chunks`）。
- 测试量跟风险走：检索、融合、评分、ID 生成这类核心纯函数要测细；薄的接线代码有一个冒烟测试就够；不为不可能发生的情况写测试。
- 修 bug 先写能复现它的失败测试，再修。
- 测试必须可重复：固定随机种子；不依赖执行顺序和当前时间（时间通过参数注入）。
- `app/` 与 `eval/` 的覆盖率 ≥ 80%。[自动 --cov-fail-under]
- `.env.example` 的字段与 `Settings` 一致，由一个单元测试保证。[自动]
- 评测不是测试：不进 CI，也不算 `poe check` 的通过条件。

## 7. 依赖

- 用 `uv add` 管理，`uv.lock` 必须提交；CI 用 `uv sync --locked`，锁文件不同步就失败。[自动]
- 标准库能做的不加依赖；新增依赖要先问，并在 PR 里写一句理由。

## 8. 配置、密钥与预算

- 配置统一由 `core/config.py` 读取；`.env` 不提交，`.env.example` 列出全部字段并加注释。
- 提交前检查私钥和大文件。[自动 pre-commit]
- DeepSeek 用量由 `providers/` 根据返回的 token 数计算。每日预算在 `.cache/budget/<日期>.json` 累计，达到 `DAILY_BUDGET_CNY`（默认 10）后拒绝后续调用。作者手动测试时可设为 `0`，表示不限。

## 9. 可复现性

- 文档里不手写实测数字（测试数、指标、覆盖率）。数字只出现在评测报告里，其他文档链接报告。
- 每份评测报告都记录 commit、配置、模型名与版本、语料版本或清单指纹、题集版本和日期。可公开的汇总进报告，开发评测原始输出放 `.cache/`，封存运行目录由作者放在仓库之外。
- 遍历文件要先排序。用随机数时固定种子。记录合成语料生成日期和参数，公开来源只使用本地快照和清单复现。

## 10. 文件与目录

- **`.cache/`**：AI 生成的临时内容、中间结果、LLM 响应缓存、评审输出、模型缓存、用量记录。已 gitignore，可随时删除。
- **`data/`**：下载的原始文档，已 gitignore。
- 不在仓库根目录或源码目录放临时文件。
- 文档的位置和写法见 `WORKFLOW.md` §6。

## 11. 评测纪律

- `backend/eval/data/` 只读，不许修改评测题和金标。
- 测试集不在仓库里，开发时不得读取或推测测试集内容。
- 不许为了提高指标修改评测代码、评分规则或评审 Prompt；确需修改，须由项目作者批准。
