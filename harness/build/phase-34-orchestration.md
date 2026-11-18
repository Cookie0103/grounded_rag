# 阶段 34：双泳道编排

状态：已完成（本地分支 `2026-11-18-dual-orchestration`）

> 这是计划和记录，不是完成证据；进度以 [build-log](../build-log.md) 为准。设计依据见 [PLANS.md](../../PLANS.md) §4.1、§4.6、§4.7。

## 需求

### 目标

1. 把现有的单图五路路由改成「意图四分类 + 坐席 / 客户双泳道」，查数走工具、规程走检索。
2. 主链路的模型调用次数压到：意图 1 次（小模型）+ 工具规划 0～2 次（小模型）+ 生成 1 次（大模型）。
3. 对话状态换成 LangGraph Postgres checkpointer。

### 非目标

- 逐 token 流式和断点续推、出口护栏（阶段 35）。本阶段生成仍可整段返回。
- 提示词调优到最佳；本阶段是第一版日文提示词，调优在阶段 36 用开发集做。

### 接口

`POST /chat` 请求体：

```json
{"question": "来月の返済額はいくらですか", "channel": "agent",
 "agent_id": "A0012", "customer_id": "C000123", "session_id": "..."}
```

- `channel`：`agent` 或 `customer`。`customer` 时忽略 `agent_id`、`customer_id`。
- 响应保留 `trace_id`、`answer`、`citations`、`steps`、`cost_cny`、`degraded`，新增 `intent`、`tool_calls`；`route` 字段由 `intent` 取代。
- 两图使用四个意图标识 `smalltalk`、`complaint`、`policy`、`lookup`。次意图唯一支持规程与查数的组合。`tool_calls` 提供脱敏摘要，响应记录网关回传的输入、输出 token。
- API 与 MCP 共用双泳道服务。MCP 的文档问答使用客户泳道。保留旧评测适配器的内部 `route` 字段，旧 REST 输入 `edition` 仍可解析，规程查询条件统一由 `filter` 控制。
- 请求的 `session_id` 按泳道和工作台作用域散列成 `thread_id`。只保存上一轮意图和最近一次规程问题。旧表迁移前先确认本机没有旧会话数据。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | 四类意图各有端到端测试（假模型）；分类器输出不合法时走保守路由 | 单元测试 |
| AC2 | 意图分类的输入只有当前问题和上一轮意图 | 测试断言提示词里不含更早的历史 |
| AC3 | 客户泳道的图里没有工具节点；查数问题得到转人工话术，回答里无任何数字 | 图结构断言 + 测试 |
| AC4 | 坐席查数：工具规划最多两轮，互不依赖的工具并行 | 用假模型和计时桩验证 |
| AC5 | 任一必需工具 `failed` 时回答是降级话术，不含客户数字；`denied` 时说明无权限 | 测试 |
| AC6 | 「查数 + 规程」混合问题两条支路都执行并合并生成 | 测试 |
| AC7 | 会话经 checkpointer 持久化；进程被杀后重启，同一 `session_id` 能接着上一轮意图继续 | 集成测试 |
| AC8 | 证据评分、忠实度校验保留为严格模式开关，默认关 | 配置与测试 |
| AC9 | 真实模型下各节点耗时分解有实测值（意图、规划、工具、检索、生成） | 20 条样例的耗时表 |
| AC10 | `poe check`、`poe test-int` 通过 | 命令输出 |

## 任务

- [x] T1 状态与图：重写 `State`；节点为 `guard`、`intent`、`plan_tools`、`run_tools`、`retrieve`、`generate`、`direct`、`escalate`、`handoff`、`degrade`。坐席和客户分别编译，客户侧不注册工具节点。旧图已归档。
- [x] T2 意图节点：小模型档，JSON 输出主意图与可选次意图；可用时按 logprobs 计算置信度。保留规则问候。
- [x] T3 工具规划与执行：函数调用选择工具和参数；执行经阶段 33 的中间件；结果按三态汇总进状态。
- [x] T4 生成：大模型档；提示词分查数、规程、混合三种；规程回答必须带引用编号（复用 `resolve_citations`）。
- [x] T5 日文提示词：`intent`、`plan_tools`、`generate_*`、`direct`、`escalate`、`handoff`、`degrade`，文件名带版本号；退役第一版专属提示词。
- [x] T6 checkpointer：接入 `langgraph-checkpoint-postgres`；退役 `sessions` 表与自写的会话存储；追问独立化只在有历史且是规程意图时执行。
- [x] T7 `providers/`：网关客户端支持函数调用；假模型能按脚本返回工具调用。
- [x] T8 清理：将原图、专用测试与相关提示词归档，严格模式继续复用评分和忠实度校验。
- [x] T9 评测适配：`eval/systems.py` 能以新接口调用系统，为阶段 36 做准备。

## 需要作者做的

无。

## 记录

实现决策、运行限制与归档范围见[阶段记录](../context/phase-34-orchestration-context.md)。本机 `.env` 的 `CHAT_MODEL` 改为 `gateway`，沿用原密钥与预算。

| 验收 | 本机命令与观察 |
|---|---|
| AC1–AC3 | `uv run --locked pytest -q tests/unit/orchestration/test_copilot.py` 的 19 项包括四类意图、非法输出、低置信度、分类输入边界、客户图结构、含查数的混合问题转人工且无数字。 |
| AC4–AC6 | 同一组测试通过事件同步验证独立工具并发以及真实工具执行与规程检索的重叠；测试断言两轮规划上限、必需工具失败或拒权时不生成客户数字、混合分路后使用两侧证据。 |
| AC7 | `uv run --locked alembic upgrade head` 将开发库从 0006 迁移到 0007。`tests/integration/test_conversation_database.py` 在真实测试库终止写入进程并启动新进程，读回同会话最新状态；服务层单测断言上一轮意图和规程问句传到图，以及坐席、客户和跨泳道会话隔离。 |
| AC8 | 专项测试断言默认图没有严格节点，开启 `STRICT_ANSWER_CHECKS` 可执行证据评分和忠实度校验。两个原提示词内容未改动。 |
| AC9 | `uv run --locked python -m scripts.phase_34_smoke` 真实请求 `/chat` 20 次均为 200，主意图 20/20，两条混合均执行工具与检索。全部样例分解见下表。 |
| AC10 | `uv run --locked poe check` 为 450 项通过，覆盖率 91.36%；`uv run --locked poe test-int` 为 39 项通过；`uv --no-config lock --check --offline` 解析 177 个包。 |

Mac M4 Max、64 GB，语料 S，MPS 嵌入，预热检索后串行发起。Ollama Qwen3 4B Instruct 做分类和规划，DeepSeek V4 Pro 做生成。端到端包含完整响应，无首字测量。第一次冒烟 P95 为 4,667.62 毫秒、费用 ¥0.26458186；在修正运行脚本和日文上下文标签后重跑，以下为最终实测，网关账本增量 ¥0.26423971。样本为合成冒烟，正式报告另用阶段 36 和阶段 37 的样本。

| 环节 | 次数 | 中位数（毫秒） | P95（毫秒） |
|---|---:|---:|---:|
| 端到端 | 20 | 2,656.15 | 3,875.82 |
| 意图 | 20 | 170.73 | 203.75 |
| 工具规划 | 8 | 295.01 | 656.97 |
| 单个工具 | 7 | 6.73 | 10.63 |
| 检索 | 8 | 53.76 | 85.22 |
| 生成 | 11 | 2,961.10 | 3,625.99 |

## 阻塞

（无）
