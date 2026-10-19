# 评测运行手册（给作者）

> 框架与真实调用的验证状态见 [build-log](../../harness/build-log.md)。除明确写出的 Docker 命令外，命令在 `backend/` 下执行。

## 当前采用的评测口径（2026-10-19）

作者已确认 [评测 V1](metrics-v1.md)：最终证据覆盖率、答案要点覆盖率、事实有据率、有效引用覆盖率、边界处理正确率；沿用旧总分，自动附带耗时与生成成本。定义、分母、N/A、异常、论文取舍和 20 / 70 / 30 的读法以 V1 为准。

新增证据 / 事实 / 引用自动评分尚未实现，下面已有 `eval-dev` 命令不会自动产出全部五项。首批待审开发题见 [dev20](dev20/README.md)，使用既有格式校验器：`uv run poe eval-validate ../docs/eval/dev20/questions.jsonl`。不覆盖 `eval/data/`，作者审题后才冻结并运行正式比较。

## 0. 准备（一次）

1. 在 `.env` 里写 `DEEPSEEK_API_KEY=...`（不要提交）。`DAILY_BUDGET_CNY=0` 表示你手动测试不限额；agent 自己跑时保持 `10`。
2. 仓库根目录运行 `docker compose up -d db`；进入 `backend/`，运行 `uv sync --extra gpu` → `uv run alembic upgrade head` → `uv run poe fetch-docs` → `uv run poe ingest`（已做过的会跳过）。本机端口以 `.env` 的 `DB_PORT` 为准，须与 `DATABASE_URL` 相同。
3. 确认检索正常：`uv run poe eval-dev --questions eval/smoke_retrieval.jsonl`，应看到 Recall@5 约 92.9%。

## 1. 出题（Gemini 网页端）

先把这几个词说清楚：

- **语料**：系统用来回答问题的那 182 篇 Dify 文档。
- **导出**：把这些文档整理成几份 Markdown 文本文件，方便上传给 Gemini；不需要手工复制文档，也不调用付费模型。
- **开发题**：可以反复测、看错题并据此改系统的练习题，共 70 道。
- **封存测试题**：另外留出的 30 道验收题，系统定稿前不给开发 agent 看，最后由作者运行；不能用它调系统。
- **先做 20 道**：先完成 70 道开发题中的 20 道，再补 50 道，不是额外出题。总计始终是 `20 + 50 + 30 = 100`。

1. `uv run poe export-for-gemini` → `.cache/gemini-pack/part-01.md …`。
2. 按 [PROMPTS.md §6](../../PROMPTS.md) 开一个新对话：先粘贴提示词，再上传所有 `part-*.md`，说「开始出题」。
3. 把输出的 JSON Lines 存成 `backend/eval/data/dev.jsonl`（`split` 为 `dev` 的约 70 题）；`split` 为 `test` 的约 30 题存到**仓库外**（例如 `D:\eval-private\test.jsonl`），不要让 agent 看到。
4. `uv run poe eval-validate`：应为 0 个错误；有错误就把提示贴回 Gemini 让它改。提醒（题干里有「根据文档」之类）建议改掉。
5. 人工过一遍 70 道开发题：问题是否独立成立、金标文档是否真的有答案、关键点是否原子。

### 第一批开发题怎么准备

先打开现成的 `.cache/gemini-pack/part-01.md` 和 `part-02.md`，上传给 Gemini，并使用 [PROMPTS.md §6](../../PROMPTS.md) 的提示词。追加：“这次只出 20 道开发题，全部 split=dev，不生成测试题；按下面数量出题，每道先找原文依据，再写问题和期望要点。”

| 题型 | 数量 | 要检查什么 |
|---|---:|---|
| 单篇事实 fact_single | 7 | 一个明确问题；其中至少两题用用户口语替换原文术语，观察改写是否有帮助 |
| 归纳 summary | 3 | 一段或几段内容能否完整总结，不能只命中一个关键词 |
| 跨篇 reasoning | 4 | 至少两篇文档分别提供必要证据，不能把两个互不依赖的问题硬拼在一起 |
| 版本 version | 2 | 写明 cloud / self_host，检查有没有混用另一版本的答案 |
| 不可直接回答 unanswerable | 4 | 含糊需反问、无关需拒绝、注入需拒绝、相关但库内缺依据，各一题 |

