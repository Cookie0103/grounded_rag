# M1：数据管线

状态：待批准（作者看过后改为「已批准」；M0 完成前可以先审）

## 需求

### 目标

1. 按固定 commit 下载 182 篇 Dify 中文文档，清洗成干净的 Markdown。
2. 父子切块，带标题路径、版本、类别等元数据，用 Qwen3-Embedding 生成向量，写入 PostgreSQL。
3. 重复运行时只处理有变化的文档，不产生重复数据；每次运行输出一份数据报告，供作者检查。

### 非目标

- BM25、混合检索、精排、`/retrieve` 接口：M2 做。
- bge-m3 的向量：M2 做模型对比时再生成；表结构现在就支持多个模型。
- 句子级过滤（Corrective RAG 的“分解再重组”）：等错误归因证明有需要再做。
- 文档里的图片：多模态是非目标，直接丢弃。

### 接口与数据

**语料清单（`app/ingest/corpus.py`）**

```python
CORPUS_REPO = "langgenius/dify-docs"
CORPUS_COMMIT = "c80a31868611b673bd77725a6310c685068a585e"
INCLUDE_PREFIXES = (
    "zh/self-host/use-dify/", "zh/self-host/deploy/", "zh/learn/", "zh/api-reference/guides/",
    "zh/cloud/use-dify/knowledge/", "zh/cloud/use-dify/workspace/", "zh/cloud/use-dify/monitor/",
)
INCLUDE_FILES = ("zh/home.mdx", "zh/quick-start.mdx")
EXPECTED_DOCUMENT_COUNT = 182
```

只收 `.mdx` 文件。Python 3.12 的 `PurePath.match` 不支持 `**`，所以用前缀判断，不用 glob。

**文档 ID、版本和类别**（纯函数，全部写单元测试）：

| 原始路径 | document_id | edition | category |
|---|---|---|---|
| `zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/readme.mdx` | `self-host/use-dify/knowledge/create-knowledge/import-text-data/readme` | `self_host` | `knowledge` |
| `zh/cloud/use-dify/monitor/x.mdx` | `cloud/use-dify/monitor/x` | `cloud` | `monitor` |
| `zh/self-host/deploy/configuration/environments.mdx` | `self-host/deploy/configuration/environments` | `self_host` | `deploy` |
| `zh/learn/key-concepts.mdx` | `learn/key-concepts` | `common` | `learn` |
| `zh/api-reference/guides/x.mdx` | `api-reference/guides/x` | `common` | `api-reference` |
| `zh/home.mdx` | `home` | `common` | `home` |

- document_id：去掉 `zh/` 前缀和 `.mdx` 后缀，可读且跨机器稳定，评测集的 `gold_docs` 也用它。
- edition：路径以 `cloud/` 开头为 `cloud`，以 `self-host/` 开头为 `self_host`，其余为 `common`。
- category：路径中有 `use-dify/<x>` 时取 `<x>`；以 `self-host/deploy` 开头为 `deploy`；其余取第一段。

**表（迁移 `0002_corpus_tables`）**

```text
documents
  id              text primary key        -- document_id
  path            text not null           -- zh/...mdx
  edition         text not null           -- check in ('self_host','cloud','common')
  category        text not null
  title           text not null
  description     text null
  content_hash    text not null           -- sha256(原始文件字节 + INGEST_VERSION)
  corpus_commit   text not null
  created_at      timestamptz not null default now()
  updated_at      timestamptz not null default now()

parent_chunks
  id              text primary key        -- f"{document_id}#p{ordinal}"
  document_id     text not null references documents(id) on delete cascade
  ordinal         int  not null
  heading_path    text not null           -- "标题 > H2 > H3"
  text            text not null
  created_at      timestamptz not null default now()

chunks
  id              text primary key        -- f"{document_id}#c{ordinal}"
  document_id     text not null references documents(id) on delete cascade
  parent_id       text not null references parent_chunks(id) on delete cascade
  ordinal         int  not null
  heading_path    text not null
  text            text not null
  created_at      timestamptz not null default now()
  index (document_id)

chunk_embeddings
  id              bigint generated always as identity primary key
  chunk_id        text not null references chunks(id) on delete cascade
  model           text not null           -- 'qwen3-embedding-0.6b' / 'bge-m3'
  embedding       vector(1024) not null
  created_at      timestamptz not null default now()
  unique (chunk_id, model)
  hnsw 部分索引：USING hnsw (embedding vector_cosine_ops) WHERE model = 'qwen3-embedding-0.6b'
```

