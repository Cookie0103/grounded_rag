# 评测相关论文阅读笔记（2026-10-16）

proposal §6 引用的 6 篇论文都读过一遍。每篇写三部分：论文讲了什么、关键数字、在本项目里怎么用。
§7 把这些结论汇总成评测集和打分的具体规则，M3 的 Spec 直接以 §7 为准。

## 1. CRAG：Comprehensive RAG Benchmark（Meta，2024）

[arXiv 2406.04744](https://arxiv.org/abs/2406.04744)

**讲了什么**：4409 道问答的 RAG 基准，覆盖 8 种题型（简单事实、带条件事实、集合、比较、聚合、多跳、重后处理、错误前提），按时效性（实时 / 快变 / 慢变 / 静态）和热度分层。

**打分**：每个回答标为 4 类之一。

| 标签 | 含义 | 分数 |
|---|---|---|
| perfect | 正确且没有幻觉 | +1 |
| acceptable | 有用，但有不影响使用的小错 | +0.5 |
| missing | “不知道”、空回答、报错，**以及要求澄清** | 0 |
| incorrect | 错误或无关 | −1 |

可信得分（truthfulness）= 所有题的平均分 = 正确率 − 幻觉率。

**关键数字**：
- GPT-4 Turbo 直接回答：正确率 33.5%、幻觉 13.5%，可信得分 20.0%。加上简单 RAG 后，正确率升到 43.6%，幻觉也升到 30.1%，可信得分反而降到 13.4%。论文的解释是：检索到的无关内容会诱发幻觉。
- 最好的工业系统可信得分 50.6%，幻觉率仍在 16～25%。
- 自动评审用两个 LLM 互相制衡，与人工标注的准确率约 96～99%。

**在本项目里怎么用**：
- 直接采用 4 档打分和可信得分作为总分，因为“答错扣分、不答不扣分”正好对应我们要解决的问题 5（检索错了还自信地答）。
- “要求澄清”算 missing（0 分），但在**含糊题**上，反问是正确行为，按 §7.3 单独规则算 +1。
- 论文按题型分层报告。我们也要**按题型分别报告**，不只报一个总分。
- 论文用了“难负例”（名字很像的实体）。我们的天然难负例是云版和自部署版的 92 个同名页面，版本差异题就从这里出。
- 论文说明了“加检索反而更差”的可能，所以**无检索基线（M4）必须做**，不能默认 RAG 一定更好。DeepSeek 很可能在预训练里见过 Dify 文档，无检索基线未必很低。

## 2. TREC 2024 RAG Track：AutoNuggetizer（2025）

[arXiv 2504.15068](https://arxiv.org/abs/2504.15068)

**讲了什么**：用“关键点”（nugget）评估 RAG 回答的召回。nugget 是一条能二元判断“回答里有没有”的事实，按语义而不是字面匹配。

**流程**：
1. 生成 nugget：LLM 读相关段落，逐轮更新 nugget 列表，最多 30 条；每条 1～12 个词，写成陈述句。
2. 标重要性：`vital`（好回答必须有）或 `okay`（有更好，没有也行），保留前 20 条。
3. 判断覆盖：对每个回答，LLM 一次判断最多 10 条 nugget，标为 `support`（完整覆盖）、`partial_support`（部分覆盖）或 `not_support`（没有）。
4. 打分：只有 `support` 记 1 分。主指标 **V_strict** = 被完整支持的 vital nugget 数 / vital nugget 总数；**A_strict** 对全部 nugget 计算。

**关键数字**：
- 自动流程与人工流程在**系统层面**排序一致性高（Kendall τ 0.73～0.90），但在**单题层面**很低（τ 0.36～0.54）。
- LLM 判断比人更严，`partial_support` 标得更多。

**在本项目里怎么用**：
- 我们题少（100 道），nugget 由出题人直接写，不需要自动生成：每题 2～4 条，**至少 1 条 vital**。
- 主指标用 V_strict，同时报 A_strict。`partial_support` 不计分（strict）。
- 论文说明**单题判定不可靠**，所以 nugget 结果只看整体平均，不要拿单题结论下判断；单题分歧交给人工复核。
- nugget 判定同时作为 CRAG 打分的依据（规则见 §7.3），这样两个指标口径一致。

## 3. Sufficient Context：A New Lens on RAG Systems（Google，ICLR 2025）

[arXiv 2411.06037](https://arxiv.org/abs/2411.06037)

**讲了什么**：提出“上下文充分性”：给定问题和上下文，**能否从上下文推出一个合理答案**。判断时不需要标准答案，所以线上也能用。

**判定方法（autorater）**：提示词让模型先把问题拆成子问题（包括隐含假设和计算），逐个用上下文回答，再写理由，最后输出 JSON：`{"Sufficient Context": 1}` 或 `0`。Gemini 1.5 Pro 加 1 个示例，与人工标注一致率 93%。多跳题要求**每一跳**都有依据；含糊问题只有在上下文能消歧时才算充分。

**关键发现**：
- 上下文充分时，模型仍有 14～25% 的幻觉。
- 上下文不充分时，模型拒答的比例并不高，仍有 15～40% 在硬答。
- 加了检索之后，模型拒答的比例明显下降（比如 Gemini 从 100% 降到 18.6%），也就是检索让模型变得“更敢答”。
- 上下文不充分时仍有 35～62% 答对，主要靠模型自身知识或猜测（是非题、选项少的题等）。
- 论文用“充分性 + 模型自信度”做逻辑回归，决定是否拒答，正确率提升 2～10%。

**在本项目里怎么用**：
- **错误归因（评测）**：对每道答错或没答的可回答题，用同一个 autorater 判断“生成器实际拿到的上下文”是否充分。充分却答错，是生成问题；不充分，是检索问题。再结合 Recall@5 区分“没检索到”和“检索到但被截断”。
- **证据评分节点（系统）**：proposal 流程图里的“证据够吗”就是充分性判断。系统内用 DeepSeek 跑同样的提示词，评测时用 Gemini 跑，提示词放在 `prompts/sufficiency_v1.md`，两边共用。
- 不做逻辑回归式的选择性生成：开发集只有 70 题，训练不出可靠的阈值（YAGNI）。
- 不能“上下文不够就一律拒答”，否则会损失能答对的题。我们的策略是：不够就改写重检索（最多 2 次），仍不够时只回答有依据的部分，并明确说明缺什么；完全没有依据才拒答。

## 4. Know Your RAG：数据集分类与生成策略（IBM，COLING 2025）

[arXiv 2411.19710](https://arxiv.org/abs/2411.19710)

**讲了什么**：按“上下文能支持哪种答案”给问答对分类，并指出评测集的类型分布会改变结论。

| 类型 | 定义 |
|---|---|
| fact_single | 答案明写在上下文里，是一个信息点 |
| summary | 答案明写在上下文里，由多个信息点组成，可以部分答对 |
| reasoning | 答案没有直接写，需要从上下文简单推理 |
| unanswerable | 既没写，也推不出 |

**关键发现**：
- 公开数据集严重偏科，比如 NewsQA 83% 是 fact_single。
- 不同类型的检索召回差距可达 42%，reasoning 类最低。
- **最优检索参数随类型变化**：在全集上最优的混合检索权重，在单一类型上未必最优。
- 用一个提示词直接让 LLM 出题，95% 都是 fact_single。

**生成方法（先答案后问题）**：总结上下文主题 → 抽取最多 5 条事实陈述 → 按目标类型把陈述合并成 summary，或推出 reasoning 结论 → 选一条陈述，写一个只有它能回答的问题。

**质量过滤（LLM 打 1～5 分）**：
- 独立性：不看原文能否看懂？出现“根据上下文”这类说法就扣分。
- 具体性：问题是否具体到能检索到这篇文档？
- 问题与上下文的关联：上下文能否回答这个问题？
- 答案与上下文的关联：答案是否有上下文支撑？

**在本项目里怎么用**：
- 题型映射：单篇事实 → fact_single；操作步骤 / 总结 → summary；跨篇推理 → reasoning（多文档）；版本差异单列；不可回答 → unanswerable。
- **出题按“先答案后问题”做**，避免全变成 fact_single：先从文档里抽陈述，陈述直接变成 nugget，再写问题。
- 审题（Gemini）就用上面 4 条打分，任一项低于 3 分就淘汰。
- 先生成约 150 道，过滤后按配额选 100 道。
- 报告里**按题型分别给出 Recall@5 和可信得分**；调检索参数时既看全集，也看各类型。

## 5. UAEval4RAG：不可回答问题的评测（Salesforce，ACL 2025）

[arXiv 2412.12300](https://arxiv.org/abs/2412.12300)

**讲了什么**：把不可回答的请求分为 6 类，并分别评测 RAG 系统的拒答能力。

| 类别 | 难度 | 定义 |
|---|---|---|
| Underspecified | 难 | 缺少关键信息，例如问“允许带宠物吗”却没说地点 |
| False-presupposition | 易 | 前提与知识库矛盾 |
| Nonsensical | 中 | 错别字、语义不通 |
| Modality-limited | 中 | 要求系统不支持的输入或输出形式（如图片） |
| Safety-concerned | 中 | 有害、违法、侵犯隐私 |
| Out-of-Database | 易 | 与知识库相关，但知识库里没有答案 |

**指标**：
- **可接受率**：回答是否符合该类别的期望行为（每类有单独的判定标准，例如 Underspecified 时反问、或兼顾多种理解都算可接受）。
- **未作答率**：回答被判为“作答 / 反问 / 拒答”中的哪一种。

**关键发现**：
- 没有一种检索配置在所有数据集上都最好；**能把可回答题答好的配置，不一定能把不可回答题拒好**。
- 加一句“严格的拒答指令”能让可接受率从 53% 升到 84%，但在另一个数据集上，可回答题的正确率从 49% 降到 44%。
- Underspecified 最难，各模型可接受率只有 17～34%。
- LLM 评审与人工的一致率约 82～84%，需要用自己领域的数据抽查。

**在本项目里怎么用**：
- 20 道不可回答题按类别拆分为：文档没写（Out-of-Database）6、错误前提 4、含糊需反问（Underspecified）5、超范围 3、注入 2。注入题对应 Safety 类。Nonsensical 和 Modality-limited 与本项目的使用场景关系不大，不单独出题。
- 错误前提题从版本差异里出，例如“云版怎么改 `UPLOAD_FILE_SIZE_LIMIT`？”。云版用户不能改环境变量，正确行为是指出前提不成立。
- 每个类别的“可接受行为”写进评审提示词（规则见 §7.3）。
- 生成提示词里的拒答指令要做对照实验（M5 消融），同时看可回答题的正确率和不可回答题的可接受率。可信得分本身已经同时惩罚“硬答”和“答错”。

## 6. DataMorgana：生成多样化的 RAG 评测问题（TII，2025）

[arXiv 2501.12789](https://arxiv.org/abs/2501.12789)

**讲了什么**：用“问题类别 × 用户类别”的组合控制合成问题的多样性。每道题按概率给每个维度抽一个取值，把取值的描述写进出题提示词。每篇文档生成 3 个候选问题，经过过滤后保留一个。

**维度**：
- 事实性：factoid（具体事实）/ open-ended（开放）
- 前提：direct（直接问）/ with-premise（先交代自己的情况）
- 措辞：自然短句 / 自然长句 / 短关键词 / 长关键词
- 用词：similar-to-document（沿用文档术语）/ distant-from-document（换种说法）
- 用户：expert / novice

**关键发现**：
- 多样性的提升主要来自问题维度，用户维度贡献小。
- **每篇文档只出 1 道题时多样性最高**。
- 多样性指标偏爱复杂措辞，会低估朴素的新手问法，所以不要只看指标。

**在本项目里怎么用**：
- 每道题标 4 个属性：`persona`（novice / expert）、`phrasing`（natural_short / natural_long / keyword）、`premise`（direct / with_premise）、`lexical`（similar / distant）。抽样比例为：novice 50%，distant 50%，keyword 20%，with_premise 30%。
- `lexical=distant` 专门测问题 2（口语和术语对不上），比如“把资料喂给机器人”对应“知识库”。报告里按 `lexical` 分组看 Recall@5，这是查询改写是否有用的直接证据。
- 单篇事实题尽量做到**一篇文档一道题**，覆盖更多文档。
- 100 道题不计算多样性指标，只统计属性分布表，确认没有偏科。

## 7. 汇总：本项目的评测规则（M3 Spec 以此为准）

### 7.1 题目字段

题目存在 `backend/eval/data/dev.jsonl`（只读）；测试集用同样格式，放在仓库外。

```json
{
  "id": "q001",
  "question": "知识库单次最多能上传几个文件？",
  "split": "dev",
  "type": "fact_single",
  "unanswerable_category": null,
  "edition": "self_host",
  "expected_route": "SINGLE",
  "gold_docs": ["self-host/use-dify/knowledge/create-knowledge/import-text-data/readme"],
  "nuggets": [
    {"text": "默认单次最多上传 5 个文件", "importance": "vital"},
    {"text": "上限由 UPLOAD_FILE_BATCH_LIMIT 控制", "importance": "okay"}
  ],
  "persona": "novice",
  "phrasing": "natural_short",
  "premise": "direct",
  "lexical": "similar"
}
```

- `type`：`fact_single` / `summary` / `reasoning` / `version` / `unanswerable`
- `unanswerable_category`：`out_of_database` / `false_premise` / `underspecified` / `out_of_scope` / `injection`，可回答题为 `null`
- `edition`：问题针对的版本，`self_host` / `cloud`，不涉及版本为 `null`
- `expected_route`：`DIRECT` / `SINGLE` / `MULTI` / `CLARIFY` / `REFUSE`
- `gold_docs`：文档 ID，即去掉 `zh/` 前缀和 `.mdx` 后缀的相对路径（M1 定义）；不可回答题为空列表
- 多跳题（reasoning）的 `gold_docs` 有 2～3 篇，Recall@5 要求全部命中

### 7.2 配额

| type | 题数 | 期望路由 |
|---|---|---|
| fact_single | 35 | SINGLE（极少数闲聊为 DIRECT） |
| summary（操作步骤 / 总结） | 15 | SINGLE |
| reasoning（跨 2～3 篇） | 20 | MULTI |
| version | 10 | SINGLE，`edition` 必填 |
| unanswerable | 20 | out_of_database 6、false_premise 4 → REFUSE；underspecified 5 → CLARIFY；out_of_scope 3、injection 2 → REFUSE |

每个 type 按 7:3 分到 dev 和 test，按类别分层抽样。

### 7.3 打分

**第一步：评审给每个回答打标签。** 评审拿到问题、nuggets、金标文档原文和系统回答，输出 JSON：
- 每条 nugget 标为 `support` / `partial_support` / `not_support`
- `contradiction`：回答里有没有与金标文档矛盾、或文档中不存在的具体说法（true / false）
- `behavior`：`answered` / `clarified` / `refused`

**第二步：按规则换算成 CRAG 标签（代码计算，不让评审直接给分）。**

可回答题：

| 条件 | 标签 | 分数 |
|---|---|---|
| `behavior` 不是 answered | missing | 0 |
| `contradiction` 为 true | incorrect | −1 |
| 所有 vital 都是 support | perfect | +1 |
| 至少一条 vital 是 support 或 partial_support | acceptable | +0.5 |
| 其他情况（答了但没答到点） | incorrect | −1 |

不可回答题：

| 类别 | +1（可接受） | −1 |
|---|---|---|
| out_of_database、out_of_scope、injection | refused，或明确说明文档没有相关内容 | answered 且给出具体做法或结论 |
| false_premise | 指出前提不成立（refused 或 answered 都可以，只要纠正了前提） | 顺着错误前提作答 |
| underspecified | clarified，或同时给出几种理解下的答案（例如两个版本分别怎么做） | 只按一种理解直接作答 |

不可回答题没有 0 分档：判为“可接受”记 +1，否则记 −1。

**第三步：汇总指标。**

| 指标 | 定义 |
|---|---|
| 可信得分 | 全部题的平均分；附 bootstrap 95% 置信区间（重采样 1000 次） |
| 正确率 / 幻觉率 / 未作答率 | 可回答题中 perfect+acceptable / incorrect / missing 的比例 |
| 不可回答可接受率 | 不可回答题中 +1 的比例，按类别分别报告 |
| V_strict / A_strict | 可回答题的 nugget 指标（strict，只算 support） |
| Recall@5 | 精排后前 5 个块所属文档覆盖全部 `gold_docs` 的比例（只算可回答题） |
| 路由准确率 | 实际路由 = `expected_route` 的比例（诊断用；Adaptive-RAG 论文里训练过的分类器也只有约 54%） |
| P95 延迟、每题成本 | 端到端 |

所有指标都按 `type`、`lexical`、`edition` 分组报告。

### 7.4 评审流程

1. 主评 Gemini，复评 Claude，两边用同一个提示词、`temperature=0`，只输出 JSON。
2. 两边标签不一致的题交作者人工判。一致率低于 85% 时，先修评审提示词，不采信这一轮结果。
3. **校准**：第一次跑开发集后，作者人工标注 20 条回答，与 Gemini 的标签对比。一致率达到 85% 以上，才开始用自动评审比较方案。
4. 错误归因：对答错或没答的可回答题，用 `prompts/sufficiency_v1.md` 判断生成器拿到的上下文是否充分，再结合 Recall@5 归到下面三类之一：
   - 没检索到（金标不在前 5）
   - 检索到了但上下文不充分（被截断、或父块扩展不够）
   - 上下文充分却答错（生成问题）

### 7.5 出题流程（Claude）

1. 按配额选文档：单篇事实题尽量一篇文档一道题；版本题从 92 个同名页面里选；跨篇题选内容有关联的 2～3 篇。
2. 读文档，写主题和事实陈述（先答案后问题）。
3. 按配额抽 4 个属性，写问题。问题必须独立成立，不能出现“文档 / 上下文 / 上文”这类说法。
4. 陈述转成 nugget，标 vital / okay；写期望路由。
5. 先生成约 150 道，交 Gemini 按 4 条标准打分，淘汰任一项低于 3 分的，再按配额选出 100 道，交作者确认。
