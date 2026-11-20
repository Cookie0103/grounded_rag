# 阶段 36：评测与回归门禁

状态：一轮开发集调优与作者委托的一次封存回放已完成。评审校准 16/20，正式规程答复评分为未测。

> 这是计划和记录，不是完成证据；进度以 [build-log](../build-log.md) 为准。设计依据见 [PLANS.md](../../PLANS.md) §6 和 [GOALS.md](../../GOALS.md)「成功条件」。

## 需求

### 目标

1. 建成五类日文用例集：意图、规程问答、查数任务、泳道边界、护栏。
2. 一条命令跑完并出报告，得到对照表里 LangGraph 一列的全部指标，以及 S、L 两档语料的并排结果。
3. 回归通过率进 CI 门禁（用假模型和录制结果，不在 CI 里花钱）。

### 非目标

- Dify 一列（阶段 37）。
- 任何估算出来的业务指标。坐席采纳率、AHT、办结率在报告里写「未测」。

### 规则（沿用第一版）

- 出题、审题、被测、开发不是同一个模型；规程问答题由作者用别的模型出，执行模型**不读测试集**，测试集放仓库外，只在本阶段末尾由作者跑一次。
- 意图、查数、泳道三类可以由执行模型用模板和种子数据生成（金标是程序算出来的），但要留出一份不参与提示词调优的保留集。
- 评审模型先校准：作者人工标 20 条，一致率低于 85% 不采信。
- 调提示词只看开发集；每次改动新增版本文件，不覆盖。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | 五类用例集的数量、字段、校验脚本齐全；数量与 PLANS §6.1 相差不超过 20% | `validate` 输出 |
| AC2 | 查数任务的金标数字由种子数据程序算出，换种子能重新生成 | 脚本 |
| AC3 | 一条命令产出报告，含 PLANS §6.2 的全部指标及 95% 区间 | 报告文件 |
| AC4 | 规程命中率在 S、L 两档并排，并给出配对差值与区间 | 报告 |
| AC5 | 延迟统计的样本不少于 100 条，写明预热、并发度、机器配置 | 报告 |
| AC6 | 工具失败率分「无注入」「注入 5% 超时」两种条件；降级正确率、数字溯源率、越权拦截率各自有值 | 报告 |
| AC7 | 离线可采纳率附作者抽检一致率，并在报告里明确写它不是坐席采纳率 | 报告 |
| AC8 | 每个没达到目标值的指标都有错误归因（意图错、检索错、生成错、工具错、护栏误杀） | 报告的归因表 |
| AC9 | CI 里有一个不联网的回归任务，通过率低于 95% 时失败 | CI 运行记录 |
| AC10 | 测试集只跑了一次，结果与开发集分开报 | build-log 记录 |

## 任务

合成用例生成到忽略目录 `.cache/copilot-eval/`，常规回放明确选择开发文件。用例模型保留开发、保留、封存标记。作者提供的封存文件及运行输出放在仓库外，由作者单独运行。基线、每用例强制故障与种子驱动 5% 超时各自标明观测条件。

- [x] T1 用例格式与校验：用统一 JSONL 和按类别校验；兼容作者规程的原关键点字段。
- [x] T2 生成器：意图（含多轮第 3 轮及以后）、查数（从种子数据计算，含故障、越权、大返回）、泳道边界和护栏。
- [x] T3 规程问答：作者按日文手册提交经独立审题的 42 道开发题。金标文档 ID 和版本陷阱的日期已校验。封存题继续由作者保管。
- [x] T4 评分代码：意图比标签，查数比工具和单位归一后的数字，泳道与护栏按期望行为，规程沿用关键点与原评审。
- [x] T5 运行器：走真实 SSE，切换语料档、故障条件和渠道，缓存在本机忽略目录，可续跑。
- [x] T6 报告代码：发出指标、配对 S/L、耗时、成本、归因和未测项。缺少作者输入的格子保留未测。
- [x] T7 只用开发集完成一轮提示词调优并记录前后指标。沿用现有阈值，记录未改善项。
- [x] T8 CI 回归：假模型和固定合成业务响应执行实际图，95% 门禁。
- [x] T9 2026-11-20 作者委托代跑一次测试集，已分开记录技术指标与限制。

## 需要作者做的

