# 阶段21 实验决定与复现入口

- 2026-10-22：作者明确要求实际做消融，取代前轮“不再跑系统”限制；仅在既有开发70题上运行，不读取封存测试或修改题集/评分/Prompt。
- 原有五档不能独立估计精排贡献，添加实验档`hybrid-no-rerank`，直接以现有NaiveRagSystem的mode/rerank参数实例化，不修改业务。
- 检索单独比较向量、BM25、混合不精排、混合精排；只纳入有金标的可回答题，保留AND/OR金标组定义。答案比较六档，前三种RAG提示词完全相同，routed/full仍为多机制组合。
- 同题配对差值与95%bootstrap区间沿用原bootstrap_interval（1000次、种子0）；不根据无配对的两条区间是否重叠下结论。区间仅覆盖题目抽样，不包括judge误差、模型重复生成波动或多重比较校正。
- 所有新答案重新生成，不用历史full回答拼接消融。模型预热后开始计时；六系统顺序逐题循环轮换，四题并行，与旧dev70并发数相同；P95包括资源竞争。
- 全链路使用评测FullSystem/ChatPipeline，不含ChatService的整答/检索缓存、多轮记忆和后处理。edition从开发题发送，各档一致；无检索基线沿用现有提示词。
- 统一Claude CLI默认模型及原judge_v2。CLI为2.1.306，未覆盖模型；无法锁定远端Claude/DeepSeek权重版本。此次各档新答案尚无额外人类校准，不能把此前作者20条完整系统的复核预标校准视为本轮全档校准。
- 公共来源审核：从GitHub固定commit读取文件树，182篇blob哈希与本地一致；同原清洗/切块函数重建，数据库文档哈希与全部子块、父块逐字一致。报告见本阶段`public-source-audit.json`归档；不发送内部文档或密钥作为实验输入。
- 预算沿用现有providers/BudgetLedger；四题并发时预留0.7元不再启动新题，provider原10元限制仍有效。不改预算、原账本或token计费。

复现脚本在`phase-21-tools/`：`.py.md`是原始Python源，原样复制到`.cache/ablation-20261022/`并去掉末尾`.md`。`run.py`依次支持retrieval、generate、judge、audit，`report.py`只读汇总，`audit.py`核验真实开关、分母、配对及费用。所有恢复先验证原manifest的代码/题集/提示词/脚本哈希；同目录只用于本轮续跑，新实验用全新目录。原始答案、逐轮trace、评审和token元数据留`.cache/ablation-20261022/`，不覆盖任何旧轮次。

2026-10-22交接：生成已全部完成。Claude额度恢复后，在backend依次执行`python ../.cache/ablation-20261022/run.py judge`、`python ../.cache/ablation-20261022/report.py`、`python ../.cache/ablation-20261022/audit.py`；仅补剩余标签，不执行generate或retrieval，不清理原缓存。CLI显示周额度2026-10-25东京12:00恢复，未安排自动任务。断点成功标签169条，待评251条，原六条并发在途失败另存。若代码/Prompt/题集哈希变化，应回到固定源码快照后恢复，不能放宽冻结检查混用结果。CLI默认远端模型未锁定，恢复时记录版本/模型变化，不能无条件保证远端裁判完全相同。

状态和数值以build-log及评测报告为准，本文件只记录决定。
