# M2：检索

状态：完成（2026-10-16）

## 需求

### 目标

1. 混合检索：向量（pgvector）和 BM25 并行，RRF 融合，再精排，取前 5，并带出所属父块。
2. 对外提供 `POST /retrieve`，返回每个候选在各环节的名次和分数，方便调试和评测。
3. 精排模型和嵌入模型都可以按配置切换（Qwen3 / bge / fake），为模型对比做好准备。

### 非目标

- 生成答案、路由、改写：M5。
- 模型对比的**最终结论**：需要 M3 的评测题；M2 只提供对比脚本，用一份小的冒烟集验证流程，结论标注为暂定。
- 多语言分词：先做中文。

### 接口

`POST /retrieve`

```json
请求  {"query": "怎么修改上传文件的大小限制", "top_k": 5, "edition": "self_host", "rerank": true}
响应  {
  "trace_id": "...", "query": "...", "edition": "self_host",
  "candidates": [{
    "rank": 1, "chunk_id": "...", "document_id": "...", "parent_id": "...",
    "heading_path": "...", "text": "...", "edition": "self_host",
    "vector_rank": 3, "vector_distance": 0.21, "bm25_rank": 1, "bm25_score": 8.4,
    "rrf_score": 0.032, "rerank_score": 0.93
  }],
  "parents": [{"id": "...", "document_id": "...", "heading_path": "...", "text": "..."}],
  "timings_ms": {"embed": 12, "vector": 8, "bm25": 3, "fuse": 0, "rerank": 55, "parents": 4, "total": 85}
}
```

- `edition` 可选 `self_host` / `cloud`：查该版本的文档加上「通用」文档；不传就查全部。
- `top_k` 1～20，默认 5；`query` 1～500 字。不满足就返回统一格式的 422。
- `rerank=false` 时跳过精排（降级路径），候选按 RRF 排序。

### 配置

| 位置 | 名称 | 默认值 |
|---|---|---|
| Settings | `RERANKER_MODEL` | `qwen3`（可选 `bge`、`fake`、`none`） |
| config.py | `RETRIEVE_TOP_K` / `FUSION_TOP_K` / `FINAL_TOP_K` / `RRF_K` | 30 / 20 / 5 / 60 |

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | 分词保护变量名和术语，bm25s 能按词检索 | 单元测试；`UPLOAD_FILE_SIZE_LIMIT` 查询第 1 名是 `environments` 里的知识库配置 |
| AC2 | RRF、BM25、版本过滤、父块扩展行为正确 | 单元测试 + 集成测试（真实库 + 假嵌入） |
| AC3 | `/retrieve` 返回约定的结构，参数不合法时是统一的 422 | API 单元测试 |
| AC4 | 真实模型端到端：Qwen3 嵌入 + Qwen3 精排，182 篇语料 | `poe retrieve-demo` 输出 3 个检查问题的结果；对比 M1 报告里纯向量的排序 |
| AC5 | 对比脚本能在冒烟集上算出 Recall@5 | `poe compare-retrieval`，结果写入 `.cache/reports/` |
| AC6 | `poe check`、`poe test-int` 通过，CI 全绿 | |

## 方案

- `app/retrieval/`：`tokenizer.py`（jieba3 + 保护变量名和术语表）、`bm25.py`（bm25s，启动时从 chunks 表在内存里建）、`fusion.py`（RRF）、`retriever.py`（编排）、`factory.py`（从引擎和配置组装）。
- 检索器的向量检索和父块读取通过传入的函数完成，单元测试里用内存实现，不连库。
- 精排：`app/providers/local_reranker.py`，`Qwen3-Reranker-0.6B`（按模型卡的 yes/no 提示词，取最后一个 token 上 yes 的概率）和 `bge-reranker-v2-m3`（CrossEncoder）。
- 版本过滤：`self_host` → {self_host, common}；`cloud` → {cloud, common}。向量那一路用 SQL `IN` 过滤（带迭代扫描），BM25 那一路用掩码。
- 层次：`api → retrieval | ingest → providers | db → core`。

## 任务

- [x] T1 分词、BM25、RRF 及单元测试 → AC1、AC2
- [x] T2 检索器、仓储扩展（加载块、读父块、按版本集合过滤）及测试 → AC2
- [x] T3 精排模型（Qwen3 / bge）与工厂 → AC4
- [x] T4 `/retrieve` 接口与组装 → AC3
- [x] T5 真实模型端到端、对比脚本、冒烟集 → AC4、AC5
- [x] T6 收尾：检查、日志、记录 → AC6

## 阻塞

## 记录

**验收结果（2026-10-16）**

