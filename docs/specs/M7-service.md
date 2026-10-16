# M7：服务与可靠性

状态：已批准（长程任务模式，agent 自批）

## 需求

### 目标

1. **`POST /chat`**：JSON 响应；`stream=true` 时返回 SSE。流里发的是**每个环节完成的事件**（`step`），最后一个 `answer` 事件带完整回答。不做逐 token 流式：回答要先过忠实度校验才能给用户看。
2. **MCP 服务**：工具 `search_docs`（只检索）、`ask_docs`（完整问答，带引用），官方 `mcp` SDK，stdio 启动：`poe mcp`。
3. **三级缓存**（内存 LRU + TTL）：查询嵌入、检索结果、完整回答（只缓存无会话、无错误、非降级的回答；键含版本和提示词版本，改提示词自动失效）。
4. **可靠性**：
   - 超时：整次问答 `CHAT_TIMEOUT_SECONDS=90`。
   - 熔断：精排连续失败 3 次后 30 秒内直接跳过精排；半开状态放一次试探。
   - 降级：精排失败 → 不精排；对话模型不可用 / 超时 / 预算用尽 → 返回检索到的片段（`degraded=true`），不报 500。
   - 重试：对话模型的重试已在 M4（429 / 5xx，2 次）。
5. **限流**：令牌桶，按客户端 IP，默认每分钟 30 次（`RATE_LIMIT_PER_MINUTE`，0 = 不限），超了返回统一格式的 429（`RATE_LIMITED`）。
6. **预热**：服务启动时就建检索器、加载模型（`PREWARM=true`，`poe serve` 默认开；测试默认关）。
7. **压测**：`scripts/load_test.py`，对 `/retrieve` 或 `/chat` 并发请求，输出 QPS、P50 / P95 / P99、错误率。

### 非目标

- 反馈接口、trace 持久化、输出后处理（黑名单、重复检测、干预库）：M8。
- 分布式缓存 / 限流（单进程内存就够）。
- 鉴权。

### 接口

```
POST /chat   {"question": "...", "edition": "self_host|cloud|null", "session_id": "...|null", "stream": false}
  → {"trace_id", "answer", "route", "citations": [{"index","document_id","heading_path"}],
     "retrieved_docs": [...], "steps": [{"name","ms","note"}], "cost_cny", "abstained",
     "degraded", "cached", "standalone_question"}
  stream=true → text/event-stream：event: step / event: answer / event: error
```

MCP 工具：`search_docs(query, edition=None, top_k=5)`、`ask_docs(question, edition=None)`。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | 缓存：命中、TTL 过期、LRU 淘汰；三级缓存各一条端到端测试（命中时不再调用下层） | 单元测试 |
| AC2 | 熔断器：连续失败后打开、超时后半开、成功后关闭 | 单元测试 |
| AC3 | 降级：精排挂了仍返回结果；对话模型挂了 / 超时 / 预算用尽仍返回检索片段 | 单元测试 |
| AC4 | 限流：超限 429 统一格式；不同客户端互不影响；令牌随时间恢复 | 单元测试 |
| AC5 | `/chat`：JSON、SSE（事件顺序、最后有 answer）、422、流中出错发 error 事件 | 单元测试 |
| AC6 | MCP：两个工具的输入输出、工具列表；用 MCP 客户端经 stdio 连上真实进程并列出工具 | 单元 + 集成测试 |
| AC7 | 启动预热；预热失败时服务仍启动，第一次请求再试 | 单元测试 |
| AC8 | 压测脚本在假模型下对 `/chat` 跑通并输出 QPS / P95 | 命令输出 |
| AC9 | `poe check`、`poe test-int`、CI 通过 | |

## 任务

- [x] T1 缓存、熔断器、限流器（`app/core/`）
- [x] T2 带缓存和降级的检索器 / 嵌入器；流式管线；`ChatService`
- [x] T3 `/chat` 与限流、预热
- [x] T4 MCP 服务
- [x] T5 压测脚本、收尾

## 阻塞

- 真实压测数字要真实模型（本机 GPU）和 DeepSeek 密钥；没有密钥时只能用假对话模型 + 真检索压测。

## 记录

2026-10-16 完成。
- AC1～AC5、AC7：`tests/unit/core/test_resilience.py`、`tests/unit/retrieval/test_resilient.py`、`tests/unit/orchestration/test_service.py`、`tests/unit/api/test_chat.py`（缓存 / 熔断 / 限流 / 降级 / SSE / 预热）；AC6：`tests/unit/api/test_mcp.py` 11 个 + `tests/integration/test_mcp_stdio.py`（真实子进程经 stdio 列出两个工具）。`poe check` 397 passed，覆盖率 94.8%；`poe test-int` 27 passed。
- AC8（本机 RTX 5070 Ti，真实 Qwen3 嵌入 + 精排，`CHAT_MODEL=fake`，`RATE_LIMIT_PER_MINUTE=0`，并发 4）：
  - `/retrieve` 冷查询（每次问题都不同）：QPS 4.8，P50 833 毫秒，P95 870 毫秒，0 错误；
  - `/retrieve` 28 题循环 56 次：QPS 3.0，P50 769 毫秒，P95 12.2 秒（第一次请求要做 CUDA 预热，之后的请求命中检索缓存或在 0.8 秒内）；
  - `/chat`（假对话模型，只测编排开销，不是真实生成耗时）：QPS 40，P50 6 毫秒。
  - 瓶颈是 GPU 上的精排（线程锁让推理串行），并发再高 QPS 不会涨；真实 `/chat` 的耗时由 DeepSeek 往返决定，要有密钥才能测。
- SSE 手动验证：`curl -N` 看到 step 事件逐个到达，最后是 answer 事件。
- **偏离 / 决定**：① 精排失败的判断是「检索抛 AppError / RuntimeError / OSError」，数据库错误也会让熔断器计一次失败（降级重试仍然失败时原样抛出真正的错误）；② 答案缓存键 = (问题, 版本, 提示词哈希)，**不含**对话模型名（换模型要重启服务）；③ 限流只按 IP，放在路由依赖里（`/health` 不限流）；④ `/feedback` 留给 M8；⑤ MCP 用 `mcp` 2.x 的 `MCPServer`（不是 1.x 的 `FastMCP`）；⑥ 预热失败只记警告，第一次请求再试。
- **未验证**：真实对话模型下的端到端耗时；HTTP 模式的 MCP（只验证了 stdio）；Claude Code 里的实际调用（要作者执行 `claude mcp add`）。

