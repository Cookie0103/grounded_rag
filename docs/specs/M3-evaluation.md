# M3：评测

状态：已批准（长程任务模式，agent 自批）

## 需求

### 目标

1. 评测框架：读题 → 让被测系统回答 → 评审打标签 → 代码按规则换算分数 → 出报告。规则以 [notes-evaluation §7](../implementation-log/2026-10-16/notes-evaluation.md) 为准。
2. 评审可以接真实的大模型（DeepSeek、命令行里的 Claude / Gemini）；没有密钥时用假评审跑通全流程。
3. 帮作者出题：题目格式校验、把清洗后的语料导出成能喂给 Gemini 的文件、一份可以直接粘贴的出题提示词。
4. 一条命令出报告：`poe eval-dev`。

### 非目标

- 正式的 100 道题：作者用 Gemini 出，放 `backend/eval/data/`（只读）。冒烟集只验证流程。
- 无检索基线、朴素 RAG、完整系统：M4、M5。M3 的被测系统只有「只检索」，用来出检索指标。

### 接口

**题目**（`backend/eval/data/{dev,test}.jsonl`，一行一题）字段：`id`、`question`、`type`（fact_single / summary / reasoning / version / unanswerable）、`unanswerable_category`（out_of_database / false_premise / underspecified / out_of_scope / injection，可回答题为 null）、`edition`、`expected_route`（DIRECT / SINGLE / MULTI / CLARIFY / REFUSE）、`gold_docs`、`nuggets`（`[{"text", "importance": "vital|okay"}]`）、`persona`、`phrasing`、`premise`、`lexical`、`split`。

**评审输出**（一个 JSON）：

```json
{"nuggets": ["support", "not_support"], "contradiction": false, "behavior": "answered",
 "corrects_premise": false, "covers_interpretations": false}
```

**换算**（代码，不让评审直接给分）：

| 情况 | 标签 | 分数 |
|---|---|---|
| 可回答题：没作答（反问或拒答） | missing | 0 |
| 作答但有矛盾 | incorrect | −1 |
| 所有 vital 都 support | perfect | +1 |
| 至少一条 vital 是 support 或 partial_support | acceptable | +0.5 |
| 其他 | incorrect | −1 |
| 不可回答题：做到该类别的可接受行为 | acceptable | +1 |
| 不可回答题：其他 | incorrect | −1 |

可接受行为：out_of_database / out_of_scope / injection → 拒答；false_premise → 纠正了前提；underspecified → 反问，或同时回答了几种理解。

**指标**：可信得分（附 bootstrap 95% 置信区间）、正确率 / 幻觉率 / 未作答率、V_strict / A_strict、不可回答题按类别的可接受率、Recall@5、路由准确率、P95 延迟、平均成本；全部按题型 / 用词 / 版本分组。

### 命令

- `poe eval-validate [--questions 文件]`：校验题目格式、金标文档是否都在语料里、配额、泄漏提示。
- `poe export-for-gemini`：把清洗后的语料分成几份 Markdown，放 `.cache/gemini-pack/`。
- `poe eval-dev [--system retrieval] [--judge none|deepseek|command:...] [--questions 文件] [--limit N]`：跑评测并出报告，中断后可续跑。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | 打分规则逐条有测试，覆盖上表每一行和每个不可回答类别 | 单元测试 |
| AC2 | 评审提示词、输出解析（含带多余文字的 JSON、缺字段、数量不对）有测试 | 单元测试 |
| AC3 | 评测器：并发、缓存、续跑、出错不中断 | 单元测试 |
| AC4 | 题目校验器能发现各种常见问题 | 单元测试 |
| AC5 | `poe eval-dev` 在冒烟集上用「只检索」系统出报告（Recall@5 按组） | 命令输出 |
| AC6 | `poe export-for-gemini` 导出 182 篇，每篇带文档 ID | 命令输出 |
| AC7 | `poe check` 通过，CI 全绿 | |

## 任务

- [x] T1 题目格式、校验器 → AC4
- [x] T2 打分、指标、置信区间 → AC1
- [x] T3 评审（提示词、解析、LLM 评审、命令行评审） → AC2
- [x] T4 被测系统接口、评测器（并发、缓存、续跑）、报告 → AC3、AC5
- [x] T5 导出语料、出题提示词、`eval-dev` 命令 → AC5、AC6
- [x] T6 收尾 → AC7

## 阻塞

- 正式的开发集和测试集要作者用 Gemini 出（见 `docs/eval/gemini-question-prompt.md`）；真实评审要密钥或可用的命令行。

## 记录
