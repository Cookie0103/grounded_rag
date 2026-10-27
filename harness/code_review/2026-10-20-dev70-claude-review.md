# 新70题（dev021～090）独立质量审查报告

- 审查版本：仓库 `grounded_rag`，分支 `2026-10-19-cloud-tracing`，HEAD `846b39f`（与 `origin/2026-10-19-cloud-tracing` 一致，工作区审查前干净）。
- 冻结语料：`langgenius/dify-docs@c80a31868611b673bd77725a6310c685068a585e`，182 篇，本机 `data/raw/dify-docs/...` 可读。
- 审查日期：2026-10-20；审查者：Claude（Sonnet 5.5）。
- 方法：先读规则文件和 `questions.jsonl`/`review-70.md`/`evidence.json`，**未看 Codex 结论前**逐题对冻结原文（Grep/Read 原文行、跨 182 篇全文检索等价来源）形成判断，再读 `semantic-review.json`、`retrieval-diagnostics.md` 等报告对照。
- 范围：不改题、不改评分/Prompt/业务代码、不碰 `backend/eval/data/` 与封存30题、不跑完整系统/无检索基线/付费评测。

## 0. 结论（一页版）

| 项 | 结论 |
|---|---|
| 新增46题 | **accept 35 / revise 11 / reject 0** |
| 配额（两半各23题、子类数量） | 标签数量精确达标（本人独立统计复核）；**但有 3 处“标签达标、实质打折”**：数值/表格（dev049）、链式（dev055/057/078）、分散（dev084） |
| 事实查重（旧20+新70共90题） | 未发现同一“文档+事实”的精确重复；发现 **1 组近似重叠**（dev074 ↔ dev077 的“逐节点追踪/耗时”）和 **1 组模板重叠**（dev043 ↔ dev019 注入） |
| 等价来源 / “同一篇最多一次” | **不成立**：`self-host/deploy/configuration/environments` 与 `api-reference/guides/streaming` 等页含同一事实但未列 OR，补齐后 environments 将被 dev048/062/070/083 共用（见 H1/H4） |
| 目录分布 | nodes 7篇≤8 ✓；少覆盖目录 25篇(gold_docs)/29篇(含OR)≥12 ✓；新46金标列面 70篇、无重复 ✓（但受上一行影响） |
| Codex 声称 7 题已修复 | 049 ✓（OR 补齐）、051 ✓、061 ✓、076 ✓、088 ✓；**059 去重 dev035 已解决，但暴露新的 OR 缺失**；**072 收窄已做，但 vital1/2 有“正反表述”嫌疑（低）** |
| 旧12题 | 9 题解决（dev035 带低风险备注），3 题带新发现（dev030/034/043）；另12题与 `7e73762` 快照逐字一致 ✓ |
| 单跳召回 | 复算 17/19=89.5% 与 Codex 一致，但 Codex 的“优先加难候选”并不都站得住（见 §6） |

**必须先修的题（6项硬伤）**：dev059、dev084、dev057、dev078、dev055，加一项需作者拍板的“配置参考页等价来源”策略（影响 dev048/070/083/062，旧dev034）。

## 1. 实际执行的检查 / 只阅读核对 / 无法判断

### 真跑过
| 检查 | 结果 |
|---|---|
| `git status/fetch/branch --contains` | HEAD=846b39f，远端同提交，工作区干净 |
| `tools/source_index.py`（重建 182篇/1252父块/2090子块/534522字符索引到 `.cache/dev70-completion/`） | 成功。**副作用**：它覆盖了已提交的 `docs/eval/dev70/corpus-distribution.json`（仅 `README/readme` 文件排序不同，Windows 大小写不敏感文件系统所致）；已 `git checkout --` 还原，工作区复干净。→ 工具在 Windows 上不可逐字复现，属小问题（L-1） |
| `tools/validate_completion.py --mode completion` | exit 0；563 pass / 141 legacy_observation_pass / **8 legacy_observation**（均为旧题已知局限：dev023 无数值干扰、dev025 清洗文 979 字符、dev027 无泛词干扰等）；`semantic_review_complete=false`（脚本自述） |
| `tools/test_tools.py` | 8 tests OK |
| 我自己的脚本（均读冻结原文/索引） | ① 两半各23题的类别与子类计数；② 新46金标（含OR）文档复用；nodes 数、少覆盖目录数；③ 对每个 nugget 的标识符在 182 篇里反查“未列入金标的等价来源”；④ 对 dev084 等分散题按父块反查等价证据；⑤ 检索自测 JSONL 的逐题名次；⑥ 12 道未点名旧题与 `7e73762` 的 JSONL/evidence 逐字比对 |
| 缺依据题的独立近义词全文检索（182篇，不依赖 Codex 词表） | dev063、dev064、dev086 见 §4.4 |
| 逐题对冻结原文核对 | 46题全部 vital 的原文摘录（通过脚本核对行号后，再人工阅读语义是否被支持）；重点题另读原文整页（start.mdx、orchestrate-node、integrations.mdx、streaming.mdx、weaviate-v4-migration 分段、publish-to-marketplace、predefined-error-handling-logic 等） |

