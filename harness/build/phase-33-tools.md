# 阶段 33：模拟业务系统与工具层

状态：已完成（本地分支 `2026-11-18-mock-tools`）

> 这是计划和记录，不是完成证据；进度以 [build-log](../build-log.md) 为准。设计依据见 [PLANS.md](../../PLANS.md) §3.3、§4.2。

## 需求

### 目标

1. 一个独立的模拟业务系统 `mock_core/`（FastAPI + MySQL），带可复现的合成数据和故障注入。
2. 问答服务侧的 5 个只读工具，全部经过统一中间件：鉴权 → 缓存 → 调用 → 字段白名单 → 截断 → 记录。

### 非目标

- 让模型决定调哪个工具（阶段 34）。
- 任何写接口。

### 本机 HTTP 契约

- 所有业务查询使用 GET，工作台坐席通过 `X-Agent-Id` 传递。每个请求都需带当前 `customer_id`，合同查询再传 `contract_id`，业务服务独立复核归属。缺坐席头为 401，非归属查数为 403。
- 中间件先请求 `GET /authorization?customer_id=...&contract_id=...`，合同 ID 可省略。正常返回 `{"authorized":true}` 或 `{"authorized":false}`。超时或服务故障进入失败分支。
- 工具接口成功返回 `{"synthetic":true,"data":{...},"total":数字或 null}`。所有金额字段以日元表示。

| 工具 | 路径 | `data` 字段 |
|---|---|---|
| `query_loan_contracts` | `/loan-contracts` | `contracts[]` 含 `contract_id, product, principal_yen, disbursed_on, status` |
| `query_repayment_schedule` | `/repayment-schedule` | `next_payment_date, next_payment_yen, outstanding_principal_yen, remaining_installments, schedule[]`，计划行含 `period, due_date, amount_yen, principal_yen, interest_yen`，可用 `start_period, end_period` 选区间 |
| `query_delinquency` | `/delinquency` | `days_overdue, amount_yen, late_fee_yen` |
| `query_rate_terms` | `/rate-terms` | `annual_rate_percent, rate_type, fixed_until, insurance_type, insurance_increment_percent` |
| `query_benefits` | `/benefits` | `benefits[]` 含 `name, status` |

- 本机关联 PG、Redis 和 MySQL 均只作用于合成测试。故障注入从环境变量读取，并只在明确启用测试开关时读取 `X-Mock-Fault`。鉴权在故障注入之前，先拦截越权调用。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | `mock_core` 一条命令建表并灌入种子数据；同一种子两次生成的数据逐行相同 | 两次导出的哈希 |
| AC2 | 种子数据覆盖：420 行还款计划、ペアローン、延滞中、已完济、固定期间一年内到期、部分固定金利特约 | 统计脚本输出 |
| AC3 | 5 个接口都是 GET，缺坐席 ID 头返回 401 | API 测试 |
| AC4 | 中间件每一环有独立的单元测试 | 测试清单 |
| AC5 | 非归属坐席查客户：工具返回「拦截」，下游接口没有被调用 | 测试里断言调用次数为 0 |
| AC6 | 同一坐席 5 秒内重复查询命中 Redis；换一个坐席不命中 | 集成测试 |
| AC7 | 口座番号、住所、電話番号等敏感字段在工具输出里不存在 | 对每个工具的输出做字段断言 |
| AC8 | 420 行的还款计划经工具返回后不超过约定上限，并带 `total` | 测试；记录裁剪前后的 token 数 |
| AC9 | 注入超时或 5xx 时，工具在超时预算内返回「失败」，带原因，不抛未处理异常 | 集成测试 |
| AC10 | `poe check`、`poe test-int` 通过 | 命令输出 |

## 任务

- [x] T1 `mock_core/`：独立的包和启动命令（compose 里加服务）；MySQL 表结构用迁移或建表脚本管理；和问答服务不共享代码，只通过 HTTP 交互。
- [x] T2 种子生成器：固定随机种子，约 300 个客户、20 个坐席；还款计划按等额本息算出，利率条件和优惠与公开层里的商品结构对得上（商品名、金利类型、団信种类取自作者保存的页面）。
- [x] T3 故障注入：按接口配置额外延迟、超时比例、5xx 比例，支持固定种子；提供管理接口或环境变量切换，评测时可按用例开关。
- [x] T4 `app/tools/`：工具定义（名称、日文描述、参数 schema、字段白名单、列表上限）与中间件链；复用 `core/resilience.py` 的超时、重试、熔断；缓存后端用 Redis。
- [x] T5 工具结果的数据结构：`ok` / `denied` / `failed` 三态，带 `data`、`total`、`reason`、`cached`、`elapsed_ms`，供后面的降级判断和数字溯源使用。
- [x] T6 trace：每次工具调用记一条步骤详情（复用现有 `Step` / `StepDetails`，按需扩字段）。
- [x] T7 import-linter 的分层约束里加入 `tools` 层。

## 需要作者做的

无。

## 记录

驱动、合成字段、还款裁剪和故障开关见[决策记录](../context/phase-33-mock-tools-context.md)。

| 验收 | 本机命令与观察 |
|---|---|
| AC1 | `MOCK_ALLOW_FAULT_HEADERS=true docker compose up -d --build --wait db es redis mock_core` 成功，镜像检查为 `linux/arm64`。两个独立命令 `docker compose exec -T mock_core python -m mock_core.seed init` 和 `docker compose exec -T mock_core python -m mock_core.seed verify` 分别重新生成数据、导出 MySQL 各表并得到相同 SHA-256 `b31ff85dbb2c0c5c81f8946107e5b8fbc852eabca33e0b0d925be11c568c1243`。重复 `init` 输出 `inserted: false`。 |
| AC2 | `python -m mock_core.seed verify` 统计为 300 个客户、20 个坐席、最长 420 期、ペアローン客户 1 个、延滞合同 1 笔、完済 1 笔、一年内固定期到期 1 笔、部分固定合同 1 笔。 |
| AC3 | `tests/integration/test_mock_core_tools.py` 验证五个 GET 缺坐席头均 401，POST 均 405。 |
| AC4–AC5 | `tests/unit/tools/test_middleware.py` 分别验证鉴权、缓存范围和失效、超时、一次重试、熔断、白名单、裁剪及脱敏 trace。越权时 HTTP 记录仅有鉴权请求，业务接口请求计数为 0。 |
| AC6–AC7 | 集成测试用真实 Redis 验证同坐席的首次、重复和另一坐席分别为未命中、命中、未命中；五种成功结果均带 `synthetic` 标记，并检查输出及 trace 的脱敏。 |
| AC8 | 集成测试验证 `L0001` 明细从 420 行压到 5 行，`total=420`。在 `backend/` 用 `HF_HUB_OFFLINE=1 uv run python` 从模拟服务和 `ToolRunner.call` 分别读取两份载荷，用 Qwen3 tokenizer 编码，测得 21,626 → 318 token。 |
| AC9 | 集成测试注入超时和 5xx 均得到 `failed` 且无结果数据。同一环境独立实测 `timeout` 2,002.32 毫秒，`upstream_error` 11.96 毫秒。 |
| AC10 | `backend/` 下 `uv run --locked poe check` 为 471 项通过，覆盖率 92.29%；`uv run --locked poe test-int` 为 40 项通过。`mock_core/` 下 `uv run --locked python -m pytest -q` 为 10 项通过，独立 Ruff 及两个 `uv lock --check --offline` 均通过。 |

## 阻塞

（无）