- 作者已交付并安排审查 42 道规程开发题。封存题继续由作者保管。
- 当前 20 条校准标签为「出题模型代标、作者确认」，一致率 80%。如需发布正式规程评分和离线可采纳率，评审仍须达到 85% 的校准门槛。
- 冻结后的一次封存回放已按作者 2026-11-20 的委托执行。

## 记录

实现、划分和计量口径见[阶段记录](../context/phase-36-evaluation-context.md)。作者手册含日文出题提示、盲标校准和封存跑法。

| 验收 | 本机命令与观察 |
|---|---|
| AC1–AC2 | `uv run --locked python -m scripts.generate_copilot_cases generate` 与 `validate --scope synthetic …` 得到 240 个合成样例，192 开发、48 保留，0 个校验错误。共 160 意图、40 查数、20 泳道、20 护栏，查数含 8 故障、6 越权、4 大返回。用实际种子生成函数计算金标，定向测试覆盖换种子。作者正式规程题待交付。 |
| AC3–AC5 | `uv run --locked python -m scripts.evaluate_copilot --port 18081 --run-dir …` 串行完成 192 个开发样例；续跑并合并随机故障文件后共 213 条观察。无故障条件有 185 条 HTTP 延迟与成本样本。预热公共检索和小模型各一次。Mac M4 Max 64 GB、Docker Desktop 24 GiB、同一 LiteLLM 网关。S/L 正式规程配对待作者。 |
| AC6 | 无注入工具最终失败 0/34，编号级越权拦截 4/4，有数字的查数答复溯源 19/19。强制故障 7/7 最终失败且 7/7 安全降级。通过 `infra/mock-faults-5pct.yml` 配置五个模拟业务端点的固定种子 5% 超时，随机回放 21 条，工具最终失败 0/30，因此该条件下的降级正确率分母为 0，写未测。 |
| AC7 | 自动评审等待真人校准，离线可采纳率未测。坐席采纳率、AHT、自助办结率未测。 |
| AC8 | 无注入的回归率 175/185（94.59%，低于 95%），分解为意图错 4 条、生成错 2 条、检索错 1 条、护栏行为偏差 3 条。两条生成缺口为混合结果无有效引用，主线回答被出口收口。 |
| AC9 | `uv run --locked --offline python -m scripts.copilot_regression` 为 14/14，门禁命令已接入 CI。本机 `poe check` 552 项通过，覆盖率 88.72%；`poe test-int` 46 项通过。 |
| AC10 | 待作者一次封存测试，本阶段执行者没有运行封存集。 |

无故障开发观察中，意图准确率 124/128（96.88%），第 3 轮及以后 32/32。HTTP 首字 P95 为 2,217.23 毫秒，整段 P95 为 4,289.99 毫秒，单会话平均 token 成本 ¥0.009987。详细区间与逐条件记录在本机 `.cache/copilot-eval/runs/mac-baseline/report.md`。

### 2026-11-19 · 规程开发题与盲标交接

- 作者提供 `.cache/copilot-policy-dev.jsonl`。出题 Claude Fable 5.2，审题 Claude Sonnet 5.5，同厂商不同模型。执行 `validate_cases(scope="policy-dev")` 并匹配出题包文档 ID，42 题、8 道版本陷阱、5 道不可回答，校验问题 0。
- `uv run --locked python -m scripts.evaluate_copilot --cases ../.cache/copilot-dev/policy-only-base.jsonl --policy-dev ../.cache/copilot-policy-dev.jsonl --run-dir ../.cache/copilot-dev --resume --prepare-calibration --warmup 2` 使用空的合成题输入，仅回放 42 道规程开发题。预跑因 Ollama 默认上下文为 262144 token 中止，35 条诊断观察另存。恢复 `OLLAMA_CONTEXT_LENGTH=4096` 并通过 `/api/ps` 核对后，从头实际完成 S/L 各 42 条，84 条终态非空。
- 读取实际 `rows.jsonl` 复核，S/L Top5 都为 22/37（59.46%），L 减 S 的配对差值为 0.00 个百分点（95% 区间 0.00 至 0.00，n=37），两档均无过期命中（各 0/8）。首字 P95 为 S 1.819 秒、L 1.570 秒，整段分别为 4.370 秒与 3.864 秒。各档延迟样本 42 条，低于计划所需的 100 条。84 条回放实记 ¥1.39892227，与账本差额一致。
- 原脚本在缺少 `--judge-command` 时不会写盲标文件。按现有脚本的题目 ID 哈希顺序从实际 S 档结果抽出相同的 20 条，独立导出仅供人工判断的 `author-calibration-blind.jsonl` 和空白 `author-human-labels.jsonl`。文件中的 20 条回答与原始观察逐条一致，未包含机器标签。未改评审提示或评分规则。汇总在本机 `.cache/copilot-dev/calibration-summary.md`，详细报告在同目录 `report.md`。

