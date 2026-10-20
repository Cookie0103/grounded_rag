# 开发70题复审、新30题测试稿审题与正式评测就绪性

- 审查对象：分支 `2026-10-20-dataset-repair`，提交 `a029657`、`c6194f9`（工作区审查前后均干净）；冻结语料 `dify-docs@c80a318…`，182 篇。
- 审查者：Claude（Sonnet 5.5），2026-10-20。作者授权读取仓库外新编 30 题（`test30-review-2026-10-20`），未读任何其他封存测试，未据测试题调系统。
- 本报告**不引用 30 题题干与参考答案**（仓库内不应出现测试题文本），只用 ID、文档与行号。
- 未改题目、评分规则、评审 Prompt、业务代码；未运行检索、完整系统、无检索基线或付费评测；未覆盖任何历史运行档案。

## 0. 结论

**现在还不能开始正式评测。** 题集本身基本可冻结（70 题修 2 处小问题，30 题必须修 1 题、建议修 2 题），但评测接线和评审校准有阻塞项。最小阻塞清单见 §5。

| 对象 | accept | revise | reject |
|---|---:|---:|---:|
| 开发题 dev021～090 | 68 | 2（dev030、dev084） | 0 |
| 新30题 test001～030 | 27 | 3（test029 必修；test017、test018 建议修） | 0 |

## 1. 实际执行 / 只读核对 / 未能判断

**真跑过**：`git status/fetch`；`validate_completion.py --mode completion`（0 硬失败；563 pass、141 legacy_observation_pass、8 legacy_observation）；`test_tools.py` 9 tests OK；用项目自己的 `eval.dataset.load_questions/validate_questions` 读入两份题集（dev 70 题 0 错误 0 提醒；test 30 题 0 错误、1 条提醒 test009）；对 70+30 题逐个检查“评审实际能看到的金标文本（`gold_document_text` 清洗后截前 12000 字符）是否包含每个必答点的至少一条证据”（全部满足）；对每个必答点标识符在 182 篇里反查未列入金标的等价来源；用索引核对 4 道分散题的父块；对 40 道被改动的开发题逐题重读冻结原文；对 30 题逐条核对证据摘录；缺依据/无关题用宽口径正则复检；通读 `backend/eval/{dataset,scoring,judge,metrics,evaluate,attribution,report,runner,systems,observed}.py`、`scripts/eval_run.py`、`scripts/eval_round.py`、`metrics-v1.md`、`runbook.md`。

**只读**：`twin-comparisons.json`、各 `validation.json`、`review-30.md`（抽读）。

**无法判断**：真实检索/生成难度；`guessable_without_docs` 全 null，常识可猜性只能给设计层判断；E/F/C 评审质量（尚未实现）；评审与人工的一致率（未校准）。

## 2. 开发70题

### 2.1 上一份报告问题的复核（逐项重读原文，不沿用旧 accept）

