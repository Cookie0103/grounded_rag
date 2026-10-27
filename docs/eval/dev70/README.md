# 新70道开发题台账

当前dev021～090共70题，已按2026-10-20 Claude报告及两轮独立复核修订，等待作者最终审定与冻结。旧dev001～020独立回归；测试30题在仓库外新编，见phase-17交接，本目录不含测试内容。

入口：[全70审阅稿](review-70.md)、[题目](questions.jsonl)、[逐点证据](evidence.json)、[本轮修订](repair-2026-10-20.json)、[修订日志](revision-log.md)、[当前静态核验](validation.json)。

行为配额仍为28单跳、28多跳、9拒答纠正、5模糊；两半新增各23题的子类配额保持。四批题目与证据副本均以当前总表同步。

| 批次 | 题号 | 审阅稿 |
|---|---|---|
| batch-01 | dev021～032 | [当前稿](batch-01/review.md) |
| batch-02 | dev033～044 | [当前稿](batch-02/review.md) |
| batch-03 | dev045～067 | [当前稿](batch-03/review.md) |
| batch-04 | dev068～090 | [当前稿](batch-04/review.md) |

冻结语料：`langgenius/dify-docs@c80a31868611b673bd77725a6310c685068a585e`，182篇，CC BY 4.0。来源重建继续使用生产clean_mdx/chunk_document；本轮不查询数据库，不调用RAG、无检索基线或付费模型。

新增46题每篇金标（含等价来源）最多用于一次；全70每篇最多两次。**H4例外只限配置参考页重复专题页已有变量、默认值或该配置取值说明的OR来源，主金标仍计数。** 本轮白名单为dev034、048、057、070、083中的environments；048/070已换成原页独有数值，不再实际使用该豁免。057是NOTION_INTEGRATION_TYPE=internal的配置值复述，同类规则与原因见phase-17 context。不能将其他专题页或不相关事实自报为豁免。

OR以每个必答点的`all_of/any_of`为准，侧表`nugget_gold_doc_groups`提供对应文档组；题级`gold_doc_groups`只表示整题的必要文档约束。dev083仍需专题页提供401症状和不同可注册域名边界，environments只能替代其实际覆盖的变量说明，不能单篇满足整题。`all_equivalent_gold_docs`保留部分等价来源以便复用审计。

**历史记录须按版本阅读**：retrieval-selftest.jsonl、retrieval-diagnostics.md、runtime-verification.json和semantic-review.json保存2026-10-19原运行与原审题；本轮未覆盖这些档案。当前题干/金标已经改变，原召回比例不是修订版结果，正式评测前需另存新检索记录。blueprint及generation-notes同为初版历史。

正式Question加载器仍忽略OR字段；本轮只修题和证据，未修改评分规则或评审Prompt。所有guessable_without_docs仍为null，待无检索基线。旧题局限及语义审定边界见validation与phase-17自查。
