# 阶段 32：检索

状态：未开始（草案；执行模型开工前可细化，细化后自行标「已批准」）

> 这是计划和记录，不是完成证据；进度以 [build-log](../build-log.md) 为准。设计依据见 [PLANS.md](../../PLANS.md) §4.3。

## 需求

### 目标

1. 关键词一路从内存 bm25s + jieba 换成 Elasticsearch + kuromoji。
2. 元数据硬过滤：产品线、规程类型、查询日期（生效区间）、语料档，向量和 ES 两路用同一个过滤对象。
3. 用数据决定精排是否默认开启，并拿到 S、L 两档的初步命中率。

### 非目标

- 查询改写、多查询（如需要，在阶段 34 里按延迟预算决定）。
- 正式评测（阶段 36）；本阶段只用一份小的冒烟集。

### 接口

`POST /retrieve` 的 `edition` 参数换成：

```json
{"query": "繰上返済の手数料はいくらですか", "top_k": 5, "rerank": true,
 "filter": {"product_line": "home_loan", "as_of": "2026-11-18", "corpus_tier": "S"}}
```

`as_of` 不传默认当天；`corpus_tier` 不传默认 `L`（全量）。响应结构不变，候选里多返回元数据。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | ES 一路返回 (chunk_id, 分数)；`policy_id` 能精确命中 | 单元测试 + 集成测试 |
| AC2 | 同一个 `MetaFilter` 生成 SQL 条件和 ES filter，两路过滤结果的块集合一致 | 集成测试：随机 20 组过滤条件比对 |
| AC3 | 失效版本在任何检索模式下都不进入候选 | 版本组的集成测试 |
| AC4 | 冒烟集（执行模型自己写约 30 题，覆盖精确编号、超短问句、口语问法、版本陷阱）上，报四种模式（仅向量、仅 ES、混合、混合加精排）在 S、L 两档的 Top5 命中率、MRR、耗时 | `poe compare-retrieval` 报告 |
| AC5 | 精排默认开或关的决定有数据支撑并写进记录 | 记录 |
| AC6 | ES 不可用时退化为仅向量并标记 `degraded` | 单元测试 |
| AC7 | `poe check`、`poe test-int` 通过；`bm25s`、`jieba3` 依赖已移除 | 命令输出 |

## 任务

- [ ] T1 `retrieval/keyword.py`：ES 客户端封装，实现与旧 `Bm25Index.search` 等价的接口；查询字段含块文本、标题路径，`policy_id` 走 keyword 精确匹配并加权。
- [ ] T2 `MetaFilter`：一个数据类，两个方法分别产出 SQL 条件和 ES filter；`retriever.py`、`factory.py`、存储层改用它，替换 `editions`。
- [ ] T3 `/retrieve` 接口和测试同步；删除 `edition` 相关的配置、列和代码。
- [ ] T4 Qwen3 嵌入的查询指令改成日文银行规程场景的说法（`QWEN3_QUERY_INSTRUCTION`），并在冒烟集上对比改前改后。
- [ ] T5 冒烟集与 `compare-retrieval`：四种模式 × 两档语料；输出耗时分解。
- [ ] T6 删除 `bm25.py`、`terms.py` 及其测试和依赖。

## 需要作者做的

无。

## 记录

（执行时填写：kuromoji 的分词模式与同义词是否需要调整、精排开关的决定和数据）

## 阻塞

（无）
