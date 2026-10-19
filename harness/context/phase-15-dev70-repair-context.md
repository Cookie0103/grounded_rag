# 新70题修订和第二批出题决策

- 2026-10-19作者本次附件覆盖旧题型数量，改按行为分28单跳/28多跳/9拒答与纠正/5模糊。正式100=70开发+30封存；旧20独立回归，最终运行规模120。
- 本次只修首批12并出第二批12，交审后停止，不自主出剩余46，不读/制作封存30，不运行系统或基线。
- 第一批多跳实际1链式+3并列跨篇+2分散，附件子类表“3分散”与6道总数冲突，按实际题目校正；两批共3链式，未来还需7。
- 所有guessable_without_docs为null，由真实无检索基线决定；静态关键词核验不等于证明Naive必然失败。
- cloud/self-host孪生逐字比较留档；同题点等价时，gold_doc_groups记组内OR，多个必要组之间AND；gold_docs只保留代表以兼容现有Question格式。现有加载器不支持此字段，正式评分前必须适配，不能直接报告默认Recall@5。
- 错误前提的最终行为是纠正。现有ROUTES无CORRECT，dev032 expected_route留null并显式requires_corrects_premise，不虚构路由。模糊题允许条件答案；注入题允许拒恶意部分后回答正常部分。
- 复用.clean_mdx、chunk_document、数据库只读导出核对、旧ev/nugget定位函数和Question校验器；新题仅写docs/eval/dev70，不修改backend/eval/data、评分规则、Prompt或运行代码。
- 作者已有四个未提交文件（eval_round.py、dev20/README、metrics-v1、runbook）保留，不纳入本次提交。旧运行快照不改。
- 交付和语义风险以docs/eval/dev70/revision-log.md、validation.json、review-24.md为准；语义查重、链式必要性最终待Claude/作者审核。
