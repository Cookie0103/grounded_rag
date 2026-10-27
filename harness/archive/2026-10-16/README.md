# 2026-10-16

- 分支：`2026-10-16-framework-build`（基于 `main`，第一天）
- 里程碑 / 任务：开发前准备（规范、调研、M0 / M1 Spec）；M0、M1 实现
- 模型：Claude Opus 5.5（写规范和 Spec）；Claude Sonnet 5.5（实现 M0）

## 做了什么

- 定稿开发规范：`AGENTS.md`（权限表、完成的定义、什么时候停下）、`CODING-STANDARDS.md`（标出由工具自动检查的条目）、`WORKFLOW.md`（Spec → Plan → Implement → Verify、按天分支、开发日志）、`harness/context/`。
- 目录结构改为 `backend/`（app、tests、eval、scripts、migrations 都在里面）+ `docs/` + 将来的 `frontend/`，不用 src layout。
- 参考了 Adaptive-rag 项目的诊断文档，把它踩过的坑提前写成规则：检查覆盖全仓库、mypy 从第一天就开 strict、不手写实测数字、评测报告记录 commit、ID 不用绝对路径、`.env.example` 与配置一致。
- 读了 proposal 引用的 6 篇评测论文，以及检索和编排相关资料，写成两份笔记：
  - [notes-evaluation.md](notes-evaluation.md)：6 篇论文，以及汇总出的评测题字段、配额和打分规则（§7）
  - [notes-rag.md](notes-rag.md)：语料实测、嵌入和精排模型、pgvector、RRF、BM25、Adaptive-RAG、Corrective RAG、DeepSeek
- 按调研结论更新 proposal：固定语料 commit、超长表格按行切、DeepSeek 模型名、nugget 分 vital / okay、不可回答题细分类别、评审需先人工校准。
- 写了 [M0 Spec](../../build/phase-00-skeleton.md)（已批准）和 [M1 Spec](../../build/phase-01-ingest.md)（待批准）。

## M0 实现（Sonnet）

- `de5d83d` feat(M0-T1)：`backend/` 初始化，core（配置、错误、trace_id、日志）
- `ae3df31` feat(M0-T2)：质量门禁（pre-commit、评测数据只读权限）
- `0c00d57` feat(M0-T3)：providers 接口与离线假实现
- `e649e9e` feat(M0-T4)：数据库（compose、engine、alembic、独立测试库）
- `d4295b2` feat(M0-T5)：API（`/health`、统一错误、trace 中间件）
- `5ed8083` feat(M0-T6)：CI 与 README

## M1 实现（Sonnet）

- `1958271` feat(M1-T1)：语料清单与下载（182 篇，按 git blob 哈希校验）
- `254b72d` feat(M1-T2)：mdx 清洗（组件、HTML 表格、缩进还原、代码保护）
- `882ce7a` feat(M1-T3)：父子切块
- `615fec7` feat(M1-T4)：四张表、迁移 0002、仓储
- `7169dfd` feat(M1-T5)：GPU 嵌入与 gpu 依赖组
- `f502b9f` feat(M1-T6)：入库流程、数据报告、`poe ingest`
- `3fbc5f2`、`5b8672d`：修 CI 的两个问题（见困难 17、18）

## M2 实现（Sonnet）

- 分词（jieba3 + 保护变量名和术语 + 停用词）、bm25s 索引、RRF、检索器（向量 + BM25 并行 → 融合 → 精排 → 父块）、`POST /retrieve`
- 精排模型：Qwen3-Reranker（按模型卡的 yes/no 提示词）和 bge-reranker-v2-m3；第二个嵌入模型的补向量流程和迁移 0003
- `poe retrieve-demo`、`poe compare-retrieval`（9 种方案，28 题冒烟集），评测指标和题集读取放进 `backend/eval/`
- 结果和偏离见 [M2 Spec](../../build/phase-02-retrieval.md) 的「记录」

## M3 实现（Sonnet）

- 评测框架 `backend/eval/`：题目格式与校验器、打分（评审只给标签，分数由代码按 Spec 的换算表算）、bootstrap 置信区间、评审（直接调模型或命令行 `claude -p`，带一次重试）、评测器（并发、缓存、续跑、出错不中断）、Markdown 报告、错误归因（没检索到 / 上下文不足 / 生成错误）
- 命令：`poe eval-dev`、`poe eval-validate`、`poe export-for-gemini`；出题提示词在 `PROMPTS.md`
- 冒烟集（28 题，只检索）：Recall@5 92.9%，MRR 0.857；用词 similar 100%、distant 77.8%（和 M2 对比结果一致）
- 测试：eval 下 83 个单元测试，覆盖率 92%
- 结果和偏离见 [M3 Spec](../../build/phase-03-evaluation.md) 的「记录」

