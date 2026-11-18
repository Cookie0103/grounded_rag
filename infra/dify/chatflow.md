# 阶段 37 · Dify Chatflow V3

[Chatflow 模板](copilot-chatflow.yml)使用 Dify 1.19.0 的应用 DSL 0.7.0。部署时，将模板中两处 `00000000-0000-4000-8000-000000000001` 替换为本机 S 档知识库的 UUID，或导入后在两个检索节点重新选中该知识库。知识库端配置混合检索，节点端设 Top 5，关闭额外精排。模型节点绑定工作区的 OpenAI 兼容供应商，使用网关别名 `small` 和 `deepseek-v4-pro`。

应用 API 使用顶层 `query` 对应 `sys.query`，其他字段放在 `inputs`。省略 `channel` 时使用 `customer`。坐席查数必须提供 `channel=agent`、`agent_id` 和 `customer_id`。可选 `as_of` 按 `YYYY-MM-DD` 传入回答提示。可选 `mock_fault` 仅用于已启用故障头的本机模拟服务，支持空值、`timeout`、`5xx` 和 `delay`。

## 节点配置

| 节点 ID | 配置与行为 |
|---|---|
| `start` | 声明渠道、坐席、客户、基准日和故障注入字段。 |
| `intent` | 网关 `small` 的原生问题分类器，使用日文类名、例句和四轮历史窗。分类失败或判不出类别时走服务降级。 |
| `channel_gate` | 任一含查数意图的请求先检查渠道。只有 `agent` 能进入工具规划。 |
| `answer_smalltalk` | 固定日文问候并邀请提问。 |
| `answer_complaint` | 固定日文回复并引导主管处理。 |
| `answer_handoff` | 客户查数和混合请求的固定转人工回复。回复无数字，路径无需业务 HTTP 节点。 |
| `plan_tools` | 网关 `small` 将当前问题转为最多五项工具计划，只提供合成工具名和参数示例。 |
| `prepare_tools` | 校验 JSON、固定工具名、坐席和客户上下文、合同位置及期数范围，并去重。合同编号只从当前问题中出现的编号提取。 |
| `plan_gate` | 合法计划进入迭代。需要合同编号时发出补充提示，其他异常走业务故障回复。 |
| `answer_contract` | 请坐席补充当前要查的合同编号。 |
| `run_tools` | 逐项执行已验证的计划，收集每项的结果对象。 |
| `tool_start` | 每次迭代的原生入口。 |
| `request_args` | 用固定工具映射生成路径和查询参数。每项查询带当前客户 ID，合同级查数另带合同 ID。 |
| `mock_authorize` | GET `http://mock_core:8001/authorization`，带坐席头。 |
| `check_authorization` | 只接受 HTTP 200 且 `authorized` 为 JSON 布尔真，其余分为拒绝和失败。 |
| `auth_gate` | 鉴权通过才进入业务 GET，拒绝与失败进入鉴权失败节点。 |
| `auth_failure` | 保存脱敏状态，标记 `business_dispatched=false`。 |
| `mock_get` | GET 调用相应业务端点。两段 HTTP 各设置 2 秒连接、读、写超时，关闭节点自身重试。显式模拟故障只注入业务请求。 |
| `crop_response` | 仅接受 `synthetic=true` 的响应，校验允许字段及类型。三个列表最多保留 5 项，保留响应总数。未指定还款区间时从下次还款起选取，已完济时取末五项。 |
| `collect_call` | 聚合鉴权未通过和业务结果两个互斥分支，输出一个对象。 |
| `tool_evidence` | 输出整轮状态和工具观察结果。整轮成功才生成供模型消费的白名单 JSON。 |
| `tool_gate` | 区分整轮成功、越权、业务故障。 |
| `answer_denied` | 固定日文越权拒绝，无业务数字。 |
| `answer_tool_failed` | 固定日文业务故障回复，无业务数字。 |
| `mixed_gate` | 单独查数直接生成，混合请求进入 S 档知识库检索。 |
| `retrieve_policy` | 规程请求查 S 档知识库，使用 `sys.query`，最多 5 条。 |
| `policy_evidence` | 检索结果为空时走固定资料不足回复。 |
| `generate_policy` | 网关 `deepseek-v4-pro` 依据规程检索结果生成日文回答。 |
| `answer_policy` | 直接输出规程生成文本。 |
| `generate_lookup` | 网关 `deepseek-v4-pro` 依据白名单 JSON 生成日文回答，提示保留合成标记。 |
| `answer_lookup` | 直接输出查数生成文本。 |
| `retrieve_mixed` | 混合请求在业务查数成功后查询相同 S 档知识库，使用 `sys.query`，最多 5 条。 |
| `mixed_evidence` | 混合检索结果为空时走固定资料不足回复。 |
| `generate_mixed` | 网关 `deepseek-v4-pro` 根据规程和查数结果分段生成日文回答。 |
| `answer_mixed` | 直接输出混合生成文本。 |
| `answer_policy_empty` | 固定日文资料不足回复。 |
| `answer_service` | 分类、检索或生成服务异常时的固定日文降级回复。 |

业务路径依次对应 `query_loan_contracts` → `/loan-contracts`、`query_repayment_schedule` → `/repayment-schedule`、`query_delinquency` → `/delinquency`、`query_rate_terms` → `/rate-terms`、`query_benefits` → `/benefits`。

## 回放观察字段

| 阶段 | 节点与输出 |
|---|---|
| 主副意图 | `intent.class_id`。四个单意图使用 `smalltalk`、`complaint`、`policy`、`lookup`。混合用 `lookup_policy`、`policy_lookup`，按 ID 的词序映射主副意图。`unclassified` 表示未判定。 |
| 检索候选 | `retrieve_policy.result` 或 `retrieve_mixed.result`。用本机知识库文件名或元数据映射回语料 ID。 |
| 工具结果 | `tool_evidence.tool_calls`。每项记录 `tool_name`、脱敏的 `arguments`、`status`、`reason`、`business_dispatched`、`data`、`total` 和 `returned_count`。拒绝的预检保留在工具轨迹中。 |
| 最终回答 | 应用 API 的回答事件。各 Answer 节点 ID 对应具体回复路径。 |
| 模型 | `intent`、`plan_tools` 使用 `small`。三个 `generate_*` 通过同一网关使用 `deepseek-v4-pro`。 |

当前模板的混合分支先查数再检索。合同级工具需要当前问题里的合同编号。知识检索调用使用原问和知识库的混合排序，`as_of` 在生成节点内作为文字证据约束。合成结果的字段范围由独立代码节点限制，HTTP 日志仍可能保留完整上游响应，评测只导出脱敏的工具结果。工作流的 `agent_id` 由本机评测入口提供，模拟服务负责复核客户及合同归属。
