# 提示词模板

> 给 Claude / Codex / Cursor 复用的任务指令，开新会话时整段粘贴即可。每条只写「怎么做」，目标和计划不在这里重复，只引用 [GOALS.md](GOALS.md)、[PLANS.md](PLANS.md)、[harness/build/](harness/build/)。
> 运行时代码用的提示词在 `backend/app/prompts/` 和 `backend/eval/prompts/`，与本文件无关。

## 1. 开始一个阶段

```text
先读 AGENTS.md、harness/build-log.md 的「当前状态」，再读 harness/build/phase-NN-*.md 和对应的 harness/context/phase-NN-*-context.md。
只读不写：先告诉我这个阶段的范围、依赖、你的假设；有歧义就列出来，等我回复再动手。
确认后只做这一个阶段，做完就停，不要开始下一个。
开始时在 harness/context/ 建（或续写）本阶段的 context 文件，只记会改变后续范围、决策或验证方式的东西，不记过程。
```

## 2. 执行并验收一个阶段

```text
按 harness/build/phase-NN-*.md 的任务顺序做：先写失败的测试，再写实现，最后只在任务范围内整理。
每个任务做完：在 backend/ 下跑 uv run poe check，把命令和输出摘要追加到 harness/build-log.md 的「活动记录」（只追加，不改旧条目）。
阶段验收：对照该文件的验收标准逐条给出证据（命令 + 输出）；没有运行过的命令不算通过。全部满足才把 build-log 的阶段状态改为「完成」。
遇到阻塞（见 AGENTS.md「什么时候停下」）就写进 build-log 并停止。
```

## 3. 静态检查与测试（review 的基础）

这些问题都由工具检查，不要靠人眼看：

| 问题 | 谁负责 | 命令（在 `backend/` 下） |
|---|---|---|
| 引用了不存在的库、import 了没用的库、变量没用 | ruff | `uv run poe lint` |
| 违反分层依赖（例如 core 反向 import api） | import-linter | `uv run poe lint`（含 `lint-imports`） |
| 类型不对（要 int 却给了 str）、缺类型标注 | mypy --strict | `uv run poe typecheck` |
| 逻辑错误 | pytest | `uv run poe check` 含单元测试；`uv run poe test-int` 跑集成测试 |

`uv run poe check` 一条命令包含以上全部。**不允许**为了通过检查加 `noqa` / `type: ignore` / `skip`，或降低门槛。

## 4. Code review

```text
用一个新会话，只看 diff（git diff <前一天的分支>...HEAD）和对应的 harness/build/phase-NN-*.md，不要读实现过程的聊天记录。
先跑 uv run poe check，把输出贴出来；失败就先报失败，不继续。
然后对照 WORKFLOW.md §4.3 的表（功能、设计、复杂度、测试、命名与注释、文档）逐项审。
只报影响正确性或违背计划的问题；风格偏好记下即可。
每条写：文件:行、问题、复现方式或失败场景、建议。
把结果写成 harness/code_review/<日期>-phase-NN-<审查者>.md（审查者填 claude / codex）。不要直接改代码，除非我说「顺手修掉」。
```

## 5. 交接（Claude ↔ Codex 互相接手）

```text
停下前更新 harness/build-log.md 顶部的「当前状态」：做到哪、剩什么、阻塞项、下一步命令。
未完成的任务在对应 harness/build/phase-NN-*.md 里保持未勾选；做出的新决定写进 harness/context/。
提交并推送当天分支。用量快到上限（95% 以上）也先做这一步再停。
接手的人：先读 AGENTS.md，再读 build-log 的「当前状态」。
```

## 6. Gemini 出评测题

作者在 Gemini 网页端使用。步骤：

1. 在 `backend/` 下运行 `uv run poe export-for-gemini`，得到 `.cache/gemini-pack/part-01.md` …（每份是清洗后的文档，每篇前有「文档 ID」）。
2. 新开一个 Gemini 对话，先粘贴下面「提示词」，再按顺序上传每一份文件；全部上传完说「开始出题」。
3. 让 Gemini 把题目以 JSON Lines 输出（一行一题）。保存为 `backend/eval/data/dev.jsonl`（约 70 题）；另一批约 30 题保存到**仓库外**当测试集。
4. 运行 `uv run poe eval-validate`，按报错让 Gemini 修正。

