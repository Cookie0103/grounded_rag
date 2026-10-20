# judge_v2 交接审查（只读）

日期：2026-10-20。分支 `2026-10-20-dataset-repair`，HEAD `159ab99`，对比基线 `0683dae`。

## 审查范围与证据强度

- **VERIFIED（我运行/比对了）**：`git diff 0683dae..HEAD` 全量阅读 `backend/eval/{judge,evaluate,metrics,scoring,dataset}.py`、`backend/scripts/rejudge.py`、`judge_v2.md`；`judge_v1.md` 对基线无 diff；`.venv/bin/python -m pytest tests/unit/eval tests/unit/scripts/test_rejudge.py tests/unit/scripts/test_eval_round.py` → 107 passed。
- **未能核实**：迁移包 `grounded-rag-eval-handoff-20261020.zip` 不在本机（Downloads/Desktop/开発 及全盘按名搜索均无）。因此 v1/v2 缓存、`checkpoint.json`、`resume_dev70.py`、`audit_v2.py` 的**内容一律 ASSUMED，未审**。B 部分只能依据仓库内文档陈述，不能给出通过结论。
- 我没有重跑 `uv run poe check`（`uv` 因 `exclude-newer` 拒绝解析 fastapi，属环境问题，非代码问题）；"449 测试 / 覆盖率 94.93% / ruff / mypy / lint-imports" 为交接文档所述，未复现。
- 未运行任何真实评审、未读取测试题内容。

## 问题清单（按严重程度）

### P1 — judge_v2 含一条未经批准的额外规则（影响校准结论的可解释性）
- 位置：`backend/eval/prompts/judge_v2.md:58`（"判断 nuggets 时……附加的含糊说明或谨慎措辞不降级"）；测试 `tests/unit/eval/test_judge.py:64` 还把它固化了。
- 事实：批准方案（phase-20 需求、预标报告"建议"）只授权"回答中的具体说法被金标**或检索上下文**支持就不算矛盾"。预标里 partial/support 边界（#13、#16）被明确标为"轻、影响小、可争议"，**没有**被批准为改规则对象。
- 影响：这是对 nugget 降级的放宽，会把 `partial_support` 抬成 `support`，方向是**抬高分数**；且与 contexts 变化叠加，v1→v2 的差异无法归因到"补充上下文"。对简历上"评审偏严已修正"的叙述有风险。
- 最小修复：二选一——(a) 删除该行及测试断言，重新说明 v2 只改 contradiction；(b) 由作者明确书面批准并写进 phase-20 "记录"，同时 v1/v2 对照里单列 partial→support 的变化。**无论哪种，已存的 36 条 dev v2 标签都是在该提示词下产生的**；若选 (a) 这 36 条必须作废重评（哈希已冻结，须重新冻结，不能静默改）。

### P1 — 三套 v2 重评未完成，校准未进行（结论性缺口）
- dev70：36 成功 / 18 明确错误 / 16 无标签；reg20、test30 未开始；`calibration-sample-v2.md`、`flips-spot-check.md` 未生成。
- v1 校准 80% < 85% 门槛；v2 尚无任何一致率数据。**因此不能说评测校准通过，也不能对外引用 v2 数字。**

### P2 — `audit_v2.py` 模板哈希检查缺键默认通过（交付前必须修，未亲自审查脚本）
- 来源：`harness/context/phase-20-cross-computer-review.md`。我没有该脚本。
- 要求：改为对冻结值的显式相等比较；缺键、多键均 fail。并加一条"缺键应失败"的自测。

### P2 — 错误历史靠外部脚本保留，主代码会覆盖
- 位置：`backend/scripts/rejudge.py:116`，每次 `_write_result` 都整体重写 `errors.json`，只反映当前一次运行的状态。
- 影响：补评成功后，首次限额造成的 18 条错误只存在于仓库外 `checkpoint.json`；文档要求保留，但没有代码/测试保证。
- 最小修复：交付时把 18 条首次错误原样写进最终 `errors-history.json`（带时间与原因"session limit"），在 v1/v2 对照里单列；不要删除。

### P3 — rejudge 的"文件未被改动"校验只在正常结束时执行
- 位置：`rejudge.py:~231`。异常路径（如 pilot 后崩溃）不做哈希复核；`_prepare` 之后到结束之间若输入被改，不会被发现。
- 影响小（仓库外外部脚本才是实际续评路径）。建议用 `try/finally` 复核。