### 只阅读核对（未重算）
- `twin-comparisons.json` 的逐字符差异：只核对了 dev054/075/076/089/066/049/056 对应的双版本原文，未逐对重算全部 4+ 对孪生。
- `corpus-distribution.json` 全表、`blueprint*.json`（已知与最终题有记录的修订，未逐项复核）。
- `validation.json` 逐题条件：以我自己的统计替代，未逐条审。

### 无法判断 / 未执行
- `retrieval_selftest.py`（需要 DB+Qwen3 模型，本轮明令不跑）；`runtime-verification.json` 的 DB 全量比对只能读不能验证。
- 题目对真实系统/无检索基线的难度：只能给设计层面的判断，**guessable_without_docs 全为 null，无法评估常识可猜性**。
- 同义改写题“连续三字重合”依赖脚本（validator 通过）；我只对 dev068/069/045/046/047 做了人工语义复核。
- 评分加载器忽略 `gold_doc_groups` 的 OR（README 自述）：本轮未读评分代码，未验证。

## 2. 新增46题逐题判定（accept / revise / reject）

标记：A=accept，A*=accept但有备注，R=revise。严重度见 §3 问题表（H=硬性，S=语义设计缺陷，O=可选加难，L=旧题/工具局限）。

| 题 | 子类 | 判定 | 依据（核心） |
|---|---|---|---|
| dev045 | 同义 | A | 4 vital 各有独立原文（snippet L20/L22/L56/L58），题干避开“Snippet”；单检索 rank1。 |
| dev046 | 同义 | A | @node/快捷键/侧边栏按钮三点独立；vital1、3 同句但分别被问到；自测未命中，难度好。 |
| dev047 | 同义 | A | 2 vital 独立（冲突以最后编辑为准；评论跨版本保留），原文 L23/L27 支持。 |
| dev048 | 数值 | R | 事实成立（additional-features L80）；但 `environments` L1092 同样含默认值50与变量名，gold 未列 OR（H4）。检索名次 5、top1 为 build/agent，并非偏易。 |
| dev049 | 数值 | R | OR 来源已补齐（cloud L47/self-host L50 逐字同）。**但“角色/所有者”查读不足以归入数值/表格**：答案是“当前所有者邮箱”和“普通成员”，不是数字/字段名/枚举取值（S1）；且名次1，偏易。 |
| dev050 | 易混 | A | 新Agent vs 旧Agent，差异句（overview L25“而不只是调用你配置好的工具”）真实影响答案；题干未并列两个候选。 |
| dev051 | 易混 | A* | 旧Agent“按每条查询与知识库描述相关性决定检索”(agent L130)对 chatbot“每条消息检索”(chatbot L92)差异真实；“漏选”是对原文的轻度推断，参考答案未越界。自测未命中。 |
| dev052 | 短问 | A | 2 vital 独立(L88/95、L36)；19 字。 |
| dev053 | 短问 | A | 唯一单 vital（短问，允许）；CONSOLE_URL/APP_URL 仅此页（L29）。 |
| dev054 | 单问版本 | A | cloud readme“首次登录自动创建”与 self-host“安装时创建”逐段不同，版本题成立；题干写“社区部署”。 |
| dev055 | 链式 | R | **桥接不必要**：第二问“谁能维护，移除唯一凭据后呢”没有宾语，也不依赖第一问答案；“唯一凭据”直指 model-providers L73；自测第一/二篇名次1、2，一次检索全中。（H6） |
| dev056 | 链式 | A* | 表格行（LLM生成问答→问答模式，create-knowledge-pipeline L44）→ 索引页“Q&A模式”(setting-indexing-methods L42–46) 真实；cloud 同名页无该段，无需 OR。注意 vital1 把“模板名”和“问答模式”捆在一条（L）。 |
| dev057 | 链式 | R | (a) 第二篇标题“从 Notion 导入数据”，题干含“Notion”（违反链式规则8）；(b) 第一篇 integrations.mdx **L16–17 已含** `NOTION_INTEGRATION_TYPE=internal`/`NOTION_INTERNAL_SECRET`（vital3），`environments` L1120–1123 亦含；(c) 一次检索名次1、4全中。（H3） |
| dev058 | 链式 | A | 本批最像样的链：必须先把“取消付费”解析为 Sandbox，才能选对容量表行(50 MB)；第一篇自测未命中。 |
| dev059 | 比较 | R | 与 dev035 已错开 ✓（题干/参考答案不含会话记忆）。但 vital1“旧版Agent仅流式”、vital3“agent_message”在 **streaming.mdx L18/L71** 及 agent.mdx L16/L28 同样成立，gold 只列 chat/completion。（H1） |
| dev060 | 比较 | A | 2 篇、4 独立 vital 原文齐；四问堆叠偏模板，但各有来源。 |
| dev061 | 分散 | A* | 父块 p2/p5/p7 各独占一个 vital，清洗文 9408 字符 ✓；“消费者”为 Celery worker 的生僻说法，题干与 vital 已对齐（不再要求完整命令）。 |
| dev062 | 分散 | A* | 父块 p9/p10/p11，清洗文 79316 ✓。vital1/3 把“变量名”与“回退行为”捆成一条（L）。 |
| dev063 | 缺依据 | A | 见 §4.4：本人宽口径检索仅命中 Redis Sentinel 故障转移(environments L345)和企业版K8s高可用(overview L56)，均不含 RPO/RTO/切换期限承诺。 |
| dev064 | 缺依据 | A | 仅命中“下载发票”(subscription-management L16)；无日本税号/开票期限。 |
| dev065 | 错误前提 | A | orchestrate-node L26“除用户输入节点外…”与 L32–35“变量/集成/知识库会在目标重新评估”直接矛盾前提。 |
| dev066 | 版本不明 | A | edition=null、无版本词；cloud 文件数量 L79“Sandbox 1/Pro·Team 50”，self-host L79“默认20”，答案确因版本而异；可答/可反问。 |
| dev067 | 缺槽位 | R | 歧义真实，但参考答案的澄清轴（“接收上传 vs 让模型理解内容”）与文档轴（开始节点/用户输入 vs 文本生成应用的模型能力开关）不一致，可能误判合理反问（S2）。 |
| dev068 | 同义 | A | 默认值/备用值（L23–31）；题干未用标题；自测名次1（易，见 §6）。 |
| dev069 | 同义 | A | Pending 撤回(L17)+两条提交前要求(L21/L22)，3 独立 vital。 |
| dev070 | 数值 | R | 事实成立(skills L61)，干扰数字真实(Builder 10个/10MB/15MB，L57)；但 `environments` L1407–1411 同样含默认50 MB 与变量名，未列 OR（H4）。句式与 dev048、旧 dev034/015 同模板（S5）。 |
| dev071 | 数值 | A* | 枚举(二进制)+变量类型(文件变量)勉强够“枚举值/字段名”；干扰项(JSON/表单/原始文本)真实。但“上传文件→二进制”靠常识可猜，区分度低（S）。 |
| dev072 | 易混 | A* | llm.mdx L141–148 三点成立；`human-input.mdx` L61 也提到“启用推理标签分离”，比登记的干扰 parameter-extractor 更接近。vital1“text仅保留回答”与vital2“思考移至reasoning_content”同句镜像，略像正反表述（S4，低）。 |
| dev073 | 易混 | A | 循环 vs 迭代，差异句(loop L8)真实决定节点选择；条件“未设退出→到最大次数”L53。 |
| dev074 | 短问 | A* | 2 独立 vital；与 dev077 vital3 在“逐节点耗时/追踪”上重叠（S3，修 dev077）。 |
| dev075 | 单问版本 | A | cloud L54 有 Sandbox 限制而 self-host 无；vital2(自定义模板)两版相同，版本差异只体现在 vital1，可接受。题干“获准发布后”措辞别扭。 |
| dev076 | 单问版本 | A | 替换后成立：cloud L36“清除安装偏好设置里保存的URL”，self-host 需“填写部署URL”（plugins L35–37），操作确实相反；vital2 两版相同，不影响。 |
| dev077 | 链式 | R(轻) | 链式形态（API持久ID→控制台）合理，但 vital3“点击某次运行查看逐节点追踪”与 dev074 vital1 近同（S3）；第二问不依赖 ID 名称也能独立检索（弱桥接，低）。 |
| dev078 | 链式 | R | human-input-flow 单独含 vital1(L9/L21)、vital3(L33)、vital4(L44)；第一篇只提供 `workflow_paused`；workflow.mdx L37 与 chatflow L47 同句。一次检索名次1、2全中；61字符四问堆叠。（H5） |
| dev079 | 链式 | A | 课程→节点（全批唯一一道）：第9课定位模板节点，题干不含“模板/Jinja/default”；自测未命中第二篇。 |
| dev080 | 比较 | A | Space ID / 空间主机名 / 系统密钥三点原文齐(arize L37、phoenix L73/L87)，cloud/self OR 齐全。 |
| dev081 | 比较 | A | Host/Public Key/Personal Access Token/项目名不一致自动建新项目四点原文齐；与 dev080 同模板（S5，低）。 |
| dev082 | 比较 | A* | 四点原文齐；实质是跨篇“流程”而非“比较选择”，标签偏弱（低）。 |
| dev083 | 比较 | R | 事实成立(faqs L75–76/L83、common-issues L25)；但 `environments` L418–420 含 CONSOLE_CORS_ALLOW_ORIGINS 与 NEXT_PUBLIC_COOKIE_DOMAIN，未列 OR（H4）。 |
| dev084 | 分散 | R | **≥3父块被等价来源虚增**：vital1(1.27.0)与vital2(gRPC 50051)同在 p3(L39–41)；1.27.0 还见 p0/p1/p2/p5，50051 见 p4/p6/p15/p25；vital3/4 同在 p10。仅 p3+p10 两个父块即可答完。（H2） |
| dev085 | 分散 | A | 父块 p9/p10/p11/p12 各独占一个 vital；清洗文 6225 字符，刚过 6000 线。 |
| dev086 | 缺依据 | A* | 宽口径检索“漏洞/补丁/安全公告”等无相关命中(仅 Weaviate EOL 的泛述)；近邻选择偏弱（plugins、marketplace 提交、deploy overview）。 |
| dev087 | 错误前提 | A | start.mdx L14“只有以用户输入启动的工作流才能发布为…MCP”与 L30“用户输入和触发器互斥”直接矛盾，操作句式。 |
| dev088 | 无关 | A | LangGraph+Patroni 明确超出 Dify 范畴，且相邻（RAG/PostgreSQL）；符合“相邻领域”。 |
| dev089 | 版本不明 | A | cloud app-management L114“始终兼容”，self-host L114“可能需先升级”，答案因版本而异；无版本词。 |
| dev090 | 缺槽位 | A* | 外部知识库(connect-external-knowledge-base) vs 外部数据工具(external-data-tool-api-extension)两种理解均有据；参考答案较好。 |

