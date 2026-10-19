# 新70道开发题 · 分批待审

口径：**20回归 + 70新开发 + 30封存测试 = 120次题目运行**。旧dev001～020不计入新70；新开发ID为dev021～dev090。只对外报告70 dev与30 test，分开报。

本目录当前只交[首批12题](batch-01/README.md)，dev021～dev032，**尚未运行RAG、基线或评分**。按作者要求每批12题后停下来审题；后续58题尚未制作，50篇覆盖等全量条件不能在当前宣称完成。封存30题不在本目录，开发agent不读取。

作者原始出题Prompt原样保存在[source-prompt.txt](source-prompt.txt)，其中重复粘贴的规则按同一份要求执行；以下台账是其去重后的工作记录。

## 配额台账

| 类别 | 70题目标 | 本批 | 剩余 |
|---|---:|---:|---:|
| fact_single | 24 | 4 | 20 |
| summary | 11 | 2 | 9 |
| reasoning | 14 | 3 | 11 |
| version | 7 | 1 | 6 |
| unanswerable | 14 | 2 | 12 |

细分目标沿用作者Prompt：事实题短问/同义改写/数值配置表格/相邻易混各6；归纳题分散证据6、有序步骤5；推理题链式8、并列3、比较3；版本7中4道题干不直接写版本；边界题库内缺依据5、错误前提4、含糊3、无关1、隐蔽注入1。本批每个事实/归纳/推理子类各一，边界为缺依据与错误前提各一；本批版本题明确云版。

全量至少50篇不同文档、同篇最多2题，api-reference/learn/cloud/self-host均覆盖；每批跟踪文档使用计数。至少35/70题不超过40字符，“自建Dify”等部署前缀最多21/70题；短问子类8～20字符且不带“自建/云端”。这些是约束，不是凑题理由。

## 制作与审题约定

- 只用固定Dify中文语料commit `c80a31868611b673bd77725a6310c685068a585e`，不查新网站或凭产品记忆补答案。先选原文事实，再写问题；不参考系统回答。
- 可答题2～4个要点，每个都必须是问题明确要求的内容；数量/对象/条件写全。不可答题不造事实金标，保存正确边界行为与核查说明。
- 除summary外最多2个独立小问。`expected_route`按1问SINGLE、2问及以上或链式MULTI；题型和首路由不是同一个字段。
- 真实chunk/父块由既有清洗、切分和数据库只读核验得到；不是推测RAG实际会召回哪些块。实际召回须后续另跑并比较。
- `hardness_tag`原Prompt没有枚举，本批使用short_fact、lexical_gap、table_schema、neighbor_confusion、scattered_evidence、ordered_steps、chain_bridge、parallel_evidence、comparison_choice、edition_conflict、absence_check、false_premise；均附理由，不声称难度已由基线验证。
- `guessable_without_docs=false`只是出题者判断：要求产品专有事件名、字段、操作或明确例外；不能证明模型不会靠预训练答对。盲答/naive检验等审题后再做。
- 建议后续用`--withhold-edition`运行。不直接写版本名称的题可通过套餐名、Docker/.env等可见环境线索保持可判定性；若确实没有任何线索，隐藏的edition不能成为唯一正确答案依据，应接受合理澄清/分版本条件回答。最终70题中4道不直接写版本的version题需按此检查；本批版本题明确云版。

原文与摘录按Dify文档[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)注明出处；题干和答案为基于冻结原文的改编。所有当前材料为待Claude及作者审阅的开发草案。