## M4 实现（Sonnet）

- `providers/deepseek.py`（httpx、重试、费用）、`providers/budget.py`（每日预算，记在 `.cache/budget/`）、`get_chat_model`
- 基线系统：无检索、朴素 RAG（向量 top5、不精排、不要求引用）；`poe eval-dev --system ... --judge claude|deepseek`
- 没有密钥，真实基线分数待作者；见 [M4 Spec](../../build/phase-04-baselines.md)

## M5 实现（Sonnet）

- `app/orchestration/`：护栏（规则）、路由、改写 / 分解、检索合并、证据评分与重检索（≤2 次）、上下文组装、带引用生成、忠实度校验（重生成 1 次）、LangGraph 组装；9 个版本化提示词在 `app/prompts/`
- 评测接入：`poe eval-dev --system full`
- 全部在假模型上验证；真实效果等密钥和开发集，见 [M5 Spec](../../build/phase-05-orchestration.md)

## M6 实现（Sonnet）

- 会话记忆：`app/core/session.py`、`SessionStore`（内存 + PostgreSQL，迁移 0004）、追问独立化、摘要（超过 6 轮并进摘要、保留 3 轮）、历史字数预算、版本记忆；`ChatRequest.session_id`
- 见 [M6 Spec](../../build/phase-06-memory.md)

## M7 实现（Sonnet）

- 缓存（嵌入 / 检索 / 完整回答）、精排熔断与降级、生成降级（只返回检索片段）、整次问答超时、令牌桶限流、启动预热
- `POST /chat`（JSON 与 SSE：每个环节一个 step 事件，最后 answer 事件）、MCP 服务（`search_docs`、`ask_docs`，`poe mcp`）、压测脚本（`poe load-test`）
- 压测数字和偏离见 [M7 Spec](../../build/phase-07-service.md)

## M8 实现（Sonnet）

- trace 持久化（`traces` 表，`GET /traces/{id}`）、反馈（`POST /feedback`）、干预库（`poe interventions`）、输出后处理（遮蔽密钥、黑名单、折叠重复）、坏例导出（`poe export-bad-cases`）；迁移 0005
- 见 [M8 Spec](../../build/phase-08-observability.md)

## 困难与解决

### 1. “表格不拆”的切块规则不可行
- 现象：proposal 原来写“代码块、表格不拆”。
- 原因：实测环境变量大全（`self-host/deploy/configuration/environments.mdx`）有 129KB、约 1035 行表格，单个小节的表格就远超子块上限。
- 解决：表格按行分组切，每组重复表头；代码块不超过 1500 字时不拆。已写进 proposal 和 M1 Spec。

### 2. mdx 组件内的内容带缩进，直接去标签会变成代码块
- 现象：Dify 文档里 `<Note>`、`<Tip>` 等组件内部的内容缩进了 4 个空格。
- 原因：去掉标签后，Markdown 会把缩进 4 格的内容解析为代码块，影响切块和显示。
- 解决：清洗时把组件解析成嵌套结构，输出时减少内部内容的缩进；用真实文档做 golden 测试（M1 Spec 的清洗部分）。

### 3. 文档没有版本字段
- 现象：front matter 只有 title、sidebarTitle、description 三个字段。
- 解决：版本从路径推出：`cloud/` 为云版，`self-host/` 为自部署版，其余为通用。document_id 用去掉前缀和后缀的相对路径，可读、跨机器稳定，评测集也直接引用它。

### 4. 按天叠分支与 squash 合并冲突
- 现象：作者要求每天从前一天的分支开新分支。
- 原因：如果 PR 用 squash 合并，后一天的分支里仍保留着前一天的原始提交，提 PR 时会重复出现这些提交，还会产生冲突。
- 解决：PR 改用 merge commit 合并，按日期顺序合并。已写进 WORKFLOW.md §3。

### 5. 集成测试会清空开发库
- 现象：M1 入库后，开发库里有完整语料；集成测试每次运行前要清空表。
- 解决：集成测试使用独立的数据库 `grounded_rag_test`，由测试夹具自动建库并迁移（M0 Spec）。