- 一个文档变化时，整篇删除再重建（靠外键级联删除），所以 chunk ID 用序号就能保持稳定。
- 两个嵌入模型都是 1024 维，存在同一张表里，用 `model` 列区分；bge-m3 的部分索引在 M2 加。
- 表用 SQLAlchemy Core 定义在 `app/db/tables.py`，向量类型用 `pgvector.sqlalchemy.Vector(1024)`。

**新增配置**

| 位置 | 名称 | 默认值 |
|---|---|---|
| Settings（`.env`） | `EMBEDDING_MODEL` | `qwen3`（可选 `qwen3`、`bge-m3`、`fake`） |
| Settings | `EMBED_DEVICE` | `cuda` |
| Settings | `EMBED_BATCH_SIZE` | `32` |
| config.py 常量 | `INGEST_VERSION` | `"1"`（改了清洗或切块逻辑就加 1，触发全量重建） |
| config.py 常量 | `CHILD_TARGET_CHARS` / `CHILD_MAX_CHARS` | `300` / `500` |
| config.py 常量 | `PARENT_MAX_CHARS` | `4000` |
| config.py 常量 | `CODE_BLOCK_MAX_CHARS` | `1500` |
| config.py 常量 | `QWEN3_QUERY_INSTRUCTION` | `"Given a question about the Dify platform, retrieve documentation passages that answer it"` |
| config.py 常量 | `MODEL_CACHE_DIR` | `CACHE_DIR / "models"` |

**命令（poe 任务）**

- `poe fetch-docs` → `python -m scripts.fetch_docs`
- `poe ingest` → `python -m scripts.ingest`（参数 `--model qwen3|fake`，默认读配置）
- `poe test-gpu` → `pytest -m gpu`（只在本机跑）

**新增依赖**：`pyyaml`（解析 front matter）、开发依赖 `types-PyYAML`；可选依赖组 `gpu`：`torch`、`transformers`、`sentence-transformers`。

### 验收标准

| 编号 | 标准 | 验证方式 |
|---|---|---|
| AC1 | 下载结果正好是 182 篇；再次运行不重复下载 | `poe fetch-docs` 两次，第二次输出“已存在，跳过” |
| AC2 | 清洗后没有残留的 JSX 标签，没有 AI 翻译声明 | 清洗的 golden 测试；数据报告中“残留标签数 = 0” |
| AC3 | 切块规则正确：标题路径、表格按行切并重复表头、代码块不拆、子块长度符合上限 | 切块单元测试；数据报告中的子块长度分布 |
| AC4 | 182 篇入库；第二次运行时变化数为 0，块数不变 | 先 `poe ingest`，再 `poe ingest` |
| AC5 | 增量正确：改一篇、删一篇，只有这两篇受影响 | 集成测试（用假嵌入，在测试库上跑） |
| AC6 | GPU 嵌入可用 | `poe test-gpu`：能加载 Qwen3，向量是 1024 维且已归一化；`torch.cuda.get_device_capability()` 为 `(12, 0)` |
| AC7 | 数据报告生成，作者检查通过 | `.cache/reports/ingest-*.md`；关键数字摘到本 Spec 的「记录」 |
| AC8 | `poe check`、`poe test-int` 通过，覆盖率不降 | 命令输出 |

### 待确认

- 文档中的站内链接现在只保留文字、丢掉 URL。如果以后要“答案里给出原文链接”，可以从 `documents.path` 拼出来，不需要保存每个链接。作者同意就按此执行。

## 方案

### 模块