这些是题型，和路由不是同一个分类。实际只有五路：DIRECT 闲聊、SINGLE 单跳、MULTI 分解、CLARIFY 反问、REFUSE 无关/注入拒绝；改写是步骤。DIRECT 用“你好”“你能做什么”手工检查即可，不强塞进正式文档问答题集。两句操作检查不计入正式题量；第一批 20 道仍全部计入 70 道开发题。

每题只需人工核对：①问题自然且独立；②正确文档 `gold_docs`；③应回答的 2～4 个要点 `nuggets`；④预期路线；⑤版本。不可回答题不填 nuggets。可另外抄下“文件路径 → 标题 → 原文段落”便于自己复核。**先确认原文和期望答案，再运行 RAG，避免把系统答复当标准答案。**

当前自动检索指标以金标文档为单位，尚没有逐 chunk 的人工金标评分。运行记录会保留 chunk ID、原文和父块，可人工检查它是否支持期望要点；“检索到金标文档”不等于“找全了所有必要证据”。只检索的报告也不能代表回答质量。

## 2. 开发集上跑各系统

```bash
uv run poe eval-dev --system retrieval                           # 只看检索：Recall@5、按题型 / 用词分组
uv run poe eval-dev --system no-retrieval --judge deepseek       # 基线一
uv run poe eval-dev --system naive-rag    --judge deepseek       # 基线二
uv run poe eval-dev --system full         --judge deepseek       # 完整系统
```

- 报告在 `.cache/eval/<系统>/report.md`；回答和评审标签都缓存在同目录，中断后重跑会接着做。
- 评审默认用 `CHAT_MODEL` 配置的 DeepSeek。设计里的「Gemini 主评、Claude 复评」需要命令行后端：`--judge claude` 会调 `claude -p`（消耗你的 Claude 用量，先在 5 题上试）。
- 100 题的大致花费：被测系统 + 评审，`deepseek-flash` 每题几分钱，总共应在 ¥10 以内；超了会抛 `BUDGET_EXCEEDED` 而不是继续花。

## 3. 校准评审（必须做）

1. 从 `.cache/eval/full/answers.jsonl` 随机挑 20 条（含可回答和不可回答）。
2. 对每条，自己按 [notes-evaluation §7.3](../../harness/archive/2026-10-16/notes-evaluation.md) 的规则判：每个关键点 support / partial_support / not_support、有没有矛盾、行为（回答 / 反问 / 拒答）。
3. 与 `verdicts.jsonl` 里的标签对比。**一致率 ≥ 85% 才采信自动评审**；不到就改 `eval/prompts/judge_v1.md`（新增 `judge_v2.md`，不要覆盖）并重跑。

## 4. 完整消融与模型对比

| 行 | 命令 / 配置 | 说明 |
|---|---|---|
| 无检索 | `--system no-retrieval` | |
| naive RAG | `--system naive-rag` | 向量 top5，不精排 |
| + 混合检索与精排 | `--system hybrid-rag` | 混合检索 + 精排，直接生成 |
| + 改写与自适应路由 | `--system routed` | 护栏、路由、改写 / 分解、带引用生成；关掉证据评分和校验 |
| + 校验与拒答 | `--system full` | 再加证据评分（重检索 / 拒答）和忠实度校验 |
| 嵌入模型对比（只看 Recall@5） | `poe compare-retrieval`（已有 9 种方案，换成开发集：`--questions eval/data/dev.jsonl`） | |

> 每行报 4 个核心指标：可信得分（带 95% 区间）、Nugget 召回（V_strict）、Recall@5、P95 与单题成本。题量只有 100，差距小于置信区间时不宣称提升，如实写「没用」。

## 5. 测试集（只跑一次）

1. 确认开发集上的所有改动都已提交、不再改提示词和规则。
2. `uv run poe eval-dev --system full --judge deepseek --questions D:\eval-private\test.jsonl`（输出目录在 `.cache/eval/full`，**先把开发集的缓存移走**，否则会续用开发集的回答缓存）。
3. 把数字填进 [final-report-template.md](../final-report-template.md)。测试集结果不能用来再调参。

## 6. 服务与 MCP 的人工验证