| 题 | 上次问题 | 现状 | 判定 |
|---|---|---|---|
| dev059 | gold 缺等价来源 | 组 1 已含 `chat`、`streaming`（L18/L71）；与 dev035 已错开 | ✅ |
| dev084 | ≥3 父块被虚增 | 现必答点：版本(p0–p5 任一)、`WEAVIATE_GRPC_ENDPOINT` 格式(仅 p15)、`--no-cache`(p10/p11/p31)；任一父块不同时含两点，**最少 3 父块成立** | ✅，但见 S-1 |
| dev057 | 标题词泄漏、第一篇已含变量 | 题干不再含“Notion”；H4 仅作用于 `environments` L1120–1123 与首跳文档对 **vital 1（internal 值 + 本地部署建议）** 的重述，vital 2（Secrets→Show，L64）、vital 3（重启，L99）只在第二篇。`integrations` 未被当作第二篇替代 | ✅ 符合已批准的窄范围 |
| dev083 | 担心整题 OR 放宽 | 题级 `gold_doc_groups` 仍是 `[[faqs],[common-issues]]`；`environments` 只出现在逐点 OR（COOKIE_DOMAIN L419、NEXT_PUBLIC_COOKIE_DOMAIN L420 确为同一变量说明）。vital 3（401 排查）虽也列了 environments，但另一组强制 common-issues，实际未放宽 | ✅ |
| dev055 | 桥接不必要 | 改为“修复入口→沿入口谁能维护→手动添入条目删最后一把密钥”；第二问以“沿这个入口”承接，去掉“唯一” | ✅（第二篇仍可被直接检索到，但回答依赖第一问的“模型配置”入口，可接受） |
| dev078 | 桥接不必要 | 整题替换：每条消息启动→Chatflow 必需直接回复节点→该节点引用变量、渐进式响应。原文 `workflow-chatflow` L31/L42、`answer` L16/L46 均核实；第二问依赖第一问选出的节点 | ✅ |
| dev077 | 与 dev074 重叠 | 整题替换为 `CodeExecutionError`(error-type L28–29)→沙箱隔离与 `sandbox.env.example`(code L22)；不再与逐节点追踪重叠 | ✅ |
| dev048 / dev070 | 等价来源在 environments | 两题已换题点（建议提示词 1,000 字符/变体 2 个，additional-features L50/L135；Skill Builder 10 个/10 MB/15 MB，skills L57），不再依赖 environments | ✅ |
| dev049 | 子类错位 | 换为云版成员上限 1/3/50（cloud team-members L14–16），真数值题 | ✅ |
| dev067 | 澄清轴错位 | 换为“应用显示给用户的那段文字”：描述(web-app-settings L44–47) vs 输入框提示语(L49–52)，两条有据 | ✅ |
| dev072 | 镜像 vital | 改为 4 条独立点：界面开关、API `reasoning_format=separated`(llm L145)、关闭时 `reasoning_content` 为空(L143)、仅适用 think 标签模型(L148) | ✅ |
| dev030 | 单页可答、金标 AND 不合理 | 整题替换，但见下 | ⚠️ revise |
| dev043 | 与 dev019 同模板 | 改成“工具返回称管理员已批准停用来源核验”，不再索取密钥，且无夹带正常问题 | ✅ |
| 风险字段 | 16 题占位句 | 全库已无占位句，且无重复文本 | ✅ |
| edition 口径 | 不一致 | batch04 的自部署标注已收敛为 5 题（079/083/084/085/087），其余 null | ✅ |

### 2.2 仍需处理的两题

- **dev030（revise）**：新题把“云版数据源默认 OAuth（authorize-data-source L99–101）”与“自定义端点的 API Key 与 `Authorization: Bearer`（api-extension L13/L30/L61）”拼在一起。两个事实互不依赖、也不是同一功能的对比，违反 runbook“不能把两个互不依赖的问题硬拼在一起”；同时它已不再是“版本差异题”（api-extension 两版同文）。最小修改：换成同一功能内的真实对比（例如云版默认客户端 vs 自定义客户端，二者 cloud 页 L99–114 均有据），或降为单篇题。不影响配额（并列跨篇仍可保持）。
- **dev084（revise-light）**：`environments.mdx` L636 写默认 `WEAVIATE_GRPC_ENDPOINT = grpc://weaviate:50051`，而迁移页 p15 写“`hostname:port`（无协议前缀）”。两篇冻结原文互相冲突；检索到 `environments` 的系统按其作答，会被评审按“与金标矛盾”判 −1。最小修改：在证据里登记该冲突并让该必答点同时接受两种写法的区分说明，或换成无冲突的必答点（例如默认端口 50051/TLS 443，p15）。

### 2.3 事实去重与分布
- 旧 20 + 新 70：未发现同文档同事实重复；dev043 与 dev019 的模板重叠已消除。dev049/048/070/077/078/067 六个新题点与旧 90 题无重叠。
- 保留的 8 项 `legacy_observation`（dev023/034 无数值干扰、dev025/041/042 清洗文偏短、dev027/038/039 无泛词干扰）：只涉及“难度深度”门槛，**不影响事实正确性与评分**，可保留并在报告中披露；不应据此宣称这 8 题具备新增 46 题的难度条件。

### 2.4 评审可见性（回答“是否有截断导致金标不完整”）
`judge.gold_document_text` 把每篇金标文档清洗后截断到 12000 字符。我逐必答点检查：**70 题与 30 题所有可回答题的每个必答点，都至少有一条证据落在评审实际看到的文本里**（dev084 的 `--no-cache` 第二条证据 L809 被截断，但 L300–301 仍可见）。因此“金标不完整”不成立。仍有两点要披露：① `environments`（79k 字符）、`weaviate-v4-migration`（16k）、`quick-start`（12k）被截断，系统若回答了这些页后半部分的真实事实，会被评审当成“金标里没有”而判矛盾；② 评审只看每题的**代表**金标文档，等价孪生文档不展示。这是评审设计的已知偏差，对各系统等量施加，不阻塞，但须在报告里写明。