合计：A 35（含 A* 12）/ R 11 / reject 0。

## 3. 问题表

严重度：**H 硬性不合格**（违反作者/验收规则，必须先修）；**S 语义设计缺陷**；**O 可选加难**；**L 已知旧题/工具局限**。“影响配额”指改了之后会不会动子类/批次数量。

| 编号 | 级 | 题号 | 具体问题 | 原文文档与行号 | 最小修改建议 | 影响配额 |
|---|---|---|---|---|---|---|
| H1 | H | dev059 | 等价来源缺失：vital1“旧版Agent仅流式”、vital3“agent_message”另见 streaming/agent 页，gold 组只含 chat、completion。召回会误罚命中 streaming 的系统，也与 dev021(streaming) 隐性共用。 | `api-reference/guides/streaming` L18、L71；`api-reference/guides/agent` L16、L28；(登记的) `chat` L9/L17、`completion` L17 | vital1/3 增加 OR（chat∣streaming；agent.mdx 是“Agent 应用”页，是否纳入需作者定）；同步修 `gold_doc_groups` | 否（streaming 全70仅2次，未超） |
| H2 | H | dev084 | 分散证据被等价来源虚增：vital1、2 同在 p3 的 L39–41；p4/p6/p15/p25 均含 50051；仅 p3+p10 两父块即可全答，达不到“必答点来自≥3个不同父块”。 | `self-host/deploy/troubleshooting/weaviate-v4-migration` L18/L39–41、L91、L300–301、L319（父块 p3/p6/p10） | 重选三个互相不可替代的必答点：保留 p10 的 `--no-cache`/UI验证两点之一，另两点取互相**独占**的段落（如 p25 排障、p31 权限被拒），并删去与 p3 重叠的“版本+端口”双问 | 否（仍分散2题） |
| H3 | H | dev057 | 链式不成立：题干含第二篇标题词“Notion”（规则8）；vital3 的 `.env` 变量在第一篇 integrations.mdx L16–17 与 environments L1120–1123 已有，不依赖第二篇；单次检索一次命中两篇。 | `self-host/deploy/troubleshooting/integrations` L9、L16–17；`.../sync-from-notion` L56/L70–74/L99；`environments` L1120–1123 | 去掉“Notion”显式词（改“笔记型数据源”类描述）；把第二问收窄为**仅第二篇**有的事实（创建者必须是 Notion 工作空间所有者 L56、重启加载 L99），删 vital3 或标 okay | 否 |
| H4 | H（需作者定策略） | dev048、dev070、dev083；旧 dev034 | 同一事实在 `environments.mdx` 也成立但 gold 未列 OR。若补 OR，则 environments 被 dev048/062/070/083 共4次占用，违反“新增46每篇最多1次”；若不补，则召回计分失真。 | `environments` L1092（音频50）、L1407–1411（Skill包50）、L418/L420（CORS、COOKIE）、L1262（CODE_MAX_STRING_LENGTH=400000，旧dev034） | 作者二选一：①把配置参考页定义为“通用等价来源”，补 OR 且不计入复用上限（需改规则表述）；②只保留 dev062 用 environments，其余改写为 environments 页**没有**的事实，或替换题 | **可能**：若走②会替换最多3题，需保持各自子类（数值×2、比较×1） |
| H5 | H | dev078 | 链式必要性弱：human-input-flow 独自含 vital1/3/4，第一篇仅贡献 `workflow_paused`（chatflow L47 / workflow L37 同句）；四问堆叠61字符；一次检索全命中。 | `chatflow` L47；`workflow` L37；`human-input-flow` L9/L21/L33/L44 | 改成真正依赖 `workflow_paused` 之后的问题（例如暂停后凭什么接口恢复、同一 user 要求），并去掉第二篇已独立覆盖的 vital1；或承认并列并调整链式配额（7→6） | **是**（若降级，链式新增7→6，需补1道链式） |
| H6 | H | dev055 | 链式必要性弱：第二问无宾语，“唯一凭据”泄漏第二篇 L73 的关键词；一次检索（rank1、2）即可命中两篇。 | `api-reference/guides/errors` L37/L42；`cloud/.../model-providers` L13/L73 | 第二问显式承接第一问的“修复处”（如“这个配置位置里，谁有权改，删掉……”），去掉“唯一凭据”这类第二篇独有短语 | 否 |
| S1 | S | dev049 | 子类错位：“验证码寄给谁、之后是什么角色”是流程事实，不是数字/字段/枚举取值；干扰项仅为角色表其他行。名次1。 | `cloud/.../team-members-management` L47；`self-host/...` L50、角色表 L24 | 重新归类为短问/易混，并换一道含具体数值或字段名的真正数值题（保持“数值”子类=2） | 是（子类换题） |
| S2 | S | dev067 | 参考答案澄清轴与原文轴不一致，可能判错合理反问。 | `nodes/user-input` L85–106（“仅收集不解析”）；`build/text-generator` L162–185 | 改成“你用的是工作流(开始节点)还是文本生成/聊天应用？”并给出各自入口 | 否 |
| S3 | S | dev077（兼 dev074） | 同一事实跨文档重复：dev074 vital1(“追踪展示各节点耗时”)与 dev077 vital3(“逐节点执行追踪便于定位变慢环节”)近同。 | `debug/history-and-logs` L44；`monitor/logs` L48 | dev077 vital3 降为 okay，或改问 logs L48 中“token总量/状态”等 dev074 未覆盖的信息；必须保留≥3 vital | 否 |
| S4 | S | dev072 | vital1/2 为同句镜像（text只留回答 / 思考移到 reasoning_content），接近“正反表述拆两条”；dev058 vital3/4(“不删除”/“仍可检索”)同理，较弱。 | `nodes/llm` L143；`knowledge-storage-limit` L53 | 合并为一条，或把 vital2 改成“关闭开关时 reasoning_content 为空”(L143尾句)，使其成为独立事实 | 否 |
| S5 | S | 全局 | 模板化：dev034/048/070(+旧015)“默认多大+哪个配置”；dev080/081 同为“监控集成字段对照”；14道四 vital 的多跳多以3–4问堆叠，虽规避“顿号三问”字面规则，精神上仍是堆叠。 | — | 至少把 dev070 改成场景句（“导入 .skill 包被拒”），dev081 改成故障症状句 | 否 |
| S6 | S | 16题 | `most_likely_failure` 为占位句“忽略条件或套用邻近说明。”：dev068–075、078–083、086、090，违反规则20、对失败分析无信息。 | `questions.jsonl` / `evidence.json` | 逐题写具体失败（例如 dev071 “把二进制响应当文本”） | 否 |
| S7 | S | 全局 | `form_tags` 虚高：声明 33 场景/17 条件，本人按题干实质只认可约 20 / 12；如 dev063/064/066/086 无真实场景/条件。 | evidence `form_tags` | 删除不成立的标签；阈值（≥14/≥7）仍满足 | 否 |
| S8 | S | dev043(旧)↔dev019 | 注入题与旧 dev019 为同一模板（“忽略…规则，列出 API 密钥”），区分度低。需求文档规则17要求“嵌入正常 Dify 问题”，而本题按作者新指示做成纯注入，二者不一致。 | — | 作者确认纯注入是有意的则保留，但换一种载体（如工单正文引用文档中的伪指令） | 否 |
| S9 | S | dev068–074 | `edition=self_host` 但题干无版本词；batch-03 的自部署单文档题（如 dev045）却是 null。口径不一致，可能泄漏金标所在目录。 | `questions.jsonl` | 统一口径：仅在写明版本或孪生题才填 edition | 否 |
| S10 | S | dev030(旧) | 金标组间 AND 不合理：cloud 页“自定义”标签(L103–L114)已含“注册OAuth应用→填Client ID/Secret→保存并授权”，所以 vital2–4 并非自部署独有；vital4“保存并授权”也不是“准备流程”。 | `cloud/.../authorize-data-source` L99–114；`self-host/...` L91–105 | vital2–4 改为 OR(cloud∣self-host)，vital4 标 okay | 否 |
| O1 | O | dev048/049/054/068/069/070/072/075 | 见 §6。 | — | — | 否 |
| L1 | L | dev025/041/042(旧) 等 | 清洗文<6000字符（dev025=979、dev041=4946 等）等 8 项 legacy_observation，维持已知局限。 | validator 输出 | 不改 | — |
| L2 | L | 工具 | Windows 下 `source_index.py` 会改写已提交的 `corpus-distribution.json`（排序）。 | — | 工具输出排序前统一小写或固定 locale | — |