- `uv run poe serve` → 打开 `http://127.0.0.1:8000/docs`，用 `POST /chat` 试几个问题；`"stream": true` 看 SSE。
- `claude mcp add grounded-rag -- uv run --directory <仓库>/backend poe mcp`，在 Claude Code 里让它「用 grounded-rag 查一下知识库最多上传几个文件」。
- `uv run poe load-test --endpoint chat --unique --requests 50 --concurrency 4`（服务端设 `RATE_LIMIT_PER_MINUTE=0`）：记下 QPS 和 P95。

## 7. 看每道题的实验过程

新运行的 `.cache/eval/<系统>/answers.jsonl` 每行是一道题，`steps` 按执行顺序保存过程。REST `/chat`、SSE 最终回答及 `GET /traces/{trace_id}` 的 `steps` 使用相同结构。

| 步骤 | 详情位置 | 能看到什么 |
|---|---|---|
| `rewrite` / `decompose` / `retry_query` | `details.queries` | 实际使用的改写查询、子问题列表及补证据查询，列表长度就是这一轮查询数 |
| `retrieve` | `details.retrievals` | 每条 query 的 `recall_candidates`（两路召回合并，含两路排名与分数）、`reranked_candidates`（精排候选及分数）、`candidates`（最终 top-k）和父块 |
| `retrieve` | `details.parents` | 本轮结束后跨子问题、跨轮次合并去重的父块 |
| `grade` | `details.sufficient`、`details.missing` | 是否足够、还缺什么；关闭或解析失败的退路看 note |
| `generate` | `details.context`、`details.output` | 实际资料文本与本次模型原始回答；重生成各记一条，保留截断和引用处理前输出 |
| `verify` | `note`、`details.output` | 校验结果及模型返回的无依据说法 |
| `direct` / `clarify` / `refuse` / `abstain` | `details.output` | 闲聊、反问、范围拒绝和证据不足拒答的输出 |
| `postprocess` | `note`、`details.output` | 通过无修改、遮蔽、重复折叠或黑名单拦截及处理后答案 |
| `answer_cache` | `note` | 本次命中缓存，没有重新生成；不把历史生成步骤冒充本次执行，费用为零 |
| `pipeline_error` | `note` | 触发降级的异常类别；此前完成步骤仍保留 |
| `fallback_retrieve` | `details.retrievals` | 生成不可用后用于返回片段的检索结果；不冒充模型已接收的上下文 |

`contexts` 仍是原来的父块正文列表；判断“模型究竟看到了什么”请以 `generate.details.context` 为准。未执行生成的拒答或只检索请求，没有生成上下文。无检索基线的生成上下文为空字符串。

精排关闭或降级时 `reranked_candidates` 为空，不代表执行了精排。`recall_candidates` 的 rank 是融合名次；精排名次以 `reranked_candidates` 的列表顺序为准。检索结果的 `cached=true` 表示复用候选，其内部耗时来自原检索，没有在本轮重跑 GPU 推理。未完成节点不保证有本地详情，评测异常仍由 error 字段报告。

旧 JSONL 缓存仍可读取，但不能自动补出历史过程。要拿到新记录，先把相应系统的旧缓存移到另一个实验目录再重跑；换题集、模型或提示词也应隔离缓存，避免复用旧答案。

## 8. Langfuse 云端与最终静态报告

在 Langfuse 免费项目 Settings → API Keys 创建项目凭据，只填仓库根目录 `.env`，不要发到聊天或提交 Git：

```dotenv
LANGFUSE_PUBLIC_KEY=你的项目公钥
LANGFUSE_SECRET_KEY=你的项目私钥
LANGFUSE_BASE_URL=你的项目所在区域地址
```

区域地址按项目设置复制；常见为欧洲 `https://cloud.langfuse.com`、美国 `https://us.cloud.langfuse.com`、日本 `https://jp.cloud.langfuse.com`。保存后重启服务或重新执行终端命令。