### 6. 两篇论文都简称 CRAG
- 现象：proposal 的评测部分引用 CRAG（Meta 的基准），编排部分的“证据评分”又像 Corrective RAG。
- 解决：两篇都读了，笔记里分开写并注明区别。打分采用 Meta CRAG 的 4 档制；Corrective RAG 只借鉴三态动作，不训练评估器，也不做网络搜索兜底。

### 7. 开发者和出题人现在都是 Claude
- 现象：原计划由 Codex 开发，现在改为 Claude Sonnet 开发，与出题的 Claude 同属一家。
- 解决：测试集保持放在仓库外，开发 agent 接触不到；评审以 Gemini 为主。proposal 的分工表已更新。如需更严格的隔离，可以让作者或 Gemini 出测试集，**请作者决定**。

### 8. jieba 太老，BM25 分词怎么选
- 现象：作者指出 jieba 是 2020 年的库，不想用。
- 排查：查了 PyPI 上 jieba 系列、pkuseg、LTP、HanLP、bm25s、rank_bm25 的最近发布日期；在隔离环境里用同一句话测了 jieba / rjieba / jieba-next / jieba3，切分结果完全相同（词典内容相同），并且都会拆碎 `UPLOAD_FILE_SIZE_LIMIT`、不认识「工作流」。顺带发现 `rank_bm25` 也是 2022 年的库。我一度建议用字符二元组，作者选了 jieba3 + bm25s。
- 解决：中文分词用 jieba3（现代 Python 3 重写版，只依赖 pydantic），BM25 用 bm25s（2026-10 仍在更新）。检查 jieba3 的接口发现它**没有用户词典接口**，所以在切词前用正则保护变量名和术语表，其余文字再交给 `cut_query`。在本机跑通：变量名和术语不被拆，三个测试查询都排到第 1。字符二元组留作 M2 的对照。

### 9. 分块：固定窗口 vs 语义切分 vs 按结构切
- 现象：作者看不懂「表格怎么拆」，并问固定字数切是否太生硬、是否该用语义切分，以及 Adaptive-rag 怎么做。
- 排查：读了 Adaptive-rag 的 `chunking.py`（按标题分节后 500 字窗口、重叠 60，硬切）；查了语义切分的论文（NAACL 2025 Findings）和 Anthropic 的 Contextual Retrieval。
- 解决：保持按文档结构切（不是固定窗口，也没有重叠）；不做语义切分；表格按字数分组，每组几行不固定，M2 对照「一行一块」；标题路径拼进嵌入和 BM25 文本，作为 Contextual Retrieval 的免费简化版。澄清了一个误会：1024 是向量维度，不是字符数。已写进 Notion 4.2–4.5 节和 notes-rag §11。

### 10. 开发前的环境检查发现 Docker 没开、端口被占
- 现象：`docker info` 连不上守护进程；5432 被 Windows 上的 `postgres.exe` 服务占用；改成 5433 后依然连到别人的库（`用户 "grounded" Password 认证失败`），`netstat` 显示 5433 上有两个监听者（本机的另一个 PostgreSQL 实例和 Docker）。
- 解决：启动 Docker Desktop；compose 端口改为 `${DB_PORT:-5432}:5432`，本机 `.env` 设 `DB_PORT=15432`。CI 用默认的 5432。没有动用户本机的 PostgreSQL 服务。

### 11. ruff 0.17 的 format 会改 Markdown 里的代码块
- 现象：`pre-commit run --all-files` 后 docs 里 3 个文件被改动（代码块被重排）。
- 解决：`git checkout -- docs` 还原；pre-commit 的两个 ruff 钩子加 `types_or: [python, pyi]`。`backend/` 内的 `poe fmt` 只处理 `backend/`，不受影响。

### 12. 几个小的检查报错
- ruff `ASYNC109`：async 函数不能有名为 `timeout` 的参数 → 改名 `timeout_seconds`。
- ruff `RUF001/2/3`：中文注释里的全角标点被当成易混淆字符 → 在配置里忽略这三条。
- mypy 报两个 `conftest` 模块重名（`tests/unit/api` 和 `tests/integration`）→ `tests/` 各级目录加 `__init__.py`。
- Windows 上 `ASGITransport` 默认会把应用里未捕获的异常抛进测试 → 测试客户端设 `raise_app_exceptions=False`，才能断言 500 响应。
- 一次写多个大 heredoc 时 bash 报语法错，整条命令没有执行 → 改用 Write 工具逐个写文件。