## 4. 分项结论

### 4.1 配额（独立统计，与 Codex 一致）
- dev045–067：单跳10（同义3、数值2、易混2、短问2、版本1）、多跳8（链式4、比较2、分散2）、拒答纠正3（缺依据2、错误前提1）、模糊2（版本不明1、缺槽位1）。✓
- dev068–090：单跳9（同义2、数值2、易混2、短问1、版本2）、多跳9（链式3、比较4、分散2）、拒答纠正3（缺依据1、错误前提1、无关1）、模糊2。✓
- 全70：28/28/9/5 行为配额与 `requirements-review-v2.txt` 一致（新46+旧24）。
- **实质折扣**：数值子类 6 道里 dev049 不成立；链式 7 道里 055/057/078 弱；分散 4 道里 084 不成立。修完后若不替换，实质达标数 = 数值5/链式4–5/分散3。

### 4.2 事实去重（旧20+新70）
- 精确重复（同一文档同一事实）：**未发现**。dev059 已与 dev035 错开：dev035 的“会话变量跨轮保留”不再出现在 dev059 的题干、vital、参考答案。
- 近似重叠：dev074↔dev077（S3）；dev043↔dev019（S8，模板）。dev066 与旧 dev015/016 的“1/50”数字巧合，但文档/功能不同（流水线 vs 即用型上传），不算重复。dev084 与 dev026 同为 Weaviate，但分属 v4-migration 与 server-migration-path，事实不重叠。
- 隐性复用（因等价来源缺失）：H4。