- `/chat`、MCP `ask_docs`、终端 `scripts.ask` 共用服务：每个步骤完成后进入 SDK 后台发送队列，Langfuse 中查看 `grounded-rag`。步骤显示为完成事件，真实耗时在 `ms` / `duration_ms`；不是伪造的节点时间线。服务关闭会发送剩余队列。
- `poe eval-dev` 中新执行的题在 `eval/<系统名>`，Input.expected 是原题、gold_docs、nuggets、expected_route，Output 是生成答案，步骤事件含 chunk 与上下文。评测步骤在该题完成后发送；评审分数仍保存在本地 verdicts/report，此次未迁移自动评审任务。
- 云端 metadata 的 `trace_id` 对应本地数据库 trace；CLI 默认也打印此 ID。Langfuse 内部 ID 是同一应用 ID 的确定性映射。评测运行不写服务的 traces 表，详情保存在 answers.jsonl。
- 缺任一密钥时停用云端，终端明确提示；SDK 后台上传失败会记录日志，本地记录不受影响。**填了密钥和本地成功不代表云端已成功，首次需在 Langfuse 页面确认。**
- 评测旧缓存命中的题不重跑，也不会自动补传云端；需新实验时先隔离旧缓存。命令行 `retrieve-demo`、裸 `/retrieve`、MCP `search_docs` 只用于检索诊断，此次没有单独上传云端。

选型：开发过程用 Langfuse Cloud Hobby；系统定稿并完成正式实验后，把题目、期望要点、各版本答案、逐步证据、人工点评和汇总指标导出为 JSON + HTML，发布 **GitHub Pages**。免费 Pages 使用公开仓库，封存测试题在最终验收前不公开。Hugging Face Static Space 也能托管同样文件，但当前不需要依赖它；发布格式不绑定某个观测平台。

