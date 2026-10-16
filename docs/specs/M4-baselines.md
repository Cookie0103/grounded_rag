# M4：基线

状态：已批准（长程任务模式，agent 自批）

## 需求

### 目标

1. DeepSeek 客户端（`providers/`）：统一的 `ChatModel` 接口，统计 token 和费用，每天 ¥10 的预算由代码强制。
2. 两个基线被测系统：**无检索**（直接问模型）和**朴素 RAG**（向量检索 top5 → 拼上下文 → 生成），后面的完整系统要和它们比。
3. `poe eval-dev --system no-retrieval|naive-rag` 能跑；评审可以用 DeepSeek（`--judge deepseek`）。
4. 没有密钥时全部用假模型验证流程；真实运行等作者提供密钥和开发集。

### 非目标

- 路由、改写、分解、引用格式、忠实度校验：M5。
- 真实的基线分数：要开发集和密钥，作者回来后跑。

### 接口

**配置**（`Settings`，同步 `.env.example`）：`deepseek_api_key`（可空）、`deepseek_base_url`、`deepseek_model`、`chat_model`（`deepseek` / `fake`，默认 `deepseek`）、`daily_budget_cny`（默认 10）。

**DeepSeekChat**：`complete(messages, json_mode=False) -> Completion`。
- 请求 `POST {base_url}/chat/completions`，`temperature=0`，`json_mode` 时 `response_format={"type": "json_object"}`。
- 超时 60 秒；429 和 5xx 重试 2 次（间隔 1、2 秒），其他 4xx 不重试。
- 连接失败、超时、最终的 5xx → `DependencyUnavailableError`；没有密钥 → `ConfigError`。
- 费用 = 输入 token × 输入单价 + 输出 token × 输出单价（单价是 `config.py` 里的常量，**调用前要对照官方价格页核对**）。

**预算**（`BudgetLedger`）：按日期记在 `.cache/budget/<日期>.json`；每次调用前检查，今天已花费 ≥ 预算就抛 `BudgetExceededError`（`code=BUDGET_EXCEEDED`，429）；每次调用后记账。作者手动测试不受限（`daily_budget_cny=0` 表示不限制）。

**被测系统**
- `NoRetrievalSystem(chat)`：提示词只有问题；`retrieved_docs=()`、`contexts=()`。
- `NaiveRagSystem(retriever, chat)`：`retrieve(top_k=5, rerank=False)` → 把父块文本拼成上下文 → 生成；记录检索到的文档、上下文和成本。
- 两个系统的提示词在 `eval/prompts/baseline_*_v1.md`，**不许要求引用或拒答**（那是 M5 的内容，基线要保持朴素）。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | DeepSeek 客户端：成功、`json_mode`、重试、不重试的 4xx、超时、没有密钥、费用计算 | 单元测试（`httpx.MockTransport`） |
| AC2 | 预算：累计、跨天重置、超限抛错、0 表示不限、文件损坏时从 0 开始并告警 | 单元测试 |
| AC3 | 两个基线系统的回答、上下文、成本、提示词内容 | 单元测试（假模型） |
| AC4 | `poe eval-dev --system naive-rag --chat fake --judge none` 能跑通并出报告 | 命令输出 |
| AC5 | `poe check`、`poe test-int` 通过，CI 全绿 | |

## 任务

- [x] T1 配置、DeepSeek 客户端、预算
- [x] T2 两个基线系统和提示词
- [x] T3 `eval_run.py` 接上系统和评审选项
- [x] T4 收尾（Spec 记录、日志、HANDOFF）

## 阻塞

- 真实运行要 `DEEPSEEK_API_KEY` 和开发集；官方价格要作者或我联网核对后更新常量。

## 记录

2026-10-16 完成（代码和流程；真实基线分数待作者提供密钥和开发集）。
- AC1～AC3：`tests/unit/providers/test_deepseek.py`（13 个）、`tests/unit/eval/test_systems.py`（3 个）；`poe check` 294 passed，覆盖率 92.9%；`poe test-int` 23 passed。
- AC4：`CHAT_MODEL=fake poe eval-dev --system naive-rag --questions eval/smoke_retrieval.jsonl` 跑通；纯向量检索 Recall@5 96.4%，与 M2 对比实验里「只用向量」的 0.964 一致。
- 价格：用 `deepseek-flash` 高峰时段、缓存未命中的美元价（输入 $0.3 / 输出 $1.2 每百万 token）按 7.2 换算成人民币，偏保守；官网价格页是美元，2026-10-16 核对。
- **偏离**：`--judge` 的 `deepseek` 实际是「`CHAT_MODEL` 配的对话模型」，评审调用的费用没有计进评测报告的成本（只有被测系统的）；`httpx` 从开发依赖移到正式依赖。