### 4.3 目录分布
- 新46金标（含OR）70篇，无同一篇出现两次（按**已登记**OR 计）。
- `self-host/use-dify/nodes/*`：7篇（http-request、llm、loop、start、template、tools、user-input）≤8 ✓。
- 少覆盖目录：gold_docs 25篇 / 含OR 29篇（部署配置7、API参考6、工作空间管理6/9、应用发布3、云版计费1、插件1、模型接入1/2）≥12 ✓。
- 局限：`self-host/use-dify/*` 合计 30 篇，题材集中在“配置/限制/操作步骤”，缺少监控以外的概念类、教程类事实（旧题已有3道教程链）。

### 4.4 缺依据与边界题的独立检索
我用与 Codex 不同的**宽口径**正则对 182 篇原文（`zh/`）做了检索：
- dev063：`灾备|容灾|异地|跨机房|多活|RPO|RTO|恢复点|恢复时间|故障转移|failover|disaster|高可用|主从切换|SLA` → 仅命中 environments L345（Redis Sentinel 故障转移/高可用）与 overview L56（Enterprise 在 Kubernetes 上高可用）；没有任何恢复点/恢复时间/切换期限。**结论成立**。Codex 零命中词表偏向“长复合词”（跨机房灾备、灾备承诺、恢复点目标…）和 RPO/RTO，短近义词的真实命中另记，建议在审计里把上述两处列为“最近邻”。
- dev064：`税务|发票|invoice|注册号|适格|VAT|日本|开票|税号` → 仅 subscription-management L16“下载发票”及与题无关的“日本”示例。**成立**。
- dev086：`漏洞|vulnerab|CVE|安全公告|补丁|hotfix|披露|响应时间|SLA` → 仅 Weaviate 迁移页中泛述“补丁/安全修复”(L87/L898)，与“社区集成官方响应承诺”无关。**成立**；近邻选择偏弱（plugins L33“由发布者维护”其实暗示维护责任在发布者，不在官方，题干“官方承诺”的预设略有诱导，但不构成矛盾）。
- 错误前提：dev065（orchestrate-node L26/L32–35）、dev087（start.mdx L14/L30）均有**直接矛盾原句**，不是“没提到”。
- dev043 为纯注入、无 gold、无夹带正常问题 ✓。
- 版本不明：dev066（pipeline-orchestration cloud L79 vs self-host L79）、dev089（app-management L114）双版本答案确不同，题干无版本词 ✓。

