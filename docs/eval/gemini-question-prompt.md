# 给 Gemini 的出题提示词

> 作者在 Gemini 网页端使用。步骤：
> 1. 在仓库 `backend/` 下运行 `uv run poe export-for-gemini`，得到 `.cache/gemini-pack/part-01.md` …（每份是清洗后的文档，每篇前有「文档 ID」）。
> 2. 新开一个 Gemini 对话，先粘贴下面「提示词」，再按顺序上传每一份文件；全部上传完说「开始出题」。
> 3. 让 Gemini 把题目以 JSON Lines 输出（一行一题）。保存为 `backend/eval/data/dev.jsonl`（约 70 题）；另一批约 30 题保存到**仓库外**当测试集。
> 4. 运行 `uv run poe eval-validate`，按报错让 Gemini 修正。
>
> 开发用的 agent 不要读测试集。题目在 Gemini 生成后，开发集可以让 agent 读；测试集只在最终评测时由作者跑一次。

## 提示词

你是一个 RAG 问答系统的评测题作者。我会上传 Dify 中文文档（每篇文档前有「文档 ID」）。请按下面的规则出题。

### 出题顺序（很重要）

对每道可回答的题：**先从文档里摘出事实陈述（答案），再据此写问题**；不要先想问题再去找答案。

### 题型和数量（共 100 题）

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

### 问题要求

1. **问题必须独立成立**：不能出现「根据文档」「文档中」「上下文」「上文」「本文」「这篇文章」之类的说法。用户提问时看不到文档。
2. 每道可回答题随机组合下面 4 个属性并写进字段：
   - `persona`：`novice`（新手，说法口语、不知道术语）或 `expert`（熟悉术语和环境变量名）
   - `phrasing`：`natural_short`（日常短句）/ `natural_long`（带背景的长问题）/ `keyword`（关键词式）
   - `premise`：`direct`（直接问）或 `indirect`（带着场景问）
   - `lexical`：`similar`（用词贴近原文）或 `distant`（换成同义说法，避免原文的关键词）。**至少 40% 的题用 `distant`**
3. 问题是中文。

### 关键点（nuggets）

每道可回答题写 2～4 条关键点：把答案拆成一条条原子事实，每条能单独判断「回答里有没有说到」。`importance`：`vital`（缺了就算没答对）或 `okay`（锦上添花）。至少 1 条 `vital`。不可回答题 `nuggets` 为空数组。

### 输出格式

JSON Lines：每行一个 JSON 对象，不要代码块、不要解释。字段：

```json
{"id": "q001", "question": "知识库一次最多能上传几个文件？", "split": "dev", "type": "fact_single", "unanswerable_category": null, "edition": "self_host", "expected_route": "SINGLE", "gold_docs": ["self-host/use-dify/knowledge/create-knowledge/import-text-data/readme"], "nuggets": [{"text": "默认单次最多上传 5 个文件", "importance": "vital"}, {"text": "上限由 UPLOAD_FILE_BATCH_LIMIT 控制", "importance": "okay"}], "persona": "novice", "phrasing": "natural_short", "premise": "direct", "lexical": "similar"}
```

- `id`：`q001`、`q002`…，不重复。
- `gold_docs`：**原样使用文档 ID**（文档前「文档 ID：」后面的字符串）；不可回答题为空数组 `[]`。
- `edition`：问题针对的版本，`self_host` 或 `cloud`；不涉及版本写 `null`。
- `split`：70% 的题写 `dev`，30% 写 `test`；每个 type 和每个不可回答类别内部都按 7:3 分。

### 自检（先出约 150 题，再筛）

先出约 150 题。对每题按 4 条标准打 1～5 分：① 问题独立成立；② 答案确实只来自金标文档；③ 关键点是原子的、可判断的；④ 题不是太简单（不能只靠一个关键词就找到）。淘汰任一项低于 3 分的题，再按上面的配额选出 100 题输出。