### 13. 实际的 mdx 比 Spec 里列的复杂
- 现象：Spec 按 12 种组件设计清洗；真正统计 182 篇后，还有 `Danger`、`Check`、`Callout`、`Columns`、`Column`、`CodeGroup`，17 个 HTML 表格，大量 `div` / `ul` / `span` / `p`，以及 `<token>`、`<SCHEME>` 这种不是标签的尖括号文字。
- 排查：写脚本统计所有标签和属性（排除代码块），再逐类看真实例子。
- 解决：清洗时先把围栏代码和行内代码换成占位符；字面尖括号靠「已知 HTML / 组件名，或者文档里有对应闭合标签」来判断是不是标签；HTML 表格转 Markdown；容器类 HTML 和组件一样还原缩进；`<br>` 在表格里换成空格。每改一次规则就重新生成并逐篇核对 golden 文件，最后对 182 篇全量检查残留标签为 0。

### 14. 表格行为对齐补了几十个空格，子块被撑到 700 字
- 现象：切块后有 3 个非代码子块超过 500 字，都是 `local-source-code` 里的表格行。
- 原因：原文用空格把表格列对齐，一行里有一大片空格。
- 解决：清洗时把表格行里连续的空格压成一个。之后超过 500 字的子块全部是代码块。

### 15. 一个列表步骤带代码块，整项 4000 多字切不动
- 现象：第一版切块里最长的子块 4495 字，父块也超过 4000。
- 原因：列表按「项」切，而带代码块的编号步骤自己就很长。
- 解决：某一项超长时才拆到行，代码块作为整体保留；代码块超过 1500 字再按行切并补上围栏。

### 16. HNSW + 版本过滤的测试怎么写才有意义
- 现象：用假嵌入（哈希到固定维度的稀疏向量）写「近邻全是云版时仍能找到自部署版」的测试，带过滤时一条都搜不到，`ef_search` 调到 400 也一样。
- 原因：这些向量互相几乎正交，距离几乎都一样，HNSW 图的连通性很差，不能代表真实的稠密向量。另外，planner 可能先按版本过滤再排序，根本不走 HNSW，对照实验就失效了。
- 解决：测试改用确定性的稠密向量；断言「找到的都是自部署版、至少 3 条、且 `nearest_chunks` 确实在事务里开了 `hnsw.iterative_scan`」。

### 17. CI：干净的 clone 里 `.cache` 目录不存在
- 现象：本机通过，CI 里 4 个用 `tmp_path` 的测试报 `FileNotFoundError: .cache/pytest-tmp`。
- 原因：我把 pytest 的临时目录指到了仓库的 `.cache/pytest-tmp`（本机系统临时目录有权限问题），干净 clone 里 `.cache` 还不存在。
- 解决：`tests/conftest.py` 的 `pytest_configure` 先建好上级目录；验证时把本机的 `.cache` 临时改名再跑一遍。

### 18. CI：HNSW 测试偶发只返回 4 条
- 现象：同一个测试本机连跑 5 次都通过，CI 上一次返回 4 条。
- 原因：HNSW 是近似检索，图是随机建的，个别点可能搜不到。
- 解决：断言放宽为至少 3 条且全是自部署版，并在注释里写明原因。

### 19. PyTorch 该选哪个 CUDA 版本
- 现象：Spec 写的是 cu128；实际查官方源发现 cu128 最高只到 torch 2.11。
- 解决：用 cu130（torch 2.14.1），本机驱动 610.88 支持 CUDA 13.3；验证 `torch.cuda.get_device_capability()` 是 (12, 0)，并实际跑了一个矩阵乘核函数。

### 20. 工具使用上的两个坑
- 终端工具会把 heredoc 里的反斜杠转义吃掉一层（`"\\n"` 变成换行），用 Python 脚本批量改带反斜杠的代码时会静默改错或断言失败 → 改用 Edit / Write 工具改文件。
- 一次写很多大 heredoc 时 bash 报语法错，整条命令没有执行 → 同上。
- pre-commit 的 ruff 拦住了一次含超长注释的提交（E501），符合预期。

### 21. BM25 的空白检索：「完全无关的内容」也能命中
- 现象：单元测试里，一个和语料毫无关系的查询竟然命中了一个文档，分数 0.52。
- 原因：分词后有「的」这个单字，语料里恰好有一篇含「的」。
- 解决：加一份单字虚词停用词表（的、了、和、与…）；查询和文档共用同一个分词函数。

### 22. bm25s 不能建空索引
- 现象：语料为空时 `index()` 抛 `ValueError: max() iterable argument is empty`。
- 解决：没有文档就不建索引，`search` 直接返回空列表，加了测试。