### P3 — 有损清洗后缺少 `contexts` 顺序/截断的端到端断言
- `format_contexts`（`judge.py:98-105`）实现正确：保序、含标记总长 ≤24000、空资料有说明；单测覆盖了拼接、标记、边界。无缺陷，仅提醒"空串+非空串混合"时空串仍占分隔符（无影响）。

## 对 A 项逐条结论

| 检查点 | 结论 |
|---|---|
| judge_v1.md 保留、v1 默认行为兼容 | **通过**。v1 文件无 diff；测试用 SHA-256 锁住 v1 prompt，且 v1 忽略 contexts |
| judge_v2 只含批准的修改 | **不通过**，见 P1（第 58 行） |
| contexts 用缓存原文、顺序、≤24000 含标记 | **通过**（`judge.py:98-105`，`evaluate.py` 只传 `answer.contexts`） |
| rejudge 只读旧回答、不跑系统/检索 | **通过**（只 `load_cache`/`load_verdicts`，仅创建 `claude -p` judge） |
| 拒绝覆盖已有输出目录 | **通过**（`rejudge.py:137`，且禁止输出在旧运行目录内、test 输出必须在仓库外；有测试） |
| 错误单列、分母 | **通过**（`planned/judged/error/not_reviewed` 分列；错误不进分母）；历史保留见 P2 |
| 等价来源召回 | **通过**（`hit_groups_at_k` 组间 AND、组内 OR；MRR 用 `all_gold_docs`；空组返回 False，旧题退化为逐篇必需） |
| scoring.py 改动 | **未改逐题分值**。diff 仅新增 `TrustSummary.strict_success`（默认 0.0）及 `share(answerable,(PERFECT,))`、注释；不违规 |
| 测试能否发现上述错误 | 基本能（v1 哈希、截断、目录、错误、flips 双向）。**不能**发现 P1，因为测试把额外规则当成了契约 |

## B 项（迁移与交付脚本）
- `resume_dev70.py` 复用 36 条标签：**无法验证**（包不在本机）。审查时需确认它先校验 `protected-hashes.json`/`v2-frozen.json`，且只对缺失的 34 题（18 错误 + 16 无标签）调用评审。
- 注意：若 P1 选择"删除第 58 行"，则 `v2-frozen.json` 中的模板哈希随之失效，`resume_dev70.py` 的冻结检查会（应当）失败——这是正确行为，不要为了续评去放宽检查。
- Git HEAD 关系：冻结清单里的旧 HEAD 是评测当时来源；现 HEAD `159ab99` 在其后。做法：保留旧值不改，在最终交付里追加一条"迁移关系"记录（旧 HEAD → 159ab99，并以文件内容 SHA-256 为准核对），不要改写原清单。

## 结论

1. **v2 代码审查：不通过**（1 个 P1：judge_v2.md:58 未批准的规则；其余接线、防覆盖、contexts、指标均正确）。
2. **三套 v2 重评：未完成**（dev70 36/70，reg20/test30 未开始）。
3. **评审校准：尚未进行**（v1 为 80%，未达 85%）。
4. **现在能否收尾：不能。** 评测不是"最后一口气"——还缺：

   1. 处理 judge_v2.md:58（删除并重冻结，或作者书面批准并在对照里单列）。若删除，需作废已有 36 条 dev v2 标签。
   2. 修 `audit_v2.py` 模板哈希显式比较（需包内脚本）。
   3. 等 Claude 额度恢复（文档称东京 23:50，**未确认**）后，由作者明确授权，续评 dev70 剩余题 → reg20 → test30（不得据 test 结果改提示词）。
   4. 生成：三套 v2 报告、v1/v2 对照（保留 18 条历史错误）、完整双向 flips、种子 20261021 的 20 条 dev/reg 校准样本、所有 contradiction true→false 的原回答核查。
   5. 校准样本一致率 ≥85% 才可采信 v2；否则 v2 仍只是"初步"，不能写进简历作为正式数字。

## 给简历/复盘的建议（不依赖评测收尾）
- 现在可以**开始写复盘**，因为 v1 完整三套结果、校准未达标的发现、"评审只看金标导致 contradiction 误判"的根因分析、以及发现并拦截提示词越权改动的过程，本身都是有价值的工程内容。
- 简历**不要**写 v1 或 v2 的绝对准确率/可信得分作为最终成绩；v1 偏严已被预标证实，v2 未校准。如需数字，写"v1 初步结果，评审校准一致率 80%（未达 85% 门槛），正在做 v2 校准"。
