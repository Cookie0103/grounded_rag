# 评审校准样本：Claude 预标对照（待作者确认）

样本：`eval-final-20261020/calibration-sample.md` 的 20 条（dev/reg，种子 20261020）。我按 `judge_v1` 的标签定义，只依据冻结原文与题集必答点独立预标，再与评审（Claude CLI）对照。这是**预标，不是作者人工校准**；作者需确认分歧项后才算完成 §3 校准。

## 结果：整题一致 16/20 = 80%（门槛 ≥85%，未达标）

| # | 题 | 评审 | 我的判断 | 一致 | 说明 |
|---|---|---|---|---|---|
| 1 | dev072 | 4 点 support；contradiction=true | 4 点 support；contradiction=false | ✗ | 回答每句都有 llm.mdx 依据（L141/143/145/148），该文清洗后仅 2819 字符，未被截断，找不到矛盾或编造 |
| 2 | dev049 | 拒答，3 点 not_support | 同 | ✓ | 系统真实失败：文档有成员上限，却答“找不到依据” |
| 3 | dev031 | refused | 同 | ✓ | |
| 4 | dev086 | refused | 同 | ✓ | |
| 5 | dev017 | covers_interpretations=true | 同 | ✓ | 覆盖云版/自部署/两种知识库，数字与旧 dev015/016 及流水线页一致 |
| 6 | dev067 | clarified | 同 | ✓ | |
| 7 | dev032 | corrects_premise=true | 同 | ✓ | |
| 8 | dev087 | refused，未纠正前提 | 同 | ✓ | 系统真实失败：应指出“触发器启动的工作流不能发布为 MCP”，却拒答 |
| 9 | dev005 | 3 点 support | 同 | ✓ | 额外内容在 team-members-management L34/L40/L60 |
| 10 | dev045 | clarified，3 点 not_support | 同 | ✓ | 系统真实失败：该题可直接作答，却反问 |
| 11 | dev071 | 2 点 support | 同 | ✓ | |
| 12 | dev028 | 2 点 support | 同 | ✓ | “Workflow 停止任务不检查 user”在 end-user-identity L21 |
| 13 | dev009 | 第 3 点 partial | 第 3 点 support | ✗（轻） | 回答明确写了“暂不支持导入图片和文件”，只是又加了一句“没单独说明附件”的含糊话；可争议 |
| 14 | dev035 | 全 support | 同 | ✓ | |
| 15 | dev059 | 全 support | 同 | ✓ | |
| 16 | dev012 | 第 3 点 partial | 第 3 点 support | ✗（轻） | 回答写了手动模式、条件 `product_line is alpha`、只检索符合条件的文档；可争议 |
| 17 | dev078 | 第 1 点 partial；contradiction=true | 第 1 点 partial；contradiction=false | ✗ | “message_end 后跟 workflow_finished”是真的（streaming.mdx L77），只是不在金标文档里 |
| 18 | dev030 | 全 support | 同 | ✓ | |
| 19 | dev074 | 全 support | 同 | ✓ | |
| 20 | dev029 | 全 support | 同 | ✓ | |

## 分歧的规律
1. **contradiction 误判（#1、#17，另有 dev024、dev052、dev084 同类）**：评审只看代表金标文档；系统说了文档别处的真实内容（如 dev024 的 `remove-abnormal-output` 在 predefined-error-handling-logic，不在 iteration 金标页，后者清洗后仅 1780 字符），就被当成编造并扣到 −1。dev072 的情况还不是这个原因，另需查评审输出。
2. 个别 partial/support 边界偏严（#13、#16），影响小。
3. 评审偏**严**，方向是低估分数；没有发现评审放过明显错误的情况。

## 对已报告数字的影响
开发题里“所有 vital 完整支持却被判矛盾”共 4 题（dev024、052、072、084）。若全属误判，开发题严格成功率约由 62.5% 升到 69.6%。回归 20 题未出现此类。

## 建议（需作者批准，因会改评审输入）
按 runbook §3：新增 `judge_v2.md`（不覆盖 v1），把系统实际检索到的上下文一并交给评审，规定“**回答中的具体说法只要被金标文档或这些上下文支持，就不算矛盾**”。答案已缓存（含 contexts），只需重评审，不必重跑系统。重评审后再抽 20 条（换种子）复测，一致率 ≥85% 才采信。