```text
backend/
├── app/
│   ├── core/text.py           # search_text(heading_path, text)：嵌入和 BM25 共用的检索文本
│   ├── ingest/
│   │   ├── corpus.py          # 清单、document_id、edition、category
│   │   ├── cleaner.py         # mdx → 干净的 Markdown
│   │   ├── chunker.py         # 分节 → 父块 → 子块
│   │   └── pipeline.py        # 哈希比较、调用嵌入、写库、统计
│   ├── providers/
│   │   ├── local_embedder.py  # SentenceTransformerEmbedder（Qwen3 / bge-m3）
│   │   └── factory.py         # get_embedder(name, settings)
│   └── db/
│       ├── tables.py          # 4 张表
│       └── corpus.py          # 文档与块的读写、最近邻查询
├── migrations/versions/0002_corpus_tables.py
├── scripts/
│   ├── __init__.py
│   ├── fetch_docs.py
│   └── ingest.py              # 调用 pipeline，生成数据报告
└── tests/
    ├── fixtures/dify/         # 从语料中复制的 4～5 篇真实文档及期望输出（附 CC BY 4.0 来源说明）
    ├── unit/ingest/test_corpus.py  test_cleaner.py  test_chunker.py
    ├── unit/core/test_text.py
    ├── integration/test_ingest_pipeline.py
    └── gpu/test_local_embedder.py   # @pytest.mark.gpu
```

`app.ingest` 加进 import-linter 的 layers，位置在 `app.providers | app.db` 之上、`app.api` 之下。

### 下载（`scripts/fetch_docs.py`）

1. 用标准库 `urllib.request`（超时 60 秒）下载 `https://codeload.github.com/langgenius/dify-docs/tar.gz/{CORPUS_COMMIT}` 到 `.cache/downloads/`。不用 httpx：它只能在 providers 里用，而且标准库就够了。
2. 用 `tarfile` 解压，加 `filter="data"` 防止路径穿越。只解压清单里的文件，去掉压缩包的顶层目录，写入 `data/raw/dify-docs/{commit}/zh/...`。
3. 数量不等于 182 时报错，并列出多出或缺少的文件。目标目录已存在且数量正确时跳过。

### 清洗（`app/ingest/cleaner.py`）

输出 `CleanDocument(title, description, markdown, unknown_components: list[str])`。规则如下，每条至少一个测试：