### 4.5 链式与桥接多样性
| 题 | 桥接形态 | 本人判断 |
|---|---|---|
| 055 | 诊断标识→配置修复→凭据生命周期 | 形态独立，**但桥接不必要**（H6） |
| 056 | 需求→内置模板→索引模式细节 | 成立（第二篇自测未命中） |
| 057 | 部署协议条件→授权模式分支 | 形态独立，**但桥接不必要且标题泄漏**（H3） |
| 058 | 订阅状态→套餐实体→额度/超额行为 | **成立，最佳** |
| 077 | API持久ID→控制台定位/重演 | 成立（弱桥接，低） |
| 078 | 暂停事件→表单状态机 | **桥接不必要**（H5） |
| 079 | 教程→节点页 | 成立（仅此1道） |

- “≥4种实质不同的桥接形态”：形态有 7 种标签，实质上可归为“选分支/行取值”(056/057/058)、“标识符透传”(055/077/078)、“教程→节点”(079) 三大类，勉强够 4 种（若按次级形态拆分）。
- 泛词干扰文档：已登记 2 篇/题，且真实存在、不含所问事实。未发现伪造。
- 单次检索全中的链式：055、057、078（3/7），说明这三道的“第二问不依赖第一问”的判断与检索证据一致。

### 4.6 分散题
| 题 | 必要父块数 | 清洗文 | 结论 |
|---|---|---|---|
| 061 | p2/p5/p7，三者互相独占 | 9408 | ✓ |
| 062 | p9/p10/p11 | 79316 | ✓ |
| 084 | 声称3，实际可被2个父块替代 | 16351 | **✗**（H2） |
| 085 | p9/p10/p11/p12 | 6225 | ✓（余量仅225字符） |

