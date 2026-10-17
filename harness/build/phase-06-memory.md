# M6：记忆

状态：完成（2026-10-16，验收证据见 [build-log](../build-log.md)）

> 这是计划和记录，不是完成证据；进度以 build-log 为准。

## 需求

### 目标

1. **会话**：`ChatRequest.session_id`；同一个会话里的追问能接着上文。
2. **问题独立化**：有历史时，把含指代 / 省略的追问（「那云版本呢」）改写成完整的独立问题，后面的路由和检索都用它。没有历史就不调用模型。
3. **短期记忆与摘要**：只保留最近 `MAX_TURNS=6` 轮原文；超过就把最早的几轮并进一段摘要（模型生成），最近 `KEEP_TURNS=3` 轮保留原文；喂给模型的历史有字数预算 `HISTORY_MAX_CHARS=3000`。
4. **用户版本记忆**：用户在请求里指定、或路由从问题里识别出版本（self_host / cloud），记在会话里，之后的追问自动带上；请求里显式给的版本优先并覆盖记忆。
5. **会话存储**：`SessionStore` 接口；内存实现（测试、命令行）和 PostgreSQL 实现（`sessions` 表，迁移 0004）；`purge_expired(max_age_days)` 清理过期会话。

### 非目标

- 用户长期画像、跨会话记忆。
- 多轮评测集（作者的 Gemini 题目是单轮）；只做单元测试和一个集成测试。
- 会话相关的 HTTP 接口：M7 的 `/chat` 一起做。

### 接口

```python
Turn(question: str, answer: str)
Session(id: str, edition: str | None, summary: str, turns: list[Turn])
SessionStore.load(session_id) -> Session | None
SessionStore.save(session) -> None
SessionStore.purge_expired(max_age_days: int) -> int   # 返回删除的会话数
ChatPipeline(chat, retriever, store: SessionStore | None = None)
ChatRequest(question, edition=None, session_id=None)
ChatResponse 新增 standalone_question: str | None   # 独立化后的问题（没改写就是 None）
```

- 迁移 0004：`sessions(id text pk, edition text null, summary text not null default '', turns jsonb not null default '[]', created_at, updated_at)`，`edition` 有 CHECK 约束。
- 新提示词：`standalone_v1.md`、`summarize_v1.md`。
- 被护栏 / 路由拒绝的回合**不进入历史**（避免污染）；CLARIFY 的回合进入历史（用户的下一句通常就是回答）。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | 追问被独立化，后续检索用独立问题；首轮和没有 session 时不调用独立化模型 | 单元测试 |
| AC2 | 摘要：超过 6 轮时最早的并进摘要、保留最近 3 轮；摘要模型失败时直接截掉最早的轮次，不拖垮请求 | 单元测试 |
| AC3 | 历史字数预算：超出时丢掉最旧的 | 单元测试 |
| AC4 | 版本记忆：识别到的版本进会话；追问自动过滤；显式版本覆盖记忆 | 单元测试 |
| AC5 | 被拒绝的回合不进历史；CLARIFY 的进 | 单元测试 |
| AC6 | 内存存储与数据库存储通过同一组契约测试；过期清理 | 单元测试 + 集成测试 |
| AC7 | 迁移 0004 升降级成功；`poe check`、`poe test-int`、CI 通过 | |

## 任务

- [x] T1 类型、存储接口、内存实现、迁移 0004、数据库实现
- [x] T2 独立化、摘要、版本记忆、接入 `ChatPipeline`
- [x] T3 收尾

## 阻塞

- 真实模型下追问改写的质量要密钥后看；没有多轮评测集。

## 记录

2026-10-16 完成。
- AC1～AC5：`tests/unit/orchestration/test_memory.py` 11 个；AC6：内存存储单元测试 + `tests/integration/test_sessions_database.py` 3 个（往返、upsert、过期清理、版本约束）；AC7：迁移 0004 在测试库和开发库升级成功。`poe check` 344 passed，覆盖率 94.0%；`poe test-int` 26 passed。
- **偏离 / 决定**：① 摘要失败时保留旧摘要并丢掉最早的轮次（不重试）；② 独立化输出不合法时用原问题；③ 路由识别出的版本也写进会话（不只是显式指定的）；显式版本优先；④ 被拒绝（REFUSE）的回合不存，证据不足拒答的回合存；⑤ `ChatPipeline` 的 `store` 可选，不传就是无状态。
- **未验证**：真实模型下追问独立化和摘要的质量；没有多轮评测集。