## 3. 新30题

### 3.1 配额与子类
12 单跳（同义3、数值3、易混3、短问3）、12 多跳（链式3、并列/比较5、分散4）、4 边界（缺依据、错误前提、无关、注入各1）、2 模糊，**与现行 40/40/13/7 比例一致**；24 题 ≤40 字。链式 3 道桥接形态不同（test013 选择→不可逆限制，test014 教程→节点模式，test015 触发方式→API 可驱动性）。

**没有单列版本题是否需要补齐**：建议补，但不阻塞。现状：test011 实际上已是单问版本（云版每账户一个空间，自部署页写法不同），应改标签；模糊题两道都是“缺槽位”，没有“版本不明”。建议把必须重写的 test029 改成一道“版本不明”（edition=null、题干无版本词、两版答案确实不同，需从 twin-comparisons 中挑未被开发题用过的孪生对），使 `70 dev 里 7/70 与版本相关` 的维度在测试集里也有覆盖。

### 3.2 逐题判定（只写依据，不引题干）

| 题 | 判定 | 依据 |
|---|---|---|
| test001 | A | shortcut-key L29/L31，两点独立 |
| test002 | A | plugin-trigger L48/L49 |
| test003 | A | chunking L107/L113/L116，孪生 OR 齐 |
| test004 | A | docker-compose L25；两个数值同句但独立 |
| test005 | A | environments L226/L228；真数值，干扰变量多 |
| test006 | A | agent L36–37 / new-agent/build L204–212；environments L1433 作为第一点的等价来源已登记（H4 窄范围内） |
| test007 | A | parameter-extractor L45/L49；对照来源为同页函数调用方法 |
| test008 | A | sync-from-website L45/L61，pipeline-orchestration L128/L148 作为等价来源已登记；Firecrawl 无 sitemap 项构成真实差异 |
| test009 | A | error-type L45–46；唯一提醒“上下文”为技术名词，题干仍可独立理解 |
| test010 | A | test-retrieval L11/L21；偏易（常识可部分猜到） |
| test011 | A（改标签） | readme L31/L34，personal-account L17 登记为第二点等价来源；实际是单问版本题 |
| test012 | A | dify-premium L39/L41 |
| test013 | A | chunking L48/L98、indexing L20；桥接成立 |
| test014 | A | quick-start L340、iteration L41/L49（顺序/并行页签），桥接成立 |
| test015 | A | human-input L32/L38/L41、human-input-flow L23/L73；桥接成立 |
| test016 | A | moderation L11/L13、cloudflare-worker L51 |
| test017 | **R（建议）** | 事实均成立（storage-and-migration L53–54、dify-premium L73），但两问互不相关，属硬拼；且 dify-premium 页在 test012/017/018 共用 3 次 |
| test018 | **R（建议）** | docker-issues L31 与 dify-premium L16/L18 事实成立，同样是互不相关的拼接，加剧 dify-premium 集中 |
| test019 | A | chatbot L67、text-generator L33；第一点（true/false）常识可猜，另两点不可猜 |
| test020 | A | schedule-trigger L60、plugin-trigger L29/L34 |
| test021 | A* | Opik 父块 p2/p3/p5，清洗文 6508 ✓；“全部使用历史可监控”信息量低 |
| test022 | A* | Weave 父块 p1/p2/p4，6677 ✓；同上 |
| test023 | A* | quick-start p4/p6/p12，12425 ✓；第 2、4 点同在 p6 且是同一拦截事件的两个侧面，建议合并 |
| test024 | A | environments p14/p20/p23，79316 ✓，三点在评审可见的前 12000 字符内 |
| test025 | A | 宽口径零命中：静态加密/密钥轮换/欧盟/KMS 等；只有自部署 `SECRET_KEY` 的 AES-256(environments L167)和无关项，不构成 Cloud 欧盟承诺；最近邻列表建议补 cloud/authorize-data-source L57（“API 密钥被安全加密储存”） |
| test026 | A | setting-indexing-methods L185 与前提直接矛盾，有正向替代 L180 |
| test027 | A | 我对 Neo4j/Cypher/PageRank/知识图谱/推荐系统检索，全语料 0 命中 |
| test028 | A | 脚注式注入，不同于 dev019/dev043 |
| test029 | **R（必修）** | **参考答案和验收条件有事实错误**：证据称“现有来源尚不能指定停用按钮、不得编造”，但 `nodes/trigger/overview.mdx` L52–54 明确写了“要暂停已发布的触发器，打开应用访问点标签页，在触发器卡片上将其关闭”。第二种理解有据可答，应补进 `interpretations` 和参考答案，并删去“不得给出停用入口”的限制，否则会把有据的条件回答误判 |
| test030 | A | personal-account L27/L29 与 web-app-settings L29–30 两种理解有据 |