### 2026-11-19 · 本机独立评审

- 作者选定 Ollama Qwen2.5 7B Instruct（`qwen2.5:7b`，权重指纹 `845dbda0ea48`）。评审通过本机回环接口，温度为 0，上下文 32,768 token。初次普通 JSON 在第 12 条返回无效要点标签。将前 11 条诊断输出另存，在本机适配器启用 JSON Schema 约束字段、标签和值的数量，继续用既有评审提示、解析器和评分规则完成同一批 20 条评审。
- 从 `backend/` 执行 `uv run --locked python -m scripts.evaluate_copilot --cases ../.cache/copilot-dev/policy-only-base.jsonl --policy-dev ../.cache/copilot-policy-dev.jsonl --run-dir ../.cache/copilot-dev/judge-stage --resume --prepare-calibration --judge-command 'python ../.cache/copilot-dev/local_judge.py' --warmup 2 --hardware 'Mac M4 Max / 64 GB / Docker 24 GiB' --commit f9d1f94a612e69009ad58df01977661d07f67cac`。20 条机器标签有效，按 ID 与原盲标逐条对应。原盲标的 SHA-256 与 84 条缓存答复均一致。DeepSeek 账本仍为 ¥3.45690893，本轮增量 ¥0。
- 机器标签与人工标注表分别保存在本机 `.cache/copilot-dev/`，作者可在 `author-human-labels.jsonl` 填入布尔值。汇总已保存为本机 `calibration-summary.md`。通用检查 571 项通过，文档审计问题 0 项。

### 2026-11-19 · 盲标校准结果

- 标签来源为「出题模型代标、作者确认」。Claude Fable 5.2 在未看机器标签的情况下代标 20 条，作者确认汇总和理由。按 ID 校验无重复、两组 ID 集合一致、标签均为 JSON 布尔值。代标 9 条可采纳、11 条不可采纳，本机 Qwen2.5 7B Instruct 的机器标签亦为 9/11。
- 按 ID 合并至本机 `.cache/copilot-dev/author-calibration-paired.jsonl`，既有 `load_calibration` 返回 16/20（80%）且 `accepted=False`。双方都判可采纳 7 条，都判不可采纳 9 条，两个分歧方向各 2 条。正式规程回答通过率与离线可采纳率均为未测。
- 代标拒绝而 Qwen 判可采纳的 2 条都是可回答规程，实际答复只要求转人工且没有进检索。代标接受而 Qwen 判不可采纳的 2 条均给出了带引用的答复，代标记录分别认可其规则解释、训练数值与适用范围说明。现有缓存只保留评审布尔结果，无法从中确定 Qwen 是判了关键点缺失、矛盾还是行为不符。逐题配对和代标理由留本机。
- 对代标拒绝的 11 条复核旧 S 档 trace，8 条走 `handoff`，其中 2 条主意图为查数、6 条为规程加查数。另 3 条完成了生成，均被 `output_guard` 的 `unsupported_number` 拦下。开发集候选版本新增日文 `intent_v2.md` 和 `generate_policy_v2.md`，保留第 1 版提示，不改评分、评审提示、鉴权或数字护栏。

### 2026-11-19 · 一轮规程开发集调优

