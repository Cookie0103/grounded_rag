# 首轮20题开发诊断报告

轮次：`2026-10-19_1855_dev20_full-service`；生成代码：`bd4a312c3e58b538b05ad703701346f76806ff06`。

先打开 [逐题可视报告](report.html)。它只展示本轮，没有跨轮次总览。

## 本轮发现

- 单篇可答题大量被分解，路由预期一致8/19；路由不一致不直接扣回答分。
- dev008 标注回复题最终拒答：上下文具备启用、手工添加、命中三项依据，但缺少未命中继续AI的事实，E=3/4、A=0。经历两轮检索、两次生成/校验。
- dev012 四个必答点均正确，但附加‘只能删除后重建’缺乏唯一性依据，按既定旧规则-1；该严格判断待作者复核。
- dev013 从SINGLE补检索得到输出命名，但未明确排除Chatflow。冻结金标将其列vital，本轮按部分覆盖；金标颗粒度待作者复核。
- dev014 事实有据，但Enterprise权限说明夹带Snippet引用，C单独扣分。
- dev017 正确分版本/套餐回答，虽然不是CLARIFY，仍判边界通过；4道边界题均通过。

## 五项能力指标

| 指标 | 单题宏平均 | 有效题数 | N/A |
|---|---:|---:|---:|
| 最终证据覆盖 E | 96.88% | 16 | 4 |
| 答案要点覆盖 A | 92.19% | 16 | 4 |
| 事实有据 F | 99.52% | 16 | 4 |
| 有效引用覆盖 C | 98.48% | 16 | 4 |
| 边界处理正确 B | 100.00% | 4 | 16 |

可信总分 **0.825**（范围−1到1，不是正确率）；bootstrap 95%区间 [0.575, 1.000]。
可答题完全正确13/16、基本正确1/16、未答1/16、无依据扩写1/16。按旧规则‘完全或基本正确’为87.50%；严格必答点覆盖A另列，不混为同一正确率。
文档Recall@5：13/16；P95=42.74秒，单并发且dev001含模型冷启动。生成费用按项目固定单价估算共¥0.9034，不含当前会话评审成本。

## 逐题结果

| ID | 预期→实际 | E | A | F | C | B | 可信得分 |
|---|---|---:|---:|---:|---:|---:|---:|
| dev001 | SINGLE→SINGLE | 2/2 | 2/2 | 3/3 | 3/3 | N/A | +1 |
| dev002 | SINGLE→MULTI | 2/2 | 2/2 | 4/4 | 4/4 | N/A | +1 |
| dev003 | SINGLE→MULTI | 2/2 | 2/2 | 3/3 | 3/3 | N/A | +1 |
| dev004 | SINGLE→MULTI | 2/2 | 2/2 | 5/5 | 5/5 | N/A | +1 |
| dev005 | SINGLE→MULTI | 3/3 | 3/3 | 7/7 | 7/7 | N/A | +1 |
| dev006 | SINGLE→MULTI | 3/3 | 3/3 | 3/3 | 3/3 | N/A | +1 |
| dev007 | SINGLE→MULTI | 2/2 | 2/2 | 5/5 | 5/5 | N/A | +1 |
| dev008 | SINGLE→MULTI | 3/4 | 0/4 | N/A | N/A | N/A | +0 |
| dev009 | SINGLE→MULTI | 4/4 | 4/4 | 8/8 | 8/8 | N/A | +1 |
| dev010 | SINGLE→MULTI | 4/4 | 4/4 | 14/14 | 14/14 | N/A | +1 |
| dev011 | MULTI→MULTI | 4/4 | 4/4 | 6/6 | 6/6 | N/A | +1 |
| dev012 | MULTI→MULTI | 4/4 | 4/4 | 12/13 | 12/13 | N/A | -1 |
| dev013 | MULTI→SINGLE | 3/4 | 3/4 | 14/14 | 14/14 | N/A | +0.5 |
| dev014 | MULTI→MULTI | 3/3 | 3/3 | 6/6 | 5/6 | N/A | +1 |
| dev015 | SINGLE→SINGLE | 4/4 | 4/4 | 4/4 | 4/4 | N/A | +1 |
| dev016 | SINGLE→SINGLE | 4/4 | 4/4 | 8/8 | 8/8 | N/A | +1 |
| dev017 | CLARIFY→SINGLE | N/A | N/A | 15/15 | 15/15 | 1/1 | +1 |
| dev018 | REFUSE→REFUSE | N/A | N/A | N/A | N/A | 1/1 | +1 |
| dev019 | REFUSE→REFUSE | N/A | N/A | N/A | N/A | 1/1 | +1 |
| dev020 | 不限→SINGLE | N/A | N/A | N/A | N/A | 1/1 | +1 |

## 阅读与复核

- report.html：问题、参考答案、实际回答、逐点/逐声明评分、云端链接和可展开的完整步骤；召回/精排/最终块、每次上下文与生成均可查看。
- questions.jsonl / evidence.json / metrics-v1.md：冻结标准及原文来源；results.jsonl / reviews.jsonl：结构化分数与理由；answers.jsonl / traces.jsonl：独立答案与完整原始过程。
- manifest.json：代码、语料、题集/标准哈希、模型配置与本地权重快照。服务端模型使用deepseek-flash别名，未保存供应商不可变版本，不假称完全可复现。
- cloud-verification.json：Langfuse服务端过程/分数读回核验；其状态以实际文件为准。
- 20题仍为开发草案，本轮由当前会话agent评审，未经作者人工校准；dev011题干的文本型PDF条件、dev012唯一性、dev013的Chatflow金标需重点复核。
- E/F/C已在本轮逐题核验并确定性汇总，不代表通用自动评审模型接入已完成。生成期间未改题集、参数或提示词，未重跑挑好答案。

原文来源为冻结Dify中文文档（CC BY 4.0），每条证据保留来源链接。

## 保存与恢复

- `answers-only.jsonl` 只放20条问题、最终答案、路由和云端链接，便于单独阅读；`answers.jsonl` 另含评测器需要的完整作答数据。
- 本地原始大文件和离线页面仍在本目录。`answers.zip`、`traces.zip`、`report.zip` 分别无损保存对应原件，`archive.zip` 保存题目、证据、评分和清单；四包均随Git提交，单包不超过已有1000KB门槛。
- 换电脑后把四包都解压到本目录，双击 `report.html` 即可查看，不依赖正在运行的服务或Langfuse保留期。也可在本目录PowerShell执行：`Get-ChildItem -Filter *.zip | ForEach-Object { Expand-Archive -LiteralPath $_.FullName -DestinationPath . -Force }`。
- `checksums.sha256` 核验各文件原件；所有ZIP解压内容已与本地逐字节核验。未创建跨轮次总览。
