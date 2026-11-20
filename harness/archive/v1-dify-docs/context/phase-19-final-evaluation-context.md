# 阶段19：三套初步评测交接

- 2026-10-20：按作者明确命令执行70开发、20回归、30测试。正式调用原`scripts.eval_run.run`，不改FullSystem、Judge、scoring、Prompt、预算和题集。临时编排只负责前三题切片、同run-id缓存续跑、错误停机与存储/云端开关。
- 开发和回归输出：`.cache/eval/runs/final-dev70/full/`、`.cache/eval/runs/final-reg20/full/`。完整回答为answers.jsonl，逐点/矛盾/行为标签为verdicts.jsonl；原始报告raw-report.md与补充分母的report.md均保留。metrics.json记录精确值与完成计数，manifest.json保存实际配置和代码/题集哈希。
- 测试进程内清空Langfuse两项凭据并断言未初始化客户端，未调用HTTP服务。全部测试原始输出在仓库外：`C:/Users/user/.codex/visualizations/2026/10/20/01a158d1-5d55-7d72-9647-6d2defd22b8e/eval-final-20261020/test-storage/eval/runs/final-test30/full/`。仓库内`.cache/eval/runs/final-test30/full/`只有聚合报告、指标、ID错误清单与外部路径说明。
- 统一交付目录为上述本聊天仓库外的`eval-final-20261020/`，含overview.md、calibration-sample.md、lowest-10.md、regression-comparison.md、reproducibility.json、audit.json及可复查的编排/整理脚本。各套结果分别报告，不计算混合总数。
- Claude CLI版本与默认模型选择写入manifest；CLI没有返回可核验的实际模型ID，不猜测型号。评审标签沿用原Prompt，分数复用原评分函数；可回答题未作答的0分保留，不为满足口头公式删除。置信区间沿用原bootstrap种子。
- 校准样本在看分数前以20261020为种子冻结：各预期行为先抽两条，再从其余题抽十二条。只来自开发/回归，转录原题、要点、系统回答和Claude标签；人工栏留空。已打开给作者，后续整理脚本不覆盖现有样本，避免丢失人工备注。
- 开发/回归的每道题均由Langfuse读回回答、全部步骤、原评分数值和完整逐点/行为/矛盾标签。对应cloud-verification.json与cloud-score-details.json本地保留；测试没有云端副本。
- 核验脚本证明三套均无错误、每ID仅一条系统结果、全部输入与源文件哈希未变，原入口报告汇总行没有被整理脚本改变；仓库内测试输出无测试题干或回答，Git HEAD保持运行前状态，无暂存项。
- 方法限制：前三题与续跑阶段各自重建检索器/加载模型，原题耗时保留两次起始加载；并发沿用默认值。历史回归轮是full-service且由Codex辅助初评，当前为eval FullSystem+Claude，分差不是可归因的A/B结果。测试题由开发agent参与编写，复审建议项仍按原冻结稿保留；金标展示仍受代表来源和每篇截断限制。所有结果均待人工校准，不称最终成绩。
- 未提交Git，未运行第二遍测试或按结果调系统。下一步由作者抽查calibration-sample.md；没有本轮需补跑的系统或评审任务。