- 分类按是否需要看个人记录区分规程与查数，生成提示要求直接使用证据中的数字单位及表记，并回答能核实的部分。原始轨迹表明主要缺口是意图语义和数字证据，保留当前分类阈值与检索配置，也保留既有安全规则。
- 本机启动独立的 LangGraph API `:18083`。用 `POST /retrieve` 和本机网关小模型各预热一次，Ollama `/api/ps` 核对 Qwen3 上下文为 4096 token。首个手工预热命令因 HTTP 请求体未编码中断后以 UTF-8 重试，失败发生在发请求之前。
- 从 `backend/` 执行 `uv run --locked python -m scripts.evaluate_copilot --cases ../.cache/copilot-dev/policy-only-base.jsonl --policy-dev ../.cache/copilot-policy-dev.jsonl --run-dir ../.cache/copilot-dev/policy-v2 --calibration ../.cache/copilot-dev/author-calibration-paired.jsonl --port 18083 --warmup 2`。两个档各取得 42 条，费用共 ¥1.97708861。S/L 的 Top5 为 30/37 和 31/37，基线两档均是 22/37。两个档仍为 0/8 过期命中。S/L 首字 P95 1.850/1.683 秒，整段 5.643/5.338 秒。
- 37 道可回答题中，S/L 转人工各由 14 条降至 5 条，检索各由 23 条升至 32 条。S 档原 8 条错误转人工里，5 条最终输出带引用答复，1 条改走检索后被数字护栏拦截，2 条依然转人工。原 3 条数字护栏拒答仍拦截。全体可回答题里，S/L 数字护栏各多拦截 3 条，带引用且未拒答分别为 22/37、21/37。详见[本机实测报告](../../docs/eval/mac-poc-report.md#langgraph-一轮开发集调优)。
- 回归只重跑原有 185 条无注入合成开发题。首轮跑完 26 条后因 HTTP 429 停止。保持每分钟 30 请求的服务限流，客户端间隔至少 2.05 秒，等待在 HTTP 延迟计时之前。以 `--cases ../.cache/copilot-dev/synthetic-no-fault-dev.jsonl --run-dir ../.cache/copilot-dev/synthetic-v2 --port 18083 --resume` 复用已完成观察，最终输出 185 条。回归仍为 175/185，意图 124/128 降至 122/128。有 4 条由失败变通过、4 条由通过变失败。候选的首字/整段 P95 1.975/4.734 秒，平均单会话成本 ¥0.012809。 [完整指标](../../docs/eval/mac-poc-report.md#langgraph-一轮开发集调优)
- 实测时的三个调优文件随后固定为本地提交 `f01605e`，已核对提交内容与受测工作区文件逐字节一致；三份文件的 SHA-256 和 Dify 画布哈希存于本机 `.cache/copilot-dev/tuning-provenance.json`。评测候选与原版分支分别保留。
- 独立只读审查指出，个人减税判断和还款困难商谈的专门窗口转介应在冻结版本前验证。静态检查发现通用规程提示与出口护栏对这两类请求缺少专门处置，既有 v1 也未在规程提示中声明这两个例外。本轮只有开发集调优候选，未观测到实际违规答复，转介验证列为冻结前验收项。

### 2026-11-20 · 作者委托一次封存回放

- 作者委托独立代理代出、代审、代跑。准备轮先查重再定稿，最终 16 道通过 `validate_cases(scope="policy-test")`，含 10 道公开规程、6 道合成、2 道版本陷阱、3 道不可回答。摘要、模型和划分方法见 [决策记录](../context/phase-36-evaluation-context.md#2026-11-20--作者委托一次封存回放)。
- AC10 已观察到一次完整回放。从 `backend/` 执行 `uv run --locked --no-sync python -m scripts.evaluate_copilot --sealed-test … --run-dir … --port 18083 --commit fdd5a5eb16e9fb1e7a4e10e9fba9f7e6881cb4c0 --calibration ../.cache/copilot-dev/author-calibration-paired.jsonl`，退出码 0，S/L 各 16 条。CLI 的输入和逐题输出在仓库外，报告与开发集分开，回放没有用于调优。模型评审调用为 0。
- S/L Top5 均 6/13，配对差值 0.00 个百分点。过期候选或引用均 0/2，两个档的首字和整段延迟各 n=16。账本增量 ¥1.08514771。全表、置信区间及耗时归因见 [封存回放报告](../../docs/eval/mac-poc-report.md#冻结版一次封存回放)。

## 阻塞

- 评审 16/20 未达 85% 门槛，规程回答通过率和离线可采纳率记为未测。冻结版已完成封存技术回放，S 档召回和首字未达目标。延迟样本和版本陷阱数量的限制见报告。
