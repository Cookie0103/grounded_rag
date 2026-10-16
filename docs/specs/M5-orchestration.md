# M5：编排

状态：已批准（长程任务模式，agent 自批）

## 需求

### 目标

把 M2 的检索和 M4 的对话模型编排成完整的问答流程（`proposal` §4.2、§4.3）：

1. **护栏**：规则拦截明显的注入 / 套提示词 / 过长输入 → REFUSE。
2. **路由**：DIRECT（闲聊、问候）/ SINGLE / MULTI / CLARIFY / REFUSE；规则先判问候，其余交给对话模型（JSON），输出不合法就退回 SINGLE。
3. **改写与分解**：SINGLE 改写成适合检索的问题；MULTI 拆成 ≤3 个子问题，逐个检索再合并。
4. **证据评分与重检索**：判断检索到的上下文够不够回答；不够就按「缺什么」改写再检索，最多 2 次；仍不够就诚实说文档里没有，不硬答。
5. **上下文组装**：父块去重、保持排名顺序、按字数预算截断；每块编号，带文档 ID 和标题路径。
6. **带引用生成**：回答里用 `[1]` `[2]` 标注来源；解析出引用，丢掉编号不存在的引用。
7. **忠实度校验**：回答里有上下文不支持的说法就重生成 1 次，仍不过则拒答。
8. **提示词版本化**：`backend/app/prompts/<名字>_v<版本>.md`，改提示词就加新版本文件。
9. 评测里加 `--system full`，开发集上能和朴素 RAG 对照。

### 非目标

- 多轮记忆、指代消解：M6（`ChatRequest.history` 先留空）。
- HTTP 接口 `/chat`、SSE、MCP、缓存、降级：M7。
- 真实模型下的路由准确率、各路径得分：要开发集和密钥，作者回来后跑。

### 接口

```python
ChatRequest(question: str, edition: str | None = None)
ChatResponse(answer: str, route: str, citations: list[Citation], steps: list[Step],
             retrieved_docs: list[str], contexts: list[str], cost_cny: float, abstained: bool)
Citation(index: int, document_id: str, heading_path: str)
ChatPipeline(chat: ChatModel, retriever: Retriever).answer(request) -> ChatResponse
```

- `steps`：每个环节的名字、耗时、简短说明（给 trace 和调试用）。
- `abstained`：因为证据不足或校验不过而拒答。
- 编排用 LangGraph 的 `StateGraph`；每个节点是一个普通的异步函数，可以单独测试。

### 层次

`app.api` → `app.orchestration` → `app.retrieval | app.ingest` → `app.providers | app.db` → `app.core`（加进 import-linter）。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | 五条路由路径各一条端到端测试（假模型 + 假检索器），断言路径上调用了哪些环节、没调用哪些 | 单元测试 |
| AC2 | 护栏：每类注入模式、过长输入、正常问题不误拦 | 单元测试 |
| AC3 | 路由输出不合法 → SINGLE；问候走规则不调用模型 | 单元测试 |
| AC4 | 证据不足 → 重检索最多 2 次 → 仍不足则拒答；够则不重检索 | 单元测试 |
| AC5 | 上下文组装：去重、顺序、预算截断；引用解析丢掉不存在的编号 | 单元测试 |
| AC6 | 忠实度：不过 → 重生成 1 次 → 仍不过则拒答；通过则不重生成 | 单元测试 |
| AC7 | 所有提示词文件的占位符都能被填满、没有遗留 `{{` | 单元测试 |
| AC8 | 成本累计、每步耗时记录 | 单元测试 |
| AC9 | `poe check`、`poe test-int`、CI 通过；`CHAT_MODEL=fake` 下 `eval-dev --system full` 跑通 | |

## 任务

- [x] T1 提示词、护栏、路由
- [x] T2 改写、分解、检索合并、证据评分、上下文组装
- [x] T3 生成、引用、忠实度、图的组装
- [x] T4 评测接入（`--system full`）
- [x] T5 收尾

## 阻塞

- 真实路由准确率、各路径得分要开发集和 DeepSeek 密钥。

## 记录

2026-10-16 完成（假模型下的流程和测试；真实模型的路由准确率、各路径得分待作者提供密钥和开发集）。
- AC1～AC8：`tests/unit/orchestration/` 38 个测试（五条路由各一条端到端、护栏、重检索上限、忠实度重生成、引用清理、提示词占位符）；`poe check` 333 passed，覆盖率 93.7%；`poe test-int` 23 passed。
- AC9：`CHAT_MODEL=fake poe eval-dev --system full` 跑通（假模型只回显提示词，指标没有意义）。
- 提示词 9 个，在 `backend/app/prompts/`，文件名带 `_v1`；`render` 要求占位符一个不多一个不少。
- **偏离 / 决定**：① 版本未知时**不过滤**（proposal 写「默认自部署版并注明」，等作者决定是否改）；② 证据评分、忠实度校验的输出不合法时按「通过」处理，避免一次格式错误拒掉本来能答的问题；路由输出不合法退回 SINGLE；③ 护栏只用规则，没有模型分类；④ 编排依赖 LangGraph（`uv add langgraph`）；⑤ 后处理（黑名单、重复检测、干预库）留给 M7/M8，没做；⑥ 引用只保留回答里实际出现且编号有效的。
- **未验证**：真实模型下路由 / 评分 / 校验的提示词效果（要开发集后调提示词，每次改动都新增版本文件并在评测里对比）。