1. **front matter**：开头两条 `---` 之间的内容用 `yaml.safe_load` 解析。`title` 必填，缺失就报错；`description` 可选。
2. **删除翻译声明**：以 `> 本文档由 AI 自动翻译` 开头的行。
3. **代码块原样保留**：fenced code（```）内部的内容不做任何替换。
4. **JSX 组件**（解析成嵌套结构再输出；**组件内部内容要减少缩进**，否则会变成 Markdown 代码块）：

| 组件 | 处理 |
|---|---|
| `Note` / `Tip` / `Info` / `Warning` | 开头输出一行 `**注意：**` / `**提示：**` / `**说明：**` / `**警告：**`，后接内容 |
| `Frame` | 整个删除（内容是图片）；有 `caption` 属性时保留说明文字 |
| `Tabs`、`Steps`、`CardGroup`、`AccordionGroup` | 删除标签，保留内容 |
| `Tab title="X"`、`Accordion title="X"`、`Card title="X"` | 输出一行 `**X**`，后接内容 |
| `Step title="X"` | 输出一行 `**步骤 n：X**`，n 在所属的 `Steps` 内从 1 开始计数 |
| `Badge` 等行内组件 | 只保留内部文字 |
| 其他未知组件 | 删除标签，保留内容，组件名记入 `unknown_components` |

5. 图片 `![...](...)` 删除；链接 `[文字](地址)` 只保留文字；删除 HTML 注释；`<br>` 和 `<br/>` 换成换行。
6. 连续 3 个及以上空行压缩为 1 个空行。

**测试方法**：从语料里复制 4～5 篇覆盖上述组件的真实文档到 `tests/fixtures/dify/`，至少包括：

- `import-text-data/readme.mdx`：列表里嵌套 Tip
- 一篇含 `Tabs`
- 一篇含 `Steps`
- `environments.mdx` 的前 200 行：大表格

为每篇写期望输出 `*.expected.md`，由实现者人工逐行核对后提交，测试比对全文。另外写一个参数化测试：遍历全部 182 篇（`data/raw` 存在时才跑，否则 skip），确认输出中没有 `<[A-Z]` 开头的标签。

### 切块（`app/ingest/chunker.py`）

1. **解析块**：把 Markdown 解析成顺序排列的块：标题（级别、文字）、段落、列表（连续的列表行，包括嵌套）、代码块、表格（表头 + 分隔行 + 数据行）、引用。
2. **分节**：按 H2、H3 分节。`heading_path = " > ".join([title, h2, h3])`。第一个 H2 之前的内容归入路径 `[title]`。H4 及更深的标题当作普通段落，保留在所属小节里。只有标题、没有内容的小节不单独成块。
3. **父块**：每个小节是一个父块。超过 `PARENT_MAX_CHARS` 时，在块的边界处切成多个父块；表格按行切，每个父块都重复表头。
4. **子块**：在父块内部，按顺序把块装进子块，接近 `CHILD_TARGET_CHARS` 就开始新的子块，不超过 `CHILD_MAX_CHARS`。单个块太长时：
   - 段落：在句号、问号、叹号、分号或换行处切开
   - 列表：按列表项切
   - 表格：按若干行一组切，每组重复表头
   - 代码块：不超过 `CODE_BLOCK_MAX_CHARS` 时整块保留（允许超过子块上限）；再长就按行切，每段都补上代码围栏
5. **检索文本**：`search_text(heading_path, text) = f"{heading_path}\n{text}"`，用于嵌入（M2 的 BM25 也用它）。数据库里只存 `heading_path` 和 `text`，不存拼接结果。

为什么这样设计：标题路径能给子块补充上下文（比如“环境变量 > 文件存储 > S3”）；子块小，检索更精准；父块完整，生成时信息全。超长表格是环境变量大全（129KB、约 1035 行表格）里的真实情况，见 [RAG 笔记 §1](../implementation-log/2026-10-16/notes-rag.md)。

### 嵌入（`app/providers/local_embedder.py`）

```python
class SentenceTransformerEmbedder:
    def __init__(self, name: str, model_id: str, *, query_instruction: str | None,
                 device: str, batch_size: int, cache_dir: Path) -> None: ...
```

- 第一次调用时才加载模型（延迟导入 `sentence_transformers` 和 `torch`），这样没装 gpu 依赖组的环境（包括 CI）也能导入这个模块。
- 加载参数：`SentenceTransformer(model_id, device=device, cache_folder=str(cache_dir), tokenizer_kwargs={"padding_side": "left"}, model_kwargs={"torch_dtype": torch.float16})`。
- `embed_documents`：`model.encode(texts, batch_size=..., normalize_embeddings=True)`，在 `asyncio.to_thread` 里执行。
- `embed_queries`：Qwen3 传 `prompt=f"Instruct: {query_instruction}\nQuery:"`；bge-m3 的 `query_instruction=None`，不加提示。
- `factory.get_embedder("qwen3")` 对应 `Qwen/Qwen3-Embedding-0.6B`，数据库中 model 名为 `qwen3-embedding-0.6b`；`"bge-m3"` 对应 `BAAI/bge-m3`，model 名为 `bge-m3`；`"fake"` 对应 `FakeEmbedder`，model 名为 `fake`。
- 这个文件不计入单元测试覆盖率（`coverage.run.omit` 加上 `app/providers/local_*.py`），由 `tests/gpu/` 覆盖。

### GPU 依赖安装

```toml
[project.optional-dependencies]
gpu = ["torch", "transformers>=4.51", "sentence-transformers>=2.7"]

[tool.uv.sources]
torch = [{ index = "pytorch-cuda" }]

[[tool.uv.index]]
name = "pytorch-cuda"
url = "https://download.pytorch.org/whl/cu128"   # 先查最新 torch 提供哪些 CUDA 版本，选 cu128 或更高
explicit = true