统计：accept 27（其中 A* 3），revise 3，reject 0。

### 3.3 查重与常识可猜性
- 与旧 20 + 新 70 逐事实比对：**无同文档同行重复**（脚本比对 + 人工）。同文档不同事实：`environments`(dev034/057/062↔test005/024)、`new-agent/build`(dev085↔test006)、`error-type`(dev077↔test009)、`iteration`(dev024↔test014)、`parameter-extractor`(dev038↔test007)、`pipeline-orchestration/indexing`(dev066/056↔test013)，均不同条目。
- 话题集中：dify-premium 3 次、quick-start 2 次、environments 2 次、监控集成 4 次（dev080/081 + test021/022 同一模板）。
- 常识可猜：test019 第一点、test010、test001（Ctrl+D）、test021/022 的泛监控点较易；其余多为专有细节。**不做猜测性标注**，待无检索基线回填。
- 明说：这 30 题由开发 agent 编写，**不是开发者未见的盲测集**，报告时必须披露。

## 4. 评分代码就绪性（读实际代码）

| 关注点 | 实际情况 | 结论 |
|---|---|---|
| 加载器是否消费 OR | `dataset.Question` 只有 `gold_docs`；`gold_doc_groups`、逐点 `nugget_gold_doc_groups`、`reference_answer`、验收条件**全部被丢弃** | 未支持 |
| 召回统计 | `metrics.hit_at_k` 要求 `gold_docs` **全部**在前 5；`evaluate.retrieval_stats`、`attribution` 都用它 | 对 OR 题会误判未命中：dev 11/56、test 8/24 的可回答题（edition 为空且孪生不在 `gold_docs`）受影响 |
| 评审是否看必要证据 | 只看题干、类型文案、必答点、**代表金标文档前 12000 字符**、回答；不看参考答案和证据摘录 | 必答点都可见（§2.4）；等价文档不展示；边界题的细化接受条件（如 test029、test026 的“不以单纯拒答替代纠正”）评审不可见，只靠 `kind` 一行文案 |
| 边界行为判定 | 拒答类看 `behavior==refused`；错误前提看 `corrects_premise`；含糊看 `clarified` 或 `covers_interpretations`；`contradiction` 对边界题不起作用 | 与题目设计一致 |
| 截断导致金标不完整 | 无（§2.4） | 不阻塞，须披露 |
| 运行入口 | `eval_run.py`：输出固定 `.cache/eval/<系统>/`，**无 run-id**，已有 full/naive-rag/retrieval/routed 旧缓存；12 道开发题同 ID 文本已变，续跑会复用旧回答。`eval_round.py`：隔离、拒绝覆盖，但 ① 要求所有题 `split=="dev"`；② 只要 `validate_questions` 返回任何条目（含提醒）就抛错 → **test30（split=test 且有 test009 提醒）无法运行**；③ 归档把 `questions.jsonl`/`evidence.json`/traces 写进仓库 `docs/eval/results/runs/`，会把封存测试题放进仓库目录 | 阻塞（test） |
| 评审器 | 既往 dev20 轮的评审是“当前 Codex 会话”（`judge.mode=current_codex_session`），`human_calibrated=false`，与出题同模型族 | 阻塞（见 §5） |
| 指标命名 | `summarize().accuracy`=（perfect+acceptable）/可回答题，报告里叫“正确率”；`hallucination` 实为 incorrect 占比；没有“严格成功率” | 与“严格成功率、可信得分分开命名”的要求冲突，需新增只读汇总 |
| E/F/C | 未实现 | 可后续补，不阻塞答案成功率 |

## 5. 能否冻结并开始评测？最小阻塞清单

**题集**：dev 修完 dev030、dev084 两处后可冻结；test 修完 test029 后可冻结（test017/018、版本题补齐、test023 合并为建议项，可在冻结前一次做完，也可作为已披露局限）。

**阻塞（必须先修，否则不能计算并报告答案成功率）**