官方核对（2026-10-19）：[Langfuse Hobby](https://langfuse.com/pricing) 免费、每月 50k units、30 天历史访问，并非永久档案；[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) 和 [HF 静态 Space](https://huggingface.co/docs/hub/spaces-sdks-static) 都能展示 HTML。云端不是本地唯一备份，正式结果须在可访问期内归档。当前题集未完成，还没有发布静态站点。

## 9. 本机直接提问与文档位置

首次安装依赖用 `uv sync --extra gpu`；不用 `uv add create`，也不需要自己找 main 函数。已有原文、模型和入库数据时，不用重复下载和入库。

```powershell
cd D:\项目\秋招项目\SONY\grounded_rag
docker compose up -d db
cd backend
uv sync --extra gpu
uv run python -m scripts.ask "知识库单次最多上传几个文件？" --edition self_host
# 完整过程 JSON（日志在 stderr，JSON 在 stdout）
uv run python -m scripts.ask "你的问题" --json
# 同一个会话 ID 可连续测试追问
uv run python -m scripts.ask "你的问题" --session-id demo
# 只检索，不让 DeepSeek 生成答案
uv run poe retrieve-demo "你的问题"
# 常驻服务，后续反复提问无需每次启动新进程
uv run poe serve
```

常驻服务打开 `http://127.0.0.1:8000/docs`，执行 POST /chat。或另开一个 PowerShell：

参数含义：`edition=self_host` 查自部署版和通用文档，`cloud` 查云版和通用文档；不填可由问题/历史判断，仍未确定时不限制。CLI 的值是 `self_host`（下划线），不是 `self-host`。`session_id` 是同一段对话的编号，沿用同一个值就能追问；独立测试可省略或在 JSON 中设为 null，不要把示例 `"string"` 当固定值。

`python -m scripts.ask` 表示按 Python 模块运行 `backend/scripts/ask.py`，不是调用名叫 scripts.ask 的函数；该文件的 main 解析参数，再调用 run 和已有 ChatService。`stream=false` 一次返回完整结果，true 则逐步推送。

```powershell
$payload = @{question="知识库单次最多上传几个文件？"; edition="self_host"} | ConvertTo-Json
$result = Invoke-RestMethod -Uri http://127.0.0.1:8000/chat -Method Post -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($payload))
$result.answer
$result.steps | ConvertTo-Json -Depth 30
```

本机数据库端口已按作者要求固定为 **5432**。此前密码认证失败是连到了占用 5432 的 Windows PostgreSQL 18；该服务现已停止并改为手动启动，RAG 容器接管 5432。Travel Agent 的 Docker PostgreSQL 17 仍用 5434，不受影响。`.env` 改动后需重启正在运行的 `poe serve`；仅打开 `/docs` 成功不代表数据库可用，应检查 `/health`。PowerShell 的 `docker compose up -d db` 末尾不要加反斜杠，否则服务名会被当成 `db\`。

Windows 本机 PostgreSQL 17 也已按作者要求停止并改为手动启动，5433 已释放。两个项目继续各用自己的 Docker 数据库。

端口配置分别由不同程序读取：`DATABASE_URL` 给 Python / SQLAlchemy，表示“连接哪个地址”；可选 `DB_PORT` 只给 Docker Compose，表示“把容器端口映射到本机哪个端口”。当前 compose 写的是 `${DB_PORT:-5432}:5432`，即未填 DB_PORT 时默认用 5432。因此作者已删除 `.env` 的 `DB_PORT=5432`，保留 DATABASE_URL 中的 5432 即可；以后不要为了当前配置重新添加它。只有换用其他端口时才需要两处同步。

语料是 **Dify** 文档。冻结来源为 [langgenius/dify-docs 的中文目录](https://github.com/langgenius/dify-docs/tree/c80a31868611b673bd77725a6310c685068a585e/zh)，不是金融 DeFi 文档。下载器通过 GitHub 文件树选择 corpus.py 列出的目录，再下载 raw.githubusercontent.com 的 MDX 原文、校验 Git blob 哈希；没有抓取页面渲染后的 HTML。

- 原文：`data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/`，按原仓库目录保存。
- 处理后：数据库 `documents` / `parent_chunks` / `chunks` / `chunk_embeddings`；持久卷由 `docker compose` 管理，连接串是数据库地址，不是网页。模型权重在 `.cache/models/`。
- 切分：清理 MDX 组件噪声，按 H2/H3 组织父块，父块最多 4000 字符；子块目标 300、通常上限 500 字符，代码块允许到 1500；表格按行拆且保留表头。检索子块，送给生成的是合并父块并截断后的上下文。
- 两套模型：Embedding 配置 `qwen3` / `bge-m3`；Reranker 配置 `qwen3` / `bge`。它们是检索模型，不是“正确答案模型”。DeepSeek 才是路由、改写、证据判断和回答生成的大脑；正确答案由作者根据原文确认。

## 10. 首轮20题诊断与后续逐轮保存

已完成轮次：[2026-10-19 首轮报告](results/runs/2026-10-19_1855_dev20_full-service/README.md)。本机可直接打开同目录 `report.html`，逐题看预期/实际路由、参考/实际答案、逐点评分和可展开的完整过程。20题及评分均已在Langfuse服务端读回核验，链接在每道题内；本轮是当前agent辅助初评，金标和评审未经过作者校准。

| 材料 | 文件 |
|---|---|
| 题目、参考答案、要点与证据、评分口径 | questions.jsonl、evidence.json、metrics-v1.md |
| 仅最终答案 / 评测器完整作答 | answers-only.jsonl / answers.jsonl |
| 每步查询、召回/精排/最终chunk、缺失信息、实际上下文、生成与校验 | traces.jsonl |
| 逐点和逐声明评分依据 / 汇总 | reviews.jsonl、results.jsonl / summary.json |
| 本轮报告 / 版本、配置、权重快照与哈希 / 云端回执 | report.html、README.md / manifest.json / cloud-verification.json |

原始大文件本地保留，同时以 `answers.zip`、`traces.zip`、`report.zip` 和材料包 `archive.zip` 无损提交；换电脑解压四包到原轮次目录即可离线查看，`checksums.sha256` 可核对内容。每轮使用新的run-id，不覆盖旧轮。**暂不创建跨轮次index**，等70开发/30封存测试完成后再汇总。

需要重新实际运行开发题时，在backend执行（会产生DeepSeek费用）：

```powershell
uv run python -m scripts.eval_round --run-id 新的唯一轮次名 --questions ../docs/eval/dev20/questions.jsonl
```

该入口只接受dev题，调用实际ChatService、单并发、无会话、独立空整答缓存，保存原始答案和过程；**不会自动完成逐声明评审和报告**。本轮标签由当前会话核验，旧可信总分复用已有函数。原 `poe eval-dev --system full` 直接调用pipeline，范围不同；跨轮比较必须保持相同系统范围、题集/标准/评审版本，并隔离缓存。
