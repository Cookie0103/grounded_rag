# judge_v2 Windows收尾核验

日期：2026-10-20。来源提交包含 `97623e6`；只读复算、审计和独立预标，没有真实模型调用，没有修改业务、评分、模板、题集或evidence。

## 状态结论

| 项目 | 当前结论 |
|---|---|
| 代码复审 | Claude已通过，见repair-review |
| 三套真实重评 | 完成，70/20/30均无当前错误，本机已核实原标签 |
| 数字对账 | v1/v2六行汇总、95%区间、等价来源Recall@5重算一致 |
| 严格技术审计 | Windows运行原版脚本通过；82保护文件和6实现文件原始SHA精确匹配 |
| 独立预标 | 16/20整题一致＝80%，未达85%；不是人工校准 |
| 正式人工校准 | 尚未完成，不能称通过 |
| 能否对外用最终成绩 | 不能；可以归档初步结果、准备功能与方法层面的简历描述 |

## 数据接收与完整性

- 原修复包SHA-256：`87fae93feb1f0f179ae6c1d2ae5d0340a4c3977d34ce0e88bee20bd01da33ad9`；仓库外新目录解压，96文件逐项核验。
- Mac新增结果包：`D:/Chrome_Downloads/grounded-rag-v2-results-mac-20261020.zip`；SHA-256：`bd6bfa8e4fa55a733001719ea7b9fc6356ca09751615180ba23018a653b8da06`。41文件，CRC、路径越界、符号链接和重复项检查通过，原包保留。
- 三套原标签题号完整且唯一，当前错误清单均为空；旧36条标签逐项保持一致，开发新增34条标签。首次18条限额错误原文保留在历史中。
- 测试题原文、回答、逐题核查和全部原始缓存均只在仓库外或被忽略缓存中；本报告不转录测试内容。

## 重算的初步数字

| 题集 | 严格成功率v1→v2 | 宽松正确率（含部分）v1→v2 | 可信得分v1→v2 | v2可信得分95%区间 |
|---|---|---|---|---|
| dev70 | 62.50%→67.86% | 69.64%→82.14% | +0.557143→+0.728571 | [+0.600000, +0.835714] |
| reg20 | 68.75%→87.50% | 81.25%→87.50% | +0.750000→+0.900000 | [+0.750000, +1.000000] |
| test30 | 95.83%→95.83% | 95.83%→95.83% | +0.833333→+0.833333 | [+0.633333, +1.000000] |

严格/宽松分母分别是56、16、24道可回答题；可信得分分母分别70、20、30，保留可回答题未作答的0分。三套分别报告，不混合。全部`comparison.json`六行汇总字段及各套`metrics.json`与原评分函数重算完全一致。这证明计算正确，不证明原评审标签都正确。

## 原版严格审计

在Windows实际执行的脚本是原迁移包的`audit_v2.py`，源码字节与Mac传回脚本相同，未采用换行符等价、未改任何预期SHA。

Mac运行manifest的绝对路径在Windows不可直接访问。本轮保留接收包、原始manifest和标签，只在全新派生副本映射路径；所有哈希值原样保留，并逐项验证映射目标原始字节。原始manifest另存`manifest.mac-original.json`，映射过程有完整前后哈希记录。扩展绝对路径用于避免原脚本对历史Windows前缀再次重定位，未跳过任何检查。

实际命令（backend目录）：

```powershell
.venv/Scripts/python.exe C:/Users/user/.codex/visualizations/2026/10/20/01a158d1-5d55-7d72-9647-6d2defd22b8e/eval-closeout-20261020/audit-layout/eval-rejudge-v2-repaired-20261020/audit_v2.py D:/项目/秋招项目/SONY/grounded_rag
```

退出码0；输出`all_passed: true`：三套70/20/30、当前错误0、新系统回答文件0；全部26题标签变化完整；true→false共10题，反向1题；固定20条样本只含dev/reg、原回答逐字转录、人工栏空白；来源祖先关系及历史18条错误留存通过。

首次直接审计旧迁移包时因尚未取得Mac新增结果失败，未冒充通过。取得新包及完成上述路径映射后原版全量审计才成功。运行日志与映射证明在仓库外`eval-closeout-20261020/windows-audit.log`、`windows-path-mapping-proof.json`，审计JSON在同目录`audit-layout/eval-rejudge-v2-repaired-20261020/audit-v2.json`。

## 全量翻转及逐点变化核查

- true→false：dev8、reg1、test1，10题全部对照原回答、代表金标及实际缓存contexts；反向dev023也核查。
- 9条正向翻转的主要具体事实能找到依据；另1条存在概括性表述冲突风险，细节仅见仓库外核查，不据测试修改系统或提示词。不能声称全部翻转已获人工认可。
- dev062的文件签名链接必答点并未由邀请链接说明覆盖，v2给partial仍需复核；当前评分仍为+0.5，不改原标签。
- dev078的触发机制是否完整表达、dev084的no-cache与root备选边界也单独记录，未把新增support自动归因于contexts。
- 反向dev023：实际检索包含云版与自部署API，两版清洗后的金标原文完全相同，SHA-256均为`6b6d54bfac98d1e949fadc29ccaf48e6de236ec7d7de568adedd8238df8b01f2`。新增contradiction疑似仍有版本来源识别偏严的风险，保留原判，待人工裁决。
- 全部15题/15个逐点变化已单列：partial→support 8，support→partial 4，partial→not 1，not→partial 2。v2同时调整contradiction依据和support解释，不能把整题分差全归因于contexts。

完整原回答及逐题证据仅在仓库外`flips-reviewed.md`、`flip-evidence/`和`nugget-changes-review.md`。

## 独立预标结果与剩余人工动作

收到Mac包路径后、读取其中最终标签前，Codex已基于固定样本的原回答、金标和contexts冻结20条五字段预标。预标SHA-256：`e319bd11aa2078e1cac86251c670543fbb199c07c42bcb4f6b0314aa82061aeb`。样本种子20261021，分布为可回答12、拒答3、反问/多理解3、纠正前提2，未重抽。

Codex独立于Claude CLI标签，但参与过实现，因此这仍是**agent预标，不是独立人类校准**；已经知道旧v1校准背景，不声称完全不知道历史。逐题按nuggets、contradiction、behavior、corrects_premise、covers_interpretations五字段全等比较，16/20＝80%，未达85%。

| 题号 | 分歧 | Codex预标 | Claude v2 | 是否影响本题原评分 |
|---|---|---|---|---|
| dev054 | covers_interpretations | false：题意明确，附加另一部署说明不算歧义覆盖 | true | 否，可回答题 |
| dev089 | corrects_premise | false：提问是否保证，没有直接断言保证 | true | 否，题型按多理解覆盖计分 |
| dev030 | covers_interpretations | false：题目明确分别问两版，不是缺版本的歧义 | true | 否，可回答题 |
| dev008 | 第2点nugget | not_support：系统只拒答，未表达录入问答做法 | partial_support | 否，拒答使该可回答题仍为0分 |

原分数一致20/20只作诊断，**不能用它替代整题85%门槛，也不能事后忽略字段来提高一致率**。本轮不改预标、不改正式标签、不重抽、不真实重评。

剩余最少外部输入：作者或独立标注者对固定20条提供参考标签并裁决上述分歧，按原整题口径至少17/20一致才可采信。完整盲标表`calibration-human-blank.md`不含Claude/Codex标签；对照与理由在`calibration-prelabel-v2.md`。正式校准未完成前，所有v2成绩仍写“初步结果，校准未通过/待人工确认”。
