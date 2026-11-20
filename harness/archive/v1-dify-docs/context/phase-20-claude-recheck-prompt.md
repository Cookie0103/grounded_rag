# 发给 Claude 的复审指令

```text
请拉取 grounded_rag 的 2026-10-20-dataset-repair 分支，复审 159ab99..HEAD。
本次先审查，不自动启动真实评审；真实评审会在这台电脑后续进行。

先读：
1. AGENTS.md 和 harness/build-log.md 当前状态；
2. harness/context/phase-20-review-repair.md；
3. harness/build/phase-20-judge-v2.md、docs/eval/runbook.md §11；
4. harness/code_review/2026-10-20-calibration-claude-prelabel.md；
5. harness/context/phase-20-v2-repair-freeze.json；
6. harness/context/phase-20-tools/ 中的新版外部脚本完整源码副本。

先纠正上一轮审查的授权前提：作者原任务“二/1/d”明确要求增加
“判断 nuggets 时，关键点只要被回答完整表达就是 support，附加的含糊说明或谨慎措辞不降级”。
因此保留该句有授权，不应以此作废36条标签。模板、Judge、evaluate均与旧冻结字节相同。
但v2同时改了contradiction依据和support解释，不能把全部分差归因于contexts；要单列nuggets变化。

重点验证：
- 冻结/模板哈希缺键、多键、重名或不等是否失败；单测是否确实覆盖缺键；
- 异常路径是否复核保护文件与冻结清单；强制终止时是否能靠落盘断点恢复；
- errors-history.json是否保留首次18条错误，补评成功是否不会删除历史；
- 整套错误超过10%是否立即停后续调用，恰好10%是否继续；
- --seed-run是否先验证旧模板及输入，然后只复制成功标签到全新目录；
- 旧36条标签是否保留且不会重复调用评审；旧v1/v2文件是否都未覆盖；
- 新旧冻结与Git来源关系是否真实，是否保持评分分值、题集和业务代码不变。

Codex本机最终检查：463 passed，35 deselected，覆盖率94.93%；ruff、lint-imports、mypy通过。
另以真实dev缓存做了不调用模型的迁移预检：36条标签字节保留，18条历史错误保留。
请独立核验，不把这些记录直接当成你已复现的结果。

真实数据需要单独复制新版仓库外包：grounded-rag-eval-handoff-20261020-repaired.zip。
SHA-256：87fae93feb1f0f179ae6c1d2ae5d0340a4c3977d34ce0e88bee20bd01da33ad9。
在仓库外解压，核验TRANSFER-MANIFEST.json；运行版工具在eval-rejudge-v2-repaired-20261020。
包缺失时可以审代码，但必须把缓存/外部工具实际运行标为未验证，不能宣称评测完成。

v1三套120题已跑完；v2仍只有dev36条，reg/test未开始。
复审通过后，按新版包内README可续评dev缺失34条，再reg20、仓库外test30；不重跑系统或检索。
之后生成三套报告、v1/v2对照、全部双向flips、逐点标签变化、种子20261021的20条dev/reg校准样本、
所有contradiction true→false的原回答核查，并保留18条历史错误。
作者/独立Claude标注后整题至少17/20一致才达85%；不能拿单测通过代替校准，不重抽或挑样本凑门槛。

请按严重程度输出问题、文件行号、证据和最小建议，并明确区分：
代码复审是否通过、真实重评是否完成、校准是否通过、整体能否收尾。
将本次复审报告写入harness/code_review/2026-10-20-judge-v2-repair-review.md。
```
