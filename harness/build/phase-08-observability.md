# M8：观测与坏例

状态：完成（2026-10-16，验收证据见 [build-log](../build-log.md)）

> 这是计划和记录，不是完成证据；进度以 build-log 为准。

## 需求

### 目标

1. **trace 持久化**：每次 `/chat`（含 SSE、MCP 的 `ask_docs`）把问题、路由、各环节耗时与说明、检索到的文档、引用、成本、是否缓存 / 降级 / 拒答、回答，按 `trace_id` 存进 `traces` 表；`GET /traces/{trace_id}` 复盘。记录失败不影响问答。
2. **输出后处理**（`ChatService` 里，对生成的回答）：
   - 敏感信息遮蔽：形如 API 密钥的串（`sk-…`、`Bearer …`）替换成 `[已隐藏]`；
   - 黑名单：命中 `BLOCKED_TERMS` 的回答换成拒答文案（默认空表，作者按需填）；
   - 重复检测：同一句话重复出现 ≥3 次，只留一次。
   每一项触发都记进 steps（`postprocess`）。
3. **干预库**：人工指定「问题 → 标准答案」，优先于生成（在缓存和编排之前）；问题按归一化键（小写、去空白和标点）匹配；表 `interventions`；命令行 `poe interventions add|list|remove`。命中的回答 `route=INTERVENED`，不计成本。
4. **反馈**：`POST /feedback {trace_id, rating: good|bad, comment}`，trace 不存在返回统一格式的 404；表 `feedback`。
5. **坏例导出**：`poe export-bad-cases`：把「差评、拒答、降级」的 trace 导出为 `.cache/bad_cases.jsonl`（只有问题、原因、trace_id，**没有金标**，金标要作者标注后才能进回归集）。

### 非目标

- 外部观测平台（LangSmith、OpenTelemetry）；用结构化日志（已带 trace_id）加数据库就够。
- 坏例自动进回归集（金标必须人工写）。
- 管理界面。

### 接口

```
GET  /traces/{trace_id} → {"trace_id","created_at","question","route","edition","session_id","answer",
                           "abstained","degraded","cached","cost_cny","steps":[...],
                           "retrieved_docs":[...],"citations":[...]}   404：TRACE_NOT_FOUND
POST /feedback {"trace_id": "...", "rating": "good|bad", "comment": "..."} → {"status": "ok"}
```

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | 问答后 trace 被保存、`GET /traces/{id}` 取回内容一致；保存失败不影响回答 | 单元测试 + 集成测试 |
| AC2 | 后处理：密钥遮蔽、黑名单、重复折叠；正常回答不变；steps 里有记录 | 单元测试 |
| AC3 | 干预库：归一化匹配、命中优先于缓存和编排、增删查；数据库实现 | 单元 + 集成测试 |
| AC4 | 反馈：写入、未知 trace 404、非法 rating 422 | 单元 + 集成测试 |
| AC5 | 坏例导出：差评 / 拒答 / 降级被选中，正常回答不被选中；输出没有金标字段 | 单元 + 集成测试 |
| AC6 | 迁移 0005 升降级；`poe check`、`poe test-int`、CI 通过 | |

## 任务

- [x] T1 记录类型、表与迁移 0005、数据库实现
- [x] T2 后处理、干预库、trace 记录接入 `ChatService`
- [x] T3 `/traces`、`/feedback`、命令行（干预、坏例导出）
- [x] T4 收尾

## 阻塞

- 无（全部不需要外部输入）。

## 记录

2026-10-16 完成。
- AC1～AC5：`tests/unit/orchestration/test_observability.py`（后处理、trace、干预库、坏例）、`tests/unit/api/test_observability.py`（`/traces`、`/feedback`）、`tests/integration/test_observability_database.py`（数据库往返、坏例选择、干预库归一化、约束）。AC6：迁移 0005 在测试库和开发库升级成功；`poe check` 419 passed，覆盖率 95.0%；`poe test-int` 32 passed。
- **测试发现的真实问题**：`/feedback` 的 `rating` 最初用 `str` 声明，非法值在接口里被模型层才拒绝，结果是 500；改成 `Literal` 后返回统一格式的 422。
- **偏离 / 决定**：① `ChatService` 记录 trace；MCP 的 `ask_docs`（没有请求级 trace_id）每次生成新的；② 黑名单默认空表（`BLOCKED_TERMS`），作者按需填；③ 缓存命中的回答也各存一条 trace（`cached=true`），方便统计命中率；④ 坏例导出原因优先级：差评 > 拒答 > 降级；⑤ 没有给 `traces` 加保留期清理，后续可仿照 `purge_expired`。
- **未验证**：真实流量下 trace 表的增长和查询耗时。