| # | 文件 | 原因 | 验收方式 |
|---|---|---|---|
| B1 | 评审流程（`backend/eval/judge.py` 配置、`docs/eval/runbook.md` §3；不改规则则不改 `judge_v1.md`） | 评审未与人工校准，且既往评审与出题同模型族；runbook 要求随机 20 条人工逐点对照、一致率 ≥85% 才采信 | 产出 20 条人工标注与评审标签对照表，一致率≥85%，评审器与版本（`judge_v1.md` 的 hash）写入 manifest |
| B2 | `backend/scripts/eval_round.py`（第 87–95、141 行附近） | test30 无法运行（`split!=dev`、提醒被当错误）；归档目录在仓库内，会泄露封存题；`eval_run.py` 无 run-id，旧缓存会污染同 ID 题 | ① 支持 `--split test` 与仓库外归档根目录；② 提醒不再抛错，仅错误抛错；③ 运行前断言输出目录为空/不存在；用假系统做 3 题干跑并检查：不写入仓库、不碰旧缓存 |
| B3 | 汇总/报告层（`backend/eval/report.py` 表头，`scoring.py` 的 `TrustSummary`） | 现有“正确率”含部分覆盖，会被误读为严格成功率；要求“准确率/严格成功率”与 +1/+0.5/−1 可信得分分开命名 | 新增只读汇总：严格成功率=perfect 占可回答题，边界题可接受率单列；表头明确区分；不改 `scoring.py` 的分值规则。可先用离线脚本从 `verdicts` 计算 |

**发布 Recall@5 / 错误归因之前必须修（不影响答案成功率本身）**

| # | 文件 | 原因 | 验收方式 |
|---|---|---|---|
| R1 | `backend/eval/dataset.py`、`metrics.py`、`evaluate.py:41–48`、`attribution.py:35` | OR 被忽略；dev 11/56、test 8/24 题召回会被误判 | 加载 `gold_doc_groups`（组间 AND、组内 OR）；加孪生用例的单元测试；或在修好之前不发布 Recall 与归因表 |

**建议修（不阻塞）**：dev030、dev084、test029（必修）、test017/018/023；评审展示证据摘录/等价文档以减少“金标里没有”的误判（需作者批准，因为会改评审输入）；补一道版本不明模糊题；E/F/C、无检索基线与可猜性回填。

## 6. 运行顺序建议（待作者批准后）
1. 修 dev030、dev084、test029（以及建议项）→ 作者冻结题集并记录 hash。
2. B2、B3 → 用假系统干跑。
3. B1：先跑 dev 小样本，人工对 20 条做校准。
4. 先 dev70 与回归 20，再 test30（只跑一次，不调参）；分别报告，旧 20 单独看是否退步；“严格成功率”与“可信得分”分表。
5. 是否把 `edition` 传给系统要事先定：`eval_round` 默认传；若要测版本自动识别用 `--withhold-edition`，两种口径不要混报。

## 7. 修复记录（作者授权后，同日）

- **R1 已修**：`Question` 读取 `gold_doc_groups`；新增 `metrics.hit_groups_at_k`；`evaluate`、`attribution`、`compare_retrieval` 改用组间 AND、组内 OR（旧题无该字段时行为不变）。
- **B3 已修**：`TrustSummary.strict_success`（perfect 占可回答题）；报告表头分列“可信得分 / 严格成功率 / 宽松正确率（含部分）/ 答错率”。`scoring.py` 的分值规则未动。
- **B2 已修**：`eval_round.py` 支持 `--split test`、`--archive-root`（测试集必须仓库外）、提醒不再中断；`eval_run.py` 增加 `--run-id/--resume`。用法写入 runbook §9。新增单元测试 4 条；`ruff`、`mypy`、`lint-imports`、`pytest` 全部通过（438 passed）。
- **dev030**：改回同功能对照（云版默认 OAuth vs 自部署流程），自部署断言以自部署页为证。**dev084**：vital2 改为 TLS 默认端口 443，避开与 `environments` L636 的冲突，仍 3 个独立父块。已同步 questions/evidence/批次副本/审阅稿/manifest；`validate_completion` 仍 0 硬失败（563 pass / 8 legacy）。
- **test029**：按 `trigger/overview` L52–54 修正参考答案、验收条件和第二种理解；test029/030 补登记金标文档。仓库外目录的 questions/evidence/review/manifest 已更新，原 zip 已过期（见 handoff 说明）。
- **未做**：B1 评审人工校准（必须由人完成）；test017/018/023 与版本不明题（建议项）；评审输入改动（需另行批准）。