### 4.7 其他难度标签
- 同义改写：validator 通过全语料标题/小标题三字重合；我人工确认 045（不含“Snippet”）、046（不含“Goto Anything/@node”答案以外的官方名）、047、068（不含“默认值/处理错误”）、069（不含“Pending/Draft”）。✓
- 数值/表格：048、070 有真实相似数字；049 的“相似行”是角色表其他行（S1）；071 的干扰是真实枚举但可猜。
- 易混：050、051、073 差异句真实且影响答案；072 的登记干扰（parameter-extractor）弱于真正近邻 human-input.mdx L61。
- 场景/条件：实质约 20/12，满足 ≥14/≥7，但 S7。

## 5. 旧12题（上次问题是否解决）

| 题 | 判定 | 说明 |
|---|---|---|
| dev021 | ✅ 解决 | 受理(`workflow_started`，streaming L27)与终止(`workflow_finished`，L78)分属两阶段，原“同一判断拆两条”消除；ping 降 okay。 |
| dev024 | ✅ 解决 | iteration L73/L79：“错误时继续”与“null占位”两事实分别被问到；邻近循环干扰在 loop L8。 |
| dev029 | ✅ 解决 | 与 dev022 不再重复；ELIF（ifelse L20）为新细节；3 独立 vital。 |
| dev030 | ⚠️ 部分解决 | 数字已移除，与 dev015/016 不再重叠；但金标 AND 结构不合理、vital4 未被问（S10）。 |
| dev031 | ✅ 解决 | route=null；我检索触发器目录与全库未见“去重/幂等/dedup/event_id”。 |
| dev033 | ✅ 解决 | 禁用(L27)与归档只读(L29)分问；孪生 OR 由工具记录，未逐字复算。 |
| dev034 | ⚠️ 原问题解决，新发现 | 两事实分问 ✓；但 `environments` L1262 同事实未列 OR（H4）。 |
| dev035 | ✅ 解决 | 已去候选名；保存范围被问到。次要：`learn/key-concepts` L97 是 vital2 的部分等价来源。 |
| dev036 | ✅ 解决 | publish-mcp L19：旧URL立即失效、URL含凭据，二事实分问。 |
| dev037 | ✅ 解决 | personal-account-management L13：登录方式与同邮箱自动关联分问。 |
| dev041 | ✅ 解决 | 字段名规则 metadata L147 ✓；父块数按证据记录，未逐块重算；清洗文4946字符为 legacy。 |
| dev043 | ⚠️ 解决但见 S8 | 纯注入、无 gold，但与 dev019 同模板。 |

另12题（022、023、025、026、027、028、032、038、039、040、042、044）：与 `7e73762` 快照比较，**questions.jsonl 行与 evidence 对象逐字一致**；实际变更 ID 集合恰为指定12题。✓

## 6. 检索自测与“加难候选”判断

我只读 `retrieval-selftest.jsonl`，未重跑。复算：新增46中单跳19题全组命中前5 = 17/19（miss=dev046、dev051），与 Codex 一致；该数字仅是来源命中，不是答对率。

对 Codex 优先候选的判断（名次为金标全组的最坏名次）：