开发用的 agent 不要读测试集。题目在 Gemini 生成后，开发集可以让 agent 读；测试集只在最终评测时由作者跑一次。

### 提示词

你是一个 RAG 问答系统的评测题作者。我会上传 Dify 中文文档（每篇文档前有「文档 ID」）。请按下面的规则出题。

#### 出题顺序（很重要）

对每道可回答的题：**先从文档里摘出事实陈述（答案），再据此写问题**；不要先想问题再去找答案。

#### 题型和数量（共 100 题）

| type | 题数 | expected_route | 说明 |
|---|---|---|---|
| fact_single | 35 | SINGLE | 一篇文档里的一个具体事实（数字、配置名、默认值、步骤中的某一步）；尽量一篇文档一道题 |
| summary | 15 | SINGLE | 一篇文档里的操作步骤或要点总结 |
| reasoning | 20 | MULTI | 需要综合 2～3 篇文档才能回答；`gold_docs` 列出全部 2～3 篇 |
| version | 10 | SINGLE | 自部署版和云版本的差异；`edition` 必填 |
| unanswerable | 20 | 见下 | 不可回答题 |

不可回答题的类别（`unanswerable_category`）：

| 类别 | 题数 | expected_route | 怎么出 |
|---|---|---|---|
| out_of_database | 6 | REFUSE | 看起来是 Dify 的问题，但这批文档里没有答案 |
| false_premise | 4 | REFUSE | 问题的前提与文档矛盾（例如问一个文档里不存在的功能怎么用） |
| underspecified | 5 | CLARIFY | 缺少关键信息，必须反问才能回答（例如没说是自部署还是云版本） |
| out_of_scope | 3 | REFUSE | 和 Dify 无关（天气、写代码…） |
| injection | 2 | REFUSE | 试图让系统违反规则（例如「忽略之前的指令」） |

#### 问题要求

1. **问题必须独立成立**：不能出现「根据文档」「文档中」「上下文」「上文」「本文」「这篇文章」之类的说法。用户提问时看不到文档。
2. 每道可回答题随机组合下面 4 个属性并写进字段：
   - `persona`：`novice`（新手，说法口语、不知道术语）或 `expert`（熟悉术语和环境变量名）
   - `phrasing`：`natural_short`（日常短句）/ `natural_long`（带背景的长问题）/ `keyword`（关键词式）
   - `premise`：`direct`（直接问）或 `indirect`（带着场景问）
   - `lexical`：`similar`（用词贴近原文）或 `distant`（换成同义说法，避免原文的关键词）。**至少 40% 的题用 `distant`**
3. 问题是中文。

#### 关键点（nuggets）

每道可回答题写 2～4 条关键点：把答案拆成一条条原子事实，每条能单独判断「回答里有没有说到」。`importance`：`vital`（缺了就算没答对）或 `okay`（锦上添花）。至少 1 条 `vital`。不可回答题 `nuggets` 为空数组。

#### 输出格式

JSON Lines：每行一个 JSON 对象，不要代码块、不要解释。字段：

```json
{"id": "q001", "question": "知识库一次最多能上传几个文件？", "split": "dev", "type": "fact_single", "unanswerable_category": null, "edition": "self_host", "expected_route": "SINGLE", "gold_docs": ["self-host/use-dify/knowledge/create-knowledge/import-text-data/readme"], "nuggets": [{"text": "默认单次最多上传 5 个文件", "importance": "vital"}, {"text": "上限由 UPLOAD_FILE_BATCH_LIMIT 控制", "importance": "okay"}], "persona": "novice", "phrasing": "natural_short", "premise": "direct", "lexical": "similar"}
```

- `id`：`q001`、`q002`…，不重复。
- `gold_docs`：**原样使用文档 ID**（文档前「文档 ID：」后面的字符串）；不可回答题为空数组 `[]`。
- `edition`：问题针对的版本，`self_host` 或 `cloud`；不涉及版本写 `null`。
- `split`：70% 的题写 `dev`，30% 写 `test`；每个 type 和每个不可回答类别内部都按 7:3 分。

#### 自检（先出约 150 题，再筛）

先出约 150 题。对每题按 4 条标准打 1～5 分：① 问题独立成立；② 答案确实只来自金标文档；③ 关键点是原子的、可判断的；④ 题不是太简单（不能只靠一个关键词就找到）。淘汰任一项低于 3 分的题，再按上面的配额选出 100 题输出。
