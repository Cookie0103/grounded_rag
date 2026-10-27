# RAG 技术资料阅读笔记（2026-10-16）

覆盖检索与编排的论文、模型卡、pgvector 文档，以及 Dify 文档仓库的实测结构。
每节最后的「怎么用」是给后续 Spec 的结论。

## 1. 语料：langgenius/dify-docs 实测

- 固定 commit：`c80a31868611b673bd77725a6310c685068a585e`（2026-10-16 03:22 UTC 的 main）。
- `zh/` 下共 291 篇 mdx。按 proposal 的范围统计：自部署版 137 篇、云版 45 篇，合计 182 篇，与计划一致。
  - 自部署：`zh/self-host/use-dify/**` 94、`zh/self-host/deploy/**` 14、`zh/learn/**` 16、`zh/api-reference/guides/**` 11、`zh/home.mdx`、`zh/quick-start.mdx`
  - 云版：`zh/cloud/use-dify/knowledge/**` 23、`workspace/**` 12、`monitor/**` 10
- `cloud/use-dify` 和 `self-host/use-dify` 下有 **92 个相对路径完全相同**的页面，它们是版本差异题和检索难负例的来源。
- 文件格式（抽样 knowledge 目录 44 篇）：
  - front matter 只有 `title`（44）、`sidebarTitle`（24）、`description`（5）三个字段。**没有版本字段**，版本只能从路径推出。
  - 每篇正文开头有一行“> 本文档由 AI 自动翻译。如有任何不准确之处，请参考 [英文原版](...)”，需要删掉。
  - 用到的 JSX 组件：`<Frame>` 244 次（图片）、`<Tip>` 35、`<Note>` 32、`<Info>` 27、`<Tab>` 18、`<Warning>` 12、`<Card>` 12、`<Step>` 10、`<Tabs>` 9、`<Badge>` 4、`<Accordion>` 4、`<Steps>` 2。
  - **组件内部内容缩进 4 个空格**。如果直接去掉标签，Markdown 会把这些内容当成代码块，所以去标签后必须减少缩进。
  - 站内链接写作 `/zh/...`，图片用 `![...](...)`。
- 最长的文档是 `zh/self-host/deploy/configuration/environments.mdx`（环境变量大全）：129KB，18 个 H2、47 个 H3、约 1035 行表格。单个 H3 小节就可能有几百行表格，所以**“表格不拆”的规则不可行**，必须按行切分并在每块重复表头。

**怎么用**：清洗规则、文档 ID、版本推断和表格切分写进 M1 Spec。

## 2. Qwen3-Embedding-0.6B