| 编号 | 结果 |
|---|---|
| AC1 | 分词保护变量名和术语；单元测试通过。`UPLOAD_FILE_SIZE_LIMIT` 作为一个词进索引 |
| AC2 | RRF（数值例子和平局）、BM25（掩码、空索引、可换分词）、检索器（版本过滤、父块去重、各环节耗时、三种模式）的单元测试；真实库 + 假嵌入的集成测试 4 个 |
| AC3 | `/retrieve` 的 API 测试：结构、版本包含「通用」文档、`query` 去空白、7 种非法请求都是统一的 422 |
| AC4 | `poe retrieve-demo`：真实 Qwen3 嵌入 + Qwen3 精排跑通；第一次请求要 40 秒（加载模型），之后每次约 250 毫秒（精排 20 个候选约 180 毫秒） |
| AC5 | `poe compare-retrieval`：在 28 题的冒烟集上算 9 种方案的 Recall@5，见下 |
| AC6 | `poe check` 205 个单元测试、覆盖率 90%；`poe test-int` 23 个；CI 见日志 |

**对比结果（28 题冒烟集，只用来验证流程，不能下结论）**

| 方案 | Recall@5 | MRR | 用词接近 | 用词不同 | 平均耗时 ms |
|---|---|---|---|---|---|
| 只用向量（qwen3 嵌入） | 0.964 | 0.857 | 1.000 | 0.889 | 287 |
| 只用 BM25（jieba3） | 0.821 | 0.588 | 0.947 | 0.556 | 3 |
| 只用 BM25（字符二元组） | 0.714 | 0.482 | 0.789 | 0.556 | 2 |
| 混合（jieba3），不精排 | 0.893 | 0.768 | 0.947 | 0.778 | 76 |
| 混合（字符二元组），不精排 | 0.857 | 0.756 | 0.947 | 0.667 | 77 |
| 混合（jieba3）+ qwen3 精排 | 0.929 | 0.857 | 1.000 | 0.778 | 360 |
| 混合（jieba3）+ bge 精排 | 0.964 | 0.804 | 1.000 | 0.889 | 1538 |
| 只用向量（bge-m3 嵌入） | 0.964 | 0.857 | 1.000 | 0.889 | 64 |
| 混合（bge-m3 嵌入，jieba3）+ qwen3 精排 | 0.964 | 0.864 | 1.000 | 0.889 | 253 |

初步的观察（样本太小，差一题就是 3.6 个百分点，**正式结论等 M3 的开发集**）：
- jieba3 的 BM25 比字符二元组好（0.821 vs 0.714），所以 BM25 先用 jieba3。
- 精排能把「混合」从 0.893 提到 0.929～0.964；bge 精排比 Qwen3 精排慢 4 倍以上（1.5 秒 vs 0.36 秒）。
- 冒烟集里的题大多是自然语言，向量检索已经很好，BM25 不加分；BM25 的价值在带变量名、报错信息的题，冒烟集里这类题很少。
- Qwen3 嵌入和 bge-m3 嵌入在这个集上没有区别。
- 暂定默认值：Qwen3 嵌入 + jieba3 BM25 + Qwen3 精排（`RERANKER_MODEL=qwen3`），换模型只需改配置。

**偏离 Spec 的地方**
- **消融模式**：`retrieve` 多了 `mode`（hybrid / vector / bm25）和 `with_reranker`，对比脚本和 M4 的基线要用。
- **停用词**：分词加了一份单字虚词表（的、了、和…）。没有它，「完全无关的内容」会匹配上任何带「的」的文档。
- **第二个嵌入模型**：加了 `add_missing_embeddings` 和 `poe ingest --model bge-m3 --add-embeddings`，迁移 0003 给 bge-m3 建 HNSW 部分索引；这样 M1 里「拒绝在已有库上用另一个模型入库」的保护不挡对比实验。
- **ruff**：`max-args` 从 5 提到 7（检索入口需要的参数多）。
- **冒烟集**：`backend/eval/smoke_retrieval.jsonl` 28 题是我按文档标题写的，**只用来验证评测流程**，不是正式评测集；正式的 100 题由作者用 Gemini 出，放 `backend/eval/data/`。
- sentence-transformers 6 把 `tokenizer_kwargs` 改名 `processor_kwargs`，已跟进。

**自审**：精排分数几乎都是 0.99+（yes 的概率饱和），只有排序有意义，不要把分数当置信度用；`/retrieve` 的检索器是第一次请求时才建的（读库建索引、加载模型要约 40 秒），M7 做服务时要改成启动时预热；BM25 索引在内存里，库里的语料更新后要重启服务才会生效。