### 23. 检索器的组装位置
- 现象：`/retrieve` 的检索器要读库建 BM25 索引、加载两个模型，约 40 秒。
- 解决：第一次请求时才建，用锁防止并发重复建；单元测试用依赖覆盖换成假的。M7 做服务时改成启动时预热。

### 24. 评测并发调用时本地模型加载出错
- 现象：`poe eval-dev` 用 4 路并发，所有题都报 `Cannot copy out of meta tensor` 或 `float != Half`。
- 原因：两个线程同时懒加载同一个 GPU 模型，一个线程拿到了没加载完的模型。
- 解决：嵌入和两个精排模型都加 `threading.Lock`，加载只做一次，GPU 推理也排队（本来也不能真并行）。

### 26. LangGraph 的类型标注与 mypy
- 现象：`add_node` 的重载和 `dict[str, Callable]` 对不上，mypy 报 `call-overload`。
- 解决：节点表标成 `dict[str, Any]`；状态用 TypedDict，`MeteredChat` 要在 State 之前定义（用字符串前向引用会让 mypy 认不出状态类型）。

### 27. 单元测试没有 lifespan，限流器和服务容器不能放在 lifespan 里
- 现象：给所有路由加了限流依赖后，已有的接口测试全部 `AttributeError: 'State' object has no attribute 'limiter'`。
- 原因：测试用 `ASGITransport`，不会跑 lifespan。
- 解决：限流器和服务锁在 `create_app()` 里建；lifespan 只管引擎和预热。

### 28. MCP SDK 2.x 的接口变了
- 现象：`from mcp.server.fastmcp import FastMCP` 报「mcp 2.x 里改名为 MCPServer」。
- 解决：按报错用 `mcp.server.mcpserver.MCPServer`；客户端用 `mcp.Client(StdioServerParameters(...))`；工具里抛 `ValueError`，`call_tool` 会变成 `UnexpectedToolError`。

### 25. 超时杀掉的子进程在测试结束后报警告
- 现象：命令行评审超时测试通过，但 pytest 报 `Event loop is closed` 的 ResourceWarning。
- 解决：`process.kill()` 之后 `await process.wait()`。

## 查阅资料

