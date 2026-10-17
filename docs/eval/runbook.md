# 评测运行手册（给作者）

> 代码都已经写完并测过（假模型 + 真实检索）。下面是**你**要做的事：出题、给密钥、校准评审、跑测试集。每一步都有命令和「做完应该看到什么」。所有命令在 `backend/` 下执行。

## 0. 准备（一次）

1. 在 `.env` 里写 `DEEPSEEK_API_KEY=...`（不要提交）。`DAILY_BUDGET_CNY=0` 表示你手动测试不限额；agent 自己跑时保持 `10`。
2. `docker compose up -d db` → `uv run alembic upgrade head` → `uv run poe fetch-docs` → `uv run poe ingest`（已做过的会跳过）。
3. 确认检索正常：`uv run poe eval-dev --questions eval/smoke_retrieval.jsonl`，应看到 Recall@5 约 92.9%。

## 1. 出题（Gemini 网页端）

1. `uv run poe export-for-gemini` → `.cache/gemini-pack/part-01.md …`。
2. 按 [PROMPTS.md §6](../../PROMPTS.md) 开一个新对话：先粘贴提示词，再上传所有 `part-*.md`，说「开始出题」。
3. 把输出的 JSON Lines 存成 `backend/eval/data/dev.jsonl`（`split` 为 `dev` 的约 70 题）；`split` 为 `test` 的约 30 题存到**仓库外**（例如 `D:\eval-private\test.jsonl`），不要让 agent 看到。
4. `uv run poe eval-validate`：应为 0 个错误；有错误就把提示贴回 Gemini 让它改。提醒（题干里有「根据文档」之类）建议改掉。
5. 人工过一遍 70 道开发题：问题是否独立成立、金标文档是否真的有答案、关键点是否原子。

## 2. 开发集上跑各系统

```bash
uv run poe eval-dev --system retrieval                           # 只看检索：Recall@5、按题型 / 用词分组
uv run poe eval-dev --system no-retrieval --judge deepseek       # 基线一
uv run poe eval-dev --system naive-rag    --judge deepseek       # 基线二
uv run poe eval-dev --system full         --judge deepseek       # 完整系统
```

- 报告在 `.cache/eval/<系统>/report.md`；回答和评审标签都缓存在同目录，中断后重跑会接着做。
- 评审默认用 `CHAT_MODEL` 配置的 DeepSeek。设计里的「Gemini 主评、Claude 复评」需要命令行后端：`--judge claude` 会调 `claude -p`（消耗你的 Claude 用量，先在 5 题上试）。
- 100 题的大致花费：被测系统 + 评审，`deepseek-flash` 每题几分钱，总共应在 ¥10 以内；超了会抛 `BUDGET_EXCEEDED` 而不是继续花。

## 3. 校准评审（必须做）

1. 从 `.cache/eval/full/answers.jsonl` 随机挑 20 条（含可回答和不可回答）。
2. 对每条，自己按 [notes-evaluation §7.3](../../harness/archive/2026-10-16/notes-evaluation.md) 的规则判：每个关键点 support / partial_support / not_support、有没有矛盾、行为（回答 / 反问 / 拒答）。
3. 与 `verdicts.jsonl` 里的标签对比。**一致率 ≥ 85% 才采信自动评审**；不到就改 `eval/prompts/judge_v1.md`（新增 `judge_v2.md`，不要覆盖）并重跑。

## 4. 完整消融与模型对比

| 行 | 命令 / 配置 | 说明 |
|---|---|---|
| 无检索 | `--system no-retrieval` | |
| naive RAG | `--system naive-rag` | 向量 top5，不精排 |
| + 混合检索与精排 | `--system hybrid-rag` | 混合检索 + 精排，直接生成 |
| + 改写与自适应路由 | `--system routed` | 护栏、路由、改写 / 分解、带引用生成；关掉证据评分和校验 |
| + 校验与拒答 | `--system full` | 再加证据评分（重检索 / 拒答）和忠实度校验 |
| 嵌入模型对比（只看 Recall@5） | `poe compare-retrieval`（已有 9 种方案，换成开发集：`--questions eval/data/dev.jsonl`） | |

> 每行报 4 个核心指标：可信得分（带 95% 区间）、Nugget 召回（V_strict）、Recall@5、P95 与单题成本。题量只有 100，差距小于置信区间时不宣称提升，如实写「没用」。

## 5. 测试集（只跑一次）

1. 确认开发集上的所有改动都已提交、不再改提示词和规则。
2. `uv run poe eval-dev --system full --judge deepseek --questions D:\eval-private\test.jsonl`（输出目录在 `.cache/eval/full`，**先把开发集的缓存移走**，否则会续用开发集的回答缓存）。
3. 把数字填进 [final-report-template.md](../final-report-template.md)。测试集结果不能用来再调参。

## 6. 服务与 MCP 的人工验证

- `uv run poe serve` → 打开 `http://127.0.0.1:8000/docs`，用 `POST /chat` 试几个问题；`"stream": true` 看 SSE。
- `claude mcp add grounded-rag -- uv run --directory <仓库>/backend poe mcp`，在 Claude Code 里让它「用 grounded-rag 查一下知识库最多上传几个文件」。
- `uv run poe load-test --endpoint chat --unique --requests 50 --concurrency 4`（服务端设 `RATE_LIMIT_PER_MINUTE=0`）：记下 QPS 和 P95。