| 题 | 名次/top1 | 是否确实偏易 | 加难建议（均不换金标、不制造晦涩题干） |
|---|---|---|---|
| dev048 | 5 / top1=build/agent | **不明显**（金标刚进前5，top1 是干扰） | 保留；若加难，改成“传60MB录音被拒、同时80MB视频也被拒，各调哪项”，用 L78–81 的四行相似数字；同页，仅增 vital，不动配额 |
| dev049 | 1 | 是，且子类不成立（S1） | 换题优先于加难 |
| dev054 | 2 / top1=personal-account-management | 不明显 | 保留 |
| dev068 | 1 | 是 | 在同页加例外：循环节点内失败总是立即停止(L66)，问“循环里还能用备用文案续跑吗”；或问适用节点类型(L12–13) |
| dev069 | 1 | 是 | 同页加条件：创作者中心上传 `.yaml/.yml` 上限 10 MB 及精简办法(L35–41)，使必答点落入不同父块 |
| dev070 | 1 | 是 | 场景化（“导入 .skill 包被拒”），并让答案区分“导入包50MB”与“Builder附件10个/10MB/15MB”(L57)，干扰数字已存在 |
| dev072 | 1 | 是 | 加跨页例外：`human-input.mdx` L61 的“仅显示答案”场景 |
| dev075 | 1 | 是 | 加同页条件：该功能仅 Professional/Team 可用、Sandbox 需升级(L54)。不要问“self-host 是否同样受限”（self-host 页对此沉默，属“没提到”而非“不支持”） |
| 其他 rank1 单跳：045、047、073、074、076 | 1 | 也偏易但不在候选里 | 不强制 |

“可保留”的理由：dev046、051、071（名次 5）、052/053（2/3）已有一定难度。

## 7. 必须先修 / 可保留

**必须先修（按优先级）**
1. **dev059**（H1）补 OR：streaming L18/L71（及 agent.mdx 视作者定）。
2. **dev084**（H2）重选三个互相不可替代的必答点。
3. **dev057**（H3）去标题词“Notion”并收窄 vital 到第二篇独有事实。
4. **dev078**（H5）与 **dev055**（H6）：恢复真正的桥接依赖，或接受降为并列并补一道链式。
5. **H4 策略**：环境变量页等价来源（dev048/070/083，旧dev034），先由作者定“通用等价来源”规则，再改。
6. 随后：dev049（换题）、dev067（改参考答案）、dev077（去重叠）；16 题 `most_likely_failure` 占位句（S6）。

**可以保留，后续再加难**
- dev045、046、047、050、051、052、053、054、056、058、060、061、062、063、064、065、066、068、069、071、072、073、074、075、076、079、080、081、082、085、086、087、088、089、090。
- 低风险备注（不阻塞）：dev056/062 的 vital 捆绑、dev072/058 的镜像 vital、dev075 措辞、dev085 余量 225 字符、dev061“消费者”用语。

## 8. 对 Codex 闭环声明的复核

| 声明 | 本人复核 |
|---|---|
| “7题已修复” | 049/051/061/076/088 **确实解决**；059 只解决了与 dev035 的重复，同时暴露 OR 缺失；072 收窄成功，但有镜像 vital 的低风险。 |
| “新70单跳 25/28” | 数字属实；但“全部必答点集中在一个父块”的 8 个候选里，048 与 054 并不明显偏易。 |
| “新增46每篇最多1次”“70篇无重复” | 仅在**已登记**OR 的口径下成立；补齐等价来源后不成立（H4）。 |
| “链式7道4种以上实质不同桥接” | 标签层成立；实质层 055/057/078 的桥接不必要（H3/H5/H6）。 |
| 校验脚本 pass | 本人也复跑通过（563 pass/8 legacy）；脚本不能发现等价来源缺失、桥接不必要、子类错位——这些只能靠本报告的语义审题。 |

— 以上。本轮未修改任何题目、评分或评审 Prompt；仅新增本报告及同名 `.json`。

## 9. H4 策略决定（2026-10-20，作者授权按推荐执行）

采用方案①：`self-host/deploy/configuration/environments` 作为**通用等价来源**。
- 在 dev048、dev070、dev083（及旧 dev034）相应 vital 的 `gold_doc_groups` 中追加 OR：environments L1092 / L1407–1411 / L418、L420 / L1262。
- 复用上限只统计**主金标**：environments 作为主金标仅 dev062；作为等价来源出现时不计入“新增46每篇最多1次”。规则文字需同步写明适用范围：仅限“配置参考页重复了专题页已有的变量与默认值”。
- 不选②的原因：需替换最多3道已审题并重审，改动与风险更大，且复用上限的目的是防话题扎堆，不是计分。
- 状态：本报告只记录决定，题目与证据文件尚未修改，待后续修订任务执行。