| 资料 | 结论用在哪 |
|---|---|
| [CRAG 基准](https://arxiv.org/abs/2406.04744) | 4 档打分和可信得分；按题型报告；必须做无检索基线 |
| [TREC 2024 RAG AutoNuggetizer](https://arxiv.org/abs/2504.15068) | nugget 分 vital / okay，主指标 V_strict；单题判定不可靠，只看平均 |
| [Sufficient Context](https://arxiv.org/abs/2411.06037) | 充分性提示词，同时用于错误归因和系统的“证据够吗”节点；不一律拒答 |
| [Know Your RAG](https://arxiv.org/abs/2411.19710) | 题型分类；先答案后问题的出题法；4 条审题标准 |
| [UAEval4RAG](https://arxiv.org/abs/2412.12300) | 不可回答题的类别与每类的可接受行为；拒答指令要做对照实验 |
| [DataMorgana](https://arxiv.org/abs/2501.12789) | 每题标 4 个属性（用户、措辞、前提、用词距离）；单篇事实题一篇一道 |
| [Adaptive-RAG](https://arxiv.org/abs/2403.14403) | 训练过的分类器也只有约 54% 准确率，所以采用规则兜底，不确定时走 SINGLE |
| [Corrective RAG](https://arxiv.org/abs/2401.15884) | 证据评分的三态动作；封闭语料不做网络搜索 |
| [Qwen3-Embedding 模型卡](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | 查询加指令、文档不加；左侧填充；接口区分查询和文档 |
| [Qwen3-Reranker 模型卡](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) | yes/no 打分方式；中文上 bge 略好，所以对比实验有意义 |
| [bge-m3 模型卡](https://huggingface.co/BAAI/bge-m3) | 同为 1024 维，向量表加 model 列，可同时存两种向量 |
| [pgvector README](https://github.com/pgvector/pgvector) | HNSW 参数；过滤在索引之后执行，需要 iterative scan |
| [DeepSeek 价格页](https://api-docs.deepseek.com/quick_start/pricing) | 模型 `deepseek-flash`；¥10/天大约够 1400 次调用 |
| langgenius/dify-docs 仓库（用 `gh api` 实测） | 固定 commit、182 篇的构成、92 个同名页面、组件使用统计 |
| Google eng-practices、Claude Code 最佳实践、spec-kit、Codex cookbook、GPT-6 Astra 提示词指南 | 规范与流程（见 workflow.md） |
| PyPI 发布记录（jieba、rjieba、bm25s、rank_bm25、HanLP、SudachiPy 等）与本机实测 | BM25 库和分词方案的选择（见困难 8） |
| [Is Semantic Chunking Worth the Computational Cost?](https://arxiv.org/html/2410.13070v1)、[Anthropic Contextual Retrieval](https://anthropic.com/news/contextual-retrieval) | 不做语义切分；标题路径拼进检索文本（见困难 9） |
| [PyTorch 官方 whl 索引](https://download.pytorch.org/whl/)、Qwen3-Embedding 模型卡 | cu130 才有最新 torch；Qwen3 左填充、仅查询加指令（见困难 19） |
| GitHub REST API（git/trees）、`git hash-object` 的 blob 哈希规则 | 语料下载与校验（M1-T1） |
| pgvector README（iterative scan） | `nearest_chunks` 带版本过滤（见困难 16） |
| 本地 Adaptive-rag 项目的 `docs/19-project-diagnosis.md` | 前人踩过的坑，转成本项目的规则 |

## 验收证据

M0 和 M1 的验收标准全部满足，详细结果和偏离见 [M0 Spec](../../build/phase-00-skeleton.md) 与 [M1 Spec](../../build/phase-01-ingest.md) 的「记录」。关键输出：

**M0**
- **AC1/AC5**：`uv run poe check` → 格式、lint、`lint-imports`（1 kept, 0 broken）、mypy（no issues）、38 passed，覆盖率 95.02%。
- **AC2**：`alembic upgrade head` → `Running upgrade -> 0001, enable pgvector`；`poe test-int` → 3 passed；pgvector 0.8.7。
- **AC3**（真实服务 + curl）：数据库正常 `200`；带 `X-Trace-Id: demo-001` 响应头和 body 都是它；未知路径 `404` 统一格式；`docker compose stop db` 后 `503`；恢复后 `200`。
- **AC4**（故意违规，已删除临时文件）：core 反向 import api → `lint-imports` 拦截；`import openai`（以及 `from openai import X`）→ ruff `TID251`；`os.environ` → `TID251`；`print` → `T201`；缺类型标注 → mypy `no-untyped-def`。
- **AC6**：GitHub Actions `check` 和 `integration` 两个 job 都成功。AC7、AC8 见 M0 Spec 记录。

**M3**
- `poe check`：279 passed，覆盖率 92%；`poe test-int` 23 passed；`poe test-gpu` 3 passed。
- `poe eval-dev --questions eval/smoke_retrieval.jsonl`：Recall@5 92.9%（见上）。`poe export-for-gemini`：2 份。

**M1**
- **AC1**：`poe fetch-docs` 两次：第一次下载 182 篇（6 秒，1.6MB），第二次「已存在，跳过」。
- **AC2/AC3**：golden + 全量 182 篇无残留标签；切块 28 个测试。
- **AC4**：`poe ingest` 两次：新增 182、嵌入 2090 个子块（18.4 秒，114 块/秒）→ 未变 182、嵌入 0。
- **AC6**：`torch 2.14.1+cu130 True (12, 0) NVIDIA GeForce RTX 5070 Ti`；`poe test-gpu` 3 passed。
- **AC7**：数据报告 `.cache/reports/ingest-20261016-144501.md`，摘要在 M1 Spec 的「记录」里。
- **AC8**：`poe check` 152 passed，覆盖率 92%；`poe test-int` 19 passed；CI 全绿（最新一次 `5b8672d`）。

## 遗留 / 明天

- **作者要看**：M1 的数据报告（`.cache/reports/ingest-20261016-144501.md`，摘要在 M1 Spec 记录里）；还有清洗 / 切块的 golden 文件（`backend/tests/fixtures/dify/*.expected.md`）。
- **需要作者回来后做**：从仓库根目录启动 Claude Code，试一下能不能编辑 `backend/eval/data/`（应该被拒绝）；在 Gemini 网页端出评测题（M3），需要的话我可以先导出清洗好的 182 篇文档。
- **下一步 M2**（检索）：BM25（bm25s + jieba3）、RRF、Qwen3-Reranker、`/retrieve`。先写 M2 的 Spec，作者批准后再做。M1 报告里「怎么修改上传文件的大小限制」只排到第 5，正好是 BM25 要解决的问题。
- 没有开 PR、没有合并 main（作者要求）；所有提交都在 `2026-10-16-framework-build`。
