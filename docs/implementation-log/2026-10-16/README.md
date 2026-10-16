# 2026-10-16

- 分支：`2026-10-16-framework-build`（基于 `main`，第一天）
- 里程碑 / 任务：开发前准备（规范、调研、M0 / M1 Spec）
- 模型：Claude Opus 5.5（写规范和 Spec）；实现交给 Claude Sonnet

## 做了什么

- 定稿开发规范：`AGENTS.md`（权限表、完成的定义、什么时候停下）、`docs/coding-standards.md`（标出由工具自动检查的条目）、`docs/workflow.md`（Spec → Plan → Implement → Verify、按天分支、开发日志）、`docs/decisions.md`。
- 目录结构改为 `backend/`（app、tests、eval、scripts、migrations 都在里面）+ `docs/` + 将来的 `frontend/`，不用 src layout。
- 参考了 Adaptive-rag 项目的诊断文档，把它踩过的坑提前写成规则：检查覆盖全仓库、mypy 从第一天就开 strict、不手写实测数字、评测报告记录 commit、ID 不用绝对路径、`.env.example` 与配置一致。
- 读了 proposal 引用的 6 篇评测论文，以及检索和编排相关资料，写成两份笔记：
  - [notes-evaluation.md](notes-evaluation.md)：6 篇论文，以及汇总出的评测题字段、配额和打分规则（§7）
  - [notes-rag.md](notes-rag.md)：语料实测、嵌入和精排模型、pgvector、RRF、BM25、Adaptive-RAG、Corrective RAG、DeepSeek
- 按调研结论更新 proposal：固定语料 commit、超长表格按行切、DeepSeek 模型名、nugget 分 vital / okay、不可回答题细分类别、评审需先人工校准。
- 写了 [M0 Spec](../../specs/M0-skeleton.md)（已批准）和 [M1 Spec](../../specs/M1-ingest.md)（待批准）。

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
- 解决：PR 改用 merge commit 合并，按日期顺序合并。已写进 workflow §3。

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
- 现象：作者指出 jieba 是 2020 年的库，不想用；也嫌「二元组 + 整词保留」麻烦。
- 排查：查了 PyPI 上 jieba 系列、pkuseg、LTP、HanLP、bm25s、rank_bm25 的最近发布日期；在隔离环境里用同一句话测了 jieba / rjieba / jieba-next / jieba3，切分结果完全相同（同一套词典和算法），并且都会拆碎 `UPLOAD_FILE_SIZE_LIMIT`、不认识「工作流」。顺带发现 `rank_bm25` 也是 2022 年的库。
- 解决：BM25 库换成 `bm25s`（2026-10 仍在更新，已验证可接受自己切好的词列表）；分词用字符二元组 + 保留英文标识符，约 10 行代码，不需要术语词典。M2 再用 Recall@5 与 rjieba 对照。日语版保留 SudachiPy 作为将来的方案。

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
| 本地 Adaptive-rag 项目的 `docs/19-project-diagnosis.md` | 前人踩过的坑，转成本项目的规则 |

## 验收证据

本日只写文档，没有代码。检查了环境：uv 0.9.26、Docker 28.5.1、gh 2.101.0、RTX 5070 Ti（驱动 610.88，16GB）。本机 Python 是 3.13，项目要求 3.12，由 uv 自动下载。

## 遗留 / 明天

- 作者审 M1 Spec，并决定第 7 条（测试集由谁出）。
- Sonnet 按 M0 Spec 开始实现。如果仍在 10-16 当天，就继续用本分支；否则新开 `2026-10-17-<两个词>`，从本分支创建。