[模型卡](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) · [论文 arXiv 2506.05176](https://arxiv.org/abs/2506.05176)

- 向量 1024 维，支持 MRL（可截断到 32～1024 维），上下文 32K。
- 取最后一个 token 做池化，再做 L2 归一化；**tokenizer 必须左侧填充**（`padding_side="left"`）。
- **查询要加指令，文档不加**。格式为 `Instruct: {任务描述}\nQuery:{查询}`。不加指令，效果下降 1～5%。官方建议指令用英文。
- 需要 transformers ≥ 4.51、sentence-transformers ≥ 2.7。
- C-MTEB 平均 66.33。

**怎么用**：
- `Embedder` 接口必须区分 `embed_queries` 和 `embed_documents`（M0 定接口时就要分开）。
- 查询指令：`Given a question about the Dify platform, retrieve documentation passages that answer it`，放在 config。
- 使用 sentence-transformers：`SentenceTransformer(name, tokenizer_kwargs={"padding_side": "left"}, model_kwargs={"torch_dtype": torch.float16})`，查询用 `encode(..., prompt=指令格式)`，文档直接 `encode`，并设 `normalize_embeddings=True`。
- 不用 flash-attention（Windows 上难装），使用默认的 sdpa。
- 维度保持 1024，pgvector 的 HNSW 索引支持最多 2000 维，够用。

## 3. bge-m3

[模型卡](https://huggingface.co/BAAI/bge-m3)

- 1024 维、上下文 8192，**查询不需要指令**，支持稠密、稀疏、多向量三种模式。

**怎么用**：
- 只用稠密模式做对照，通过 sentence-transformers 加载，接口与 Qwen3 相同（`embed_queries` 不加指令）。
- 两个模型都是 1024 维，所以向量表加一个 `model` 列，同一个表存两份向量，换模型不用改表结构（见 M1 Spec）。

## 4. Qwen3-Reranker-0.6B 与 bge-reranker-v2-m3

[Qwen3-Reranker 模型卡](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) · [bge-reranker-v2-m3 模型卡](https://huggingface.co/BAAI/bge-reranker-v2-m3)

- Qwen3-Reranker 是生成式模型。输入写成 `<Instruct>: {指令}\n<Query>: {问题}\n<Document>: {文档}`，外面套上固定的 system 前缀和 assistant 后缀（含空的 `<think>` 块）。分数取最后一个 token 上 “yes” 和 “no” 两个 logit 做 softmax 后 “yes” 的概率。**提示词模板要逐字照抄模型卡**。
- 公开数据（重排 Qwen3-Embedding 召回的前 100 条）：

| 基准 | Qwen3-Reranker-0.6B | bge-reranker-v2-m3 |
|---|---|---|
| CMTEB-R（中文） | 71.31 | **72.16** |
| MTEB-R | **65.80** | 57.03 |
| MLDR（长文档） | **67.28** | 59.51 |

**怎么用**：
- 中文上 bge 略好，长文档上 Qwen3 更好，正好说明 M2 的对比实验有意义，结论不能预设。
- `Reranker` 接口为 `rerank(query, documents) -> list[float]`，分数统一在 0～1。bge 用 sentence-transformers 的 `CrossEncoder`，加 sigmoid 激活。

## 5. pgvector

[GitHub](https://github.com/pgvector/pgvector)

- HNSW 索引：`CREATE INDEX ... USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)`，括号里是默认值；查询时 `hnsw.ef_search` 默认 40。
- 余弦距离运算符是 `<=>`，相似度 = 1 − 距离。
- **WHERE 过滤是在索引扫描之后才做的**：按版本过滤时，可能返回不足 k 条结果。pgvector 0.8 起可以设 `SET hnsw.iterative_scan = relaxed_order` 继续扫描。
- 索引可以加 `WHERE model = '...'` 做成部分索引，每个嵌入模型一个。

**怎么用**：
- 语料只有几千个块，就算顺序扫描也是毫秒级。HNSW 仍然要建（这是生产常用做法），但检索时要开启 iterative scan，并写一个测试：按版本过滤后仍能返回 k 条。
- 镜像用 `pgvector/pgvector:pg16`。

## 6. RRF（Reciprocal Rank Fusion）

Cormack, Clarke, Büttcher. *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods*. SIGIR 2009.

- 融合分数 = Σ 1 / (k + rank)，rank 从 1 开始，论文取 k = 60。只看排名、不看原始分数，所以不需要把 BM25 和余弦分数归一化到同一尺度。

**怎么用**：M2 中 BM25 和向量各取前 `RETRIEVE_TOP_K`（默认 30），RRF 融合后取前 `RERANK_TOP_K`（默认 20）送去精排，再取前 5。k=60 放在 config。

## 7. BM25 与中文分词

**结论（作者 2026-10-16 决定）**：中文分词用 `jieba3`，BM25 用 `bm25s`。M2 实现，M0 / M1 不装。

### 依据

- BM25 需要的是分词，不是关键词提取；查询和文档必须用同一种切法。
- 库的维护状态（PyPI，2026-10-16 核对）：jieba 0.42.1 → 2020-01；pkuseg → 2020-06；jieba3 1.0.2 → 2024-10；jieba-next 1.0.0rc1 → 2026-04；rjieba 0.2.1 → 2026-04；LTP → 2024-06；HanLP 2.1.5 → 2026-09（深度学习，要 PyTorch 和模型，对 BM25 太重）；`rank_bm25` 0.2.2 → **2022-02**；`bm25s` 0.3.13 → **2026-10-07**。
- **实测**（本机，隔离环境）：同一句话，jieba、rjieba、jieba-next、jieba3 的切分结果完全相同（词典内容相同，新版只是更快）。共同问题：`UPLOAD_FILE_SIZE_LIMIT` 被拆成 5 段；「工作流」被切成「工作 / 流有」。所以**必须在切词前保护变量名和术语**。

### jieba3 要点

- 用法：`cutter = jieba3.jieba3(model="base")`（`small` / `base` / `large`，模型文件 2.7 / 9.9 / 16.6 MB，随包安装，无需下载）；`cutter.cut_text(s)` 精确模式；`cutter.cut_query(s)` 搜索模式（长词同时给出子词：「流水线」→ 流水 / 水线 / 流水线）。
- 依赖只有 pydantic，Python ≥ 3.10。**没有用户词典接口**（没有 `add_word` / `load_userdict`），不要去找。
- 输出里有空白和标点 token，要过滤。

### 切词函数（已在本机跑通，`app/retrieval/tokenizer.py`）

```python
PROTECTED = re.compile(r"([a-z][a-z0-9]*(?:_[a-z0-9]+)+|工作流|知识流水线)")  # 变量名 + 术语表
cutter = jieba3.jieba3(model="base")

def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for i, part in enumerate(PROTECTED.split(text.lower())):
        if i % 2:                      # 奇数位是被保护的变量名 / 术语：整体保留
            tokens.append(part)
        else:                          # 其余文字交给 jieba3，丢掉空白和标点
            tokens += [t for t in cutter.cut_query(part) if re.search(r"\w", t)]
    return tokens
```

- `re.split` 带捕获组，结果里奇数位是匹配到的部分。
- 实测输出：「在知识流水线里怎么修改 UPLOAD_FILE_SIZE_LIMIT，……工作流有什么区别」→ `在 / 知识流水线 / 里 / 怎么 / 修改 / upload_file_size_limit / … / 工作流 / 有 / 什么 / 区别`。
- 术语表先放十几个（从 182 篇文档的标题统计高频词得到：「工作流」「知识流水线」「知识库」「Chatflow」「Agent」等），M2 再定；术语表放 `app/retrieval/terms.py`，不放进 config。
- 已知缺点：被保护的整词（「知识流水线」）搜「流水线」匹配不到。M2 评估时要专门看这一点；若有影响，保护词同时输出整词和 `cut_query` 的子词。

### bm25s 要点

- `r = bm25s.BM25(); r.index(list_of_token_lists)`；`r.retrieve([query_tokens], k=…, corpus=…)` 返回 `(results, scores)`。**传自己切好的词列表**，不用它自带的 tokenizer。已验证可用。
- 索引不入库，启动时从 `chunks` 表在内存里构建。
- `show_progress=False` 关掉进度条（日志干净）。

### M2 对照实验

jieba3 `cut_query` vs `cut_text` vs 字符二元组（中文连续汉字切相邻两字，英文标识符整体保留，零依赖、不需要术语表），用开发集 Recall@5 决定，并记入开发日志。可选：bge-m3 稀疏向量（不是 BM25，要换一套检索实现）。

### 日语（将来，不实现）

SudachiPy 0.7.0（2026-09）+ `sudachidict-core`（2026-10-15），备选 fugashi（2025-10）；字符二元组对日语也能用。

### 多语言嵌入

Qwen3-Embedding、bge-m3 及两个精排模型都是多语言模型，官方支持 100 多种语言，中日文都在内；效果是否相当，要用日文题集实测。嵌入模型自带分词器，与上面的 BM25 分词无关。

## 8. Adaptive-RAG（Jeong et al., NAACL 2024）

[arXiv 2403.14403](https://arxiv.org/abs/2403.14403)

- 按问题复杂度选择三种策略：不检索 / 单步检索 / 多步检索。用 T5-Large（770M）训练一个分类器，标签由“哪种最简单的策略能答对”自动生成。
- 分类器整体准确率只有约 **54%**，但即便如此，效率和效果都优于“一律多步”，与理想分类器之间仍有很大差距。

**怎么用**：
- 我们不训练分类器（数据太少），而是**规则兜底 + LLM 分类**。规则优先处理：注入特征词 → REFUSE；纯寒暄 → DIRECT；问题太短且缺少对象 → CLARIFY。其余交给 LLM 分类。
- 分类不确定时默认走 **SINGLE**：比 MULTI 便宜，又不会像 DIRECT 那样跳过检索。
- 评测时记录路由准确率，只作诊断用；路由错了，最终答案仍可能对。

## 9. Corrective RAG（Yan et al., 2024）

[arXiv 2401.15884](https://arxiv.org/abs/2401.15884)。注意：它也简称 CRAG，与 §1 的 Meta CRAG 基准不是同一个东西。

- 用一个检索评估器给每个“问题-文档”对打分，按阈值触发三种动作：
  - Correct：提炼文档后直接用
  - Incorrect：丢弃检索结果，改用网络搜索
  - Ambiguous：两者结合
- 提炼的做法是先分解再重组：把文档切成几句一条，过滤掉低分条，保留前 5 条，按原顺序拼回去。

**怎么用**：
- “证据够吗”节点借鉴它的三态，但判断用 §3 的充分性提示词，不训练评估器：
  - 充分 → 生成
  - 部分充分 → 保留有用证据，针对缺的部分改写查询再检索
  - 不充分 → 改写后重检索
  - 最多重试 2 次，仍不充分时按 notes-evaluation §3 的拒答策略处理
- 本项目是封闭语料，**没有网络搜索兜底**。
- “分解再重组”式的句子级过滤先不做；等错误归因显示“上下文太长、噪声多”时再考虑（YAGNI）。

## 10. DeepSeek API

[价格页](https://api-docs.deepseek.com/quick_start/pricing)，2026-10-16 查询。

- 当前模型：`deepseek-flash`（V4.1-Flash）和 `deepseek-v4-pro`，上下文 1M，支持 JSON 输出。旧名 `deepseek-v4-flash` 仍可用，会被路由到 V4.1-Flash。
- 价格只有美元，单位为每百万 token。Flash 高峰价：输入命中缓存 $0.006、未命中 $0.3，输出 $1.2；非高峰半价。高峰时段为北京时间工作日 09:00～12:00 和 14:00～18:00（UTC 01:00–04:00、06:00–10:00）。

**怎么用**：
- 默认模型 `deepseek-flash`，通过 OpenAI 兼容接口调用（`base_url=https://api.deepseek.com`）。
- 预算按**高峰价**估算（保守），用 config 里的汇率 `USD_TO_CNY` 换算成人民币，与 ¥10/天 比较。
- 按 Flash 高峰价粗算：一次“2k 输入 + 300 输出”的调用约 $0.001，¥10（约 $1.4）够大约 1400 次。开发集 70 题每题按 5 次调用算（路由、改写、充分性判断、生成、校验），跑一遍约 350 次，一天能跑 3～4 遍。

## 11. 分块策略的依据

**结论**：按文档结构切（标题 → 段落 / 列表 / 代码块 / 表格），不用固定字数窗口，不用语义切分。

- **Adaptive-rag 的做法**（`app/retrieval/chunking.py`）：按 `#`～`###` 标题分节，节内每 500 字切一刀、相邻重叠 60 字（`_window`，按字符位置切，不认句子、表格、代码）；标题只存元数据，嵌入的是 `chunk.content`。本项目不照搬：会把句子、表格行、代码拦腰切断。
- **语义切分**（用嵌入模型逐句比较相似度，骤降处切）：Qu / Bao / Tu，*Is Semantic Chunking Worth the Computational Cost?*（NAACL 2025 Findings，[arXiv 2410.13070](https://arxiv.org/html/2410.13070v1)）在文档检索、证据检索、答案生成三个任务上比较了语义切分与固定大小切分，结论是额外算力没有带来稳定提升，常常不值得。本项目不做。
- **文档本身有清晰结构**：Dify 文档每个 H2 / H3 小节就是作者分好的一个话题，按结构切等于已经按语义切，不需要额外算向量。
- **表格**：按字数分组（目标 300、上限 500），每组重复表头，所以每组几行不固定（长行 1 行，短行 3～5 行）。**M2 对照**：「一行一块」vs「按字数分组」，用 Recall@5 决定。
- **1024 是向量维度，不是字符数**；字符上限是子块 500、父块 4000、代码块 1500。

### Contextual Retrieval（Anthropic，备选）

[Anthropic: Introducing Contextual Retrieval](https://anthropic.com/news/contextual-retrieval)：给每个块前面补一两句「这块在整篇文档里讲什么」，再嵌入、再建 BM25 索引。Anthropic 内部基准，前 20 条里检索失败的比例：只补嵌入 −35%（5.7% → 3.7%），再补 BM25 −49%（→ 2.9%），再加精排 −67%。语料不同差别很大，不能直接套用。

- **已纳入的简化版**：嵌入和 BM25 共用 `search_text(heading_path, text)`（标题路径 + 换行 + 子块正文），不调用大模型。
- **备选，先不做**：用 DeepSeek 为每块生成一两句说明。触发条件：M3 之后的错误归因显示「块脱离上下文读不懂」是主要问题。成本：几千个块、一次性，但会让入库流程变复杂，所以不预先做。