[[tool.mypy.overrides]]
module = ["sentence_transformers.*", "torch.*", "transformers.*", "pgvector.*"]
ignore_missing_imports = true
```

- 本机安装：`uv sync --extra gpu`。CI 只跑 `uv sync --locked`，不装 GPU 依赖。
- pytest 加 `gpu` 标记（`markers` 里登记），并把 `poe test` 改成 `pytest -m 'not integration and not gpu' ...`，否则 CI 会去跑 GPU 测试。
- RTX 5070 Ti 是 sm_120，需要 CUDA 12.8 及以上的 torch 构建；本机驱动 610.88 支持 CUDA 13。
- 验证命令：`uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_capability())"`，输出写进日志。

### 入库（`app/ingest/pipeline.py`）

```python
async def ingest_corpus(raw_dir: Path, embedder: Embedder, engine: AsyncEngine) -> IngestStats
```

1. 按路径排序列出清单里的文件。
2. 每篇计算 `content_hash = sha256(原始字节 + INGEST_VERSION)`，与数据库中的值比较：相同就跳过；不同或新文件就清洗、切块、批量嵌入子块，然后在**一个事务**里删除旧文档（级联删除块和向量），插入文档、父块、子块和向量。
3. 数据库中存在、但清单里已经没有的文档，删除。
4. 返回统计：新增 / 变化 / 未变 / 删除的文档数、父块数、子块数、子块长度列表、未知组件计数、残留标签数。

### 数据报告（`scripts/ingest.py`）

打印到终端，同时写入 `.cache/reports/ingest-<YYYYMMDD-HHMMSS>.md`，内容包括：

- commit、`INGEST_VERSION`、嵌入模型、耗时、嵌入速度（块/秒）
- 文档数：总数、按 edition、按 category；新增 / 变化 / 未变 / 删除
- 父块数、子块数；子块长度的最小值、p50、p95、最大值；超过 `CHILD_MAX_CHARS` 的前 10 个块（应当只有代码块和表格）
- 未知组件计数、残留标签数（应为 0）
- 3 个检查查询（只用向量检索，用 `db/corpus.py` 的 `nearest_chunks`），每个列出前 5 个块所属的文档。下表是我预期的结果，报告中只列出实际结果，由作者对照判断：

| 查询 | 预期命中 |
|---|---|
| 知识库单次最多上传几个文件 | `self-host/use-dify/knowledge/create-knowledge/import-text-data/readme` |
| 怎么修改上传文件的大小限制 | 上面这篇，以及 `self-host/deploy/configuration/environments` |
| 云版本怎么查看应用的监控数据 | `cloud/use-dify/monitor/` 下的文档 |

`nearest_chunks` 查询前执行 `SET LOCAL hnsw.iterative_scan = relaxed_order`。M2 会复用这个函数。

### 测试数据库（M0 已经建立）

集成测试使用独立的数据库 `grounded_rag_test`，绝不碰开发库，否则测试会清空已入库的语料。做法见 M0 Spec 的测试方案：conftest 自动建库、执行迁移，每个测试前清空表。

## 任务

- [ ] T1 语料清单与下载：`corpus.py` 及测试、`scripts/fetch_docs.py`、poe 任务 → AC1
- [ ] T2 清洗：`cleaner.py`、fixtures 和 golden 测试、全量无残留标签测试 → AC2
- [ ] T3 切块：`core/text.py`、`chunker.py` 及测试 → AC3
- [ ] T4 表与仓储：`tables.py`、0002 迁移、`db/corpus.py`（写入、删除、按哈希查询、`nearest_chunks`） → AC5 的一部分
- [ ] T5 GPU 嵌入：gpu 依赖组、`local_embedder.py`、`factory.py`、`tests/gpu/` → AC6
- [ ] T6 入库流程与报告：`pipeline.py`、`scripts/ingest.py`、增量的集成测试 → AC4、AC5、AC7
- [ ] T7 收尾：全量入库跑两遍，把报告摘要写进「记录」，对抗性自审，写日志，开当天的 PR

## 阻塞

## 记录
