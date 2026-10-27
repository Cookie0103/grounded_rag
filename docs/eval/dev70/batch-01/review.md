# batch-01 当前审阅稿

2026-10-20复审修订稿；逐项原因见repair-2026-10-20.json及revision-log.md。所有原样检索和数据库记录为修订前历史证据，本版本未复跑。

## dev021 · single/short

Workflow受理和结束各看哪帧？

参考答案：受理看首个data事件workflow_started；Workflow正常结束看workflow_finished。第一帧ping只是保活。

失败风险：将ping当受理信号，或把Chatbot的message_end套为Workflow终止事件。

预期行为/路由：answered / SINGLE；小问数：2。

- **vital 1**：首个data事件workflow_started表示Workflow运行已受理。
  - 必需组1（组内OR）：
    - [api-reference/guides/streaming L27–27](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx#L27-L27) · `api-reference/guides/streaming#c2` · `api-reference/guides/streaming#p2`：Chatflow 应用和 Workflow 应用的事件流第一帧固定是 `ping`，运行期间还会约每 10 秒到达一次。不要把第一帧当作运行已受理的信号，应以第一个 `data:` 事件（`workflow_started`）为准。
- **vital 2**：Workflow应用以workflow_finished作为终止事件。
  - 必需组1（组内OR）：
    - [api-reference/guides/streaming L78–78](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx#L78-L78) · `api-reference/guides/streaming#c5` · `api-reference/guides/streaming#p3`：    - Workflow 应用为 `workflow_finished`

## dev022 · single/synonym

不重跑前面的步骤，怎么换一份中间结果只测后面的步骤？

参考答案：在底部变量检查器中编辑可修改的中间变量值，再单独运行下游节点；下游用改后的值，不必重跑前面的步骤。

失败风险：只会全流程重跑或修改节点配置。

预期行为/路由：answered / SINGLE；小问数：1。

- **vital 1**：在变量检查器中编辑可修改的中间变量值。
  - 必需组1（组内OR）：
    - [self-host/use-dify/debug/variable-inspect L15–15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L15-L15) · `self-host/use-dify/debug/variable-inspect#c1` · `self-host/use-dify/debug/variable-inspect#p1`：任何节点运行后，其输出变量会出现在屏幕底部的检查器面板中。点击任何变量可查看其完整内容。
  - 必需组2（组内OR）：
    - [self-host/use-dify/debug/variable-inspect L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L23-L23) · `self-host/use-dify/debug/variable-inspect#c2` · `self-host/use-dify/debug/variable-inspect#p2`：你可以通过点击大多数变量值来编辑它们。当你运行下游节点时，它们将使用你编辑的值而不是原始值。这让你可以测试不同场景，而无需重新运行整个工作流。
- **vital 2**：单独运行下游节点时会使用编辑后的值，无需重跑上游。
  - 必需组1（组内OR）：
    - [self-host/use-dify/debug/variable-inspect L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L23-L23) · `self-host/use-dify/debug/variable-inspect#c2` · `self-host/use-dify/debug/variable-inspect#p2`：你可以通过点击大多数变量值来编辑它们。当你运行下游节点时，它们将使用你编辑的值而不是原始值。这让你可以测试不同场景，而无需重新运行整个工作流。

## dev023 · single/numeric_table

外部知识检索请求体的顶层必填字段有哪些？

参考答案：顶层必填字段有knowledge_id、query、retrieval_setting。嵌套参数不算顶层字段。

失败风险：把top_k等嵌套参数误列为顶层字段。

预期行为/路由：answered / SINGLE；小问数：1。

- **vital 1**：顶层必填字段包括knowledge_id。
  - 必需组1（组内OR）：
    - [self-host/use-dify/knowledge/external-knowledge-api L34–34](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L34-L34) · `self-host/use-dify/knowledge/external-knowledge-api#c3` · `self-host/use-dify/knowledge/external-knowledge-api#p3`：| `knowledge_id` | 是 | string | 外部系统中知识源的标识符，即连接时填写的 **外部知识库 ID** 字段的值，用于将查询路由到正确的知识源。 |
    - [cloud/use-dify/knowledge/external-knowledge-api L34–34](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/external-knowledge-api.mdx#L34-L34) · `cloud/use-dify/knowledge/external-knowledge-api#c3` · `cloud/use-dify/knowledge/external-knowledge-api#p3`：| `knowledge_id` | 是 | string | 外部系统中知识源的标识符，即连接时填写的 **外部知识库 ID** 字段的值，用于将查询路由到正确的知识源。 |
- **vital 2**：顶层必填字段包括query。
  - 必需组1（组内OR）：
    - [self-host/use-dify/knowledge/external-knowledge-api L35–35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L35-L35) · `self-host/use-dify/knowledge/external-knowledge-api#c3` · `self-host/use-dify/knowledge/external-knowledge-api#p3`：| `query` | 是 | string | 用户的搜索查询。 |
    - [cloud/use-dify/knowledge/external-knowledge-api L35–35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/external-knowledge-api.mdx#L35-L35) · `cloud/use-dify/knowledge/external-knowledge-api#c3` · `cloud/use-dify/knowledge/external-knowledge-api#p3`：| `query` | 是 | string | 用户的搜索查询。 |
- **vital 3**：顶层必填字段包括retrieval_setting。
  - 必需组1（组内OR）：
    - [self-host/use-dify/knowledge/external-knowledge-api L36–36](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L36-L36) · `self-host/use-dify/knowledge/external-knowledge-api#c3` · `self-host/use-dify/knowledge/external-knowledge-api#p3`：| `retrieval_setting` | 是 | object | 检索参数。详见 [下文](#retrieval_setting)。 |
    - [cloud/use-dify/knowledge/external-knowledge-api L36–36](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/external-knowledge-api.mdx#L36-L36) · `cloud/use-dify/knowledge/external-knowledge-api#c3` · `cloud/use-dify/knowledge/external-knowledge-api#p3`：| `retrieval_setting` | 是 | object | 检索参数。详见 [下文](#retrieval_setting)。 |

## dev024 · single/neighbor

一批独立输入逐项处理，失败仍续跑怎么配，失败项输出什么？

参考答案：用迭代节点，错误处理选“错误时继续”；失败元素在输出数组中用null占位，其余项继续处理。

失败风险：把循环当独立数组处理，或误选移除失败结果。

预期行为/路由：answered / SINGLE；小问数：2。

- **vital 1**：采用迭代节点的“错误时继续”处理策略。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/iteration L73–73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/iteration.mdx#L73-L73) · `self-host/use-dify/nodes/iteration#c5` · `self-host/use-dify/nodes/iteration#p5`：**错误时继续** - 跳过失败的项目并继续处理，为失败的元素输出 null
- **vital 2**：失败元素在输出数组中用null占位。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/iteration L77–80](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/iteration.mdx#L77-L80) · `self-host/use-dify/nodes/iteration#c5` · `self-host/use-dify/nodes/iteration#p5`：输入输出对应示例：
- 输入：`[1, 2, 3]`
- 错误时继续的输出：`[result-1, null, result-3]`
- 移除失败的输出：`[result-1, result-3]`

## dev025 · multi/scattered_ordered

云版知识库存储按什么计量、满额还能编辑分段吗、删文档后为何额度没立刻降？

参考答案：按文档产生的向量数量计量。满额会拦截编辑分段。删文档后账单用量延迟刷新，资料没有给出固定刷新秒数。

失败风险：按文件体积算用量或凭数字未降就断言删除无效。

预期行为/路由：answered / MULTI；小问数：3。

- **vital 1**：存储用量取决于文档产生的向量数量。
  - 必需组1（组内OR）：
    - [cloud/use-dify/knowledge/knowledge-storage-limit L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L23-L23) · `cloud/use-dify/knowledge/knowledge-storage-limit#c1` · `cloud/use-dify/knowledge/knowledge-storage-limit#p1`：用量取决于文档产生的向量数量，而非文件本身的大小。分段越多，产生的向量就越多。
- **vital 2**：额度满时，编辑分段会被拦截。
  - 必需组1（组内OR）：
    - [cloud/use-dify/knowledge/knowledge-storage-limit L49–49](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L49-L49) · `cloud/use-dify/knowledge/knowledge-storage-limit#c3` · `cloud/use-dify/knowledge/knowledge-storage-limit#p3`：上传文档、新增或编辑分段、恢复已归档文档，以及修改分段设置等重新索引操作都会被拦截，以 **经济** 方式索引的知识库也不例外。
- **vital 3**：删除后账单用量数字延迟刷新。
  - 必需组1（组内OR）：
    - [cloud/use-dify/knowledge/knowledge-storage-limit L59–59](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L59-L59) · `cloud/use-dify/knowledge/knowledge-storage-limit#c4` · `cloud/use-dify/knowledge/knowledge-storage-limit#p4`：**设置** > **账单** 中的用量数字延迟刷新，删除后要过一段时间才会下降。

## dev026 · multi/scattered_ordered

启动Dify1.17.1前，Weaviate逐级升级时，备份用什么复制选项、总量用哪种查询、失败回退时数据卷怎么办？

参考答案：离线备份用cp -a保留数据卷属性；总对象数用GraphQL Aggregate查询，不用分页接口的totalResults。中途失败回退时，除回退镜像外，还必须还原初始数据卷备份，不能让旧镜像直接读新版本写过的卷。

失败风险：备份丢权限、拿分页大小当总量，或只退镜像不还原卷。

预期行为/路由：answered / MULTI；小问数：3。

- **vital 1**：离线复制备份数据卷时使用cp -a。
  - 必需组1（组内OR）：
    - [self-host/deploy/troubleshooting/weaviate-server-migration-path L51–51](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-server-migration-path.mdx#L51-L51) · `self-host/deploy/troubleshooting/weaviate-server-migration-path#c4` · `self-host/deploy/troubleshooting/weaviate-server-migration-path#p2`：`cp -a` 会保留属主、权限和时间戳。用 `sudo` 执行的普通 `cp -r` 会改写这些属性，可能导致还原后的数据卷无法被 Weaviate 容器读取。
- **vital 2**：对象总量使用GraphQL的Aggregate查询。
  - 必需组1（组内OR）：
    - [self-host/deploy/troubleshooting/weaviate-server-migration-path L210–210](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-server-migration-path.mdx#L210-L210) · `self-host/deploy/troubleshooting/weaviate-server-migration-path#c18` · `self-host/deploy/troubleshooting/weaviate-server-migration-path#p7`：不要用 `GET /v1/objects?class=...&limit=1` 统计对象数量。它的 `totalResults` 字段返回的是当前页的大小，而不是集合的总量，因此 `limit=1` 时永远显示 `1`。请使用上面的 `Aggregate` 查询。
- **vital 3**：失败回退时还原初始备份的数据卷。
  - 必需组1（组内OR）：
    - [self-host/deploy/troubleshooting/weaviate-server-migration-path L217–217](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-server-migration-path.mdx#L217-L217) · `self-host/deploy/troubleshooting/weaviate-server-migration-path#c19` · `self-host/deploy/troubleshooting/weaviate-server-migration-path#p8`：启动 Dify 1.17.1 前，先把 Weaviate 镜像改回 `semitechnologies/weaviate:1.27.0`，然后还原初始备份：

## dev027 · multi/chain

自建Dify邮件助理第8课里，检索后是什么、上线前哪些内置凭据要换？

参考答案：第8课在知识检索后接Product Support Agent，使用从空白开始的新Agent。其节点说明要求生产使用前，把DIFY_AGENT_SERVER_SECRET_KEY和DIFY_AGENT_API_TOKEN换成自己的随机值。

失败风险：只停在课程摘要，或查到经典Agent配置而遗漏新Agent运行时凭据。

预期行为/路由：answered / MULTI；小问数：2。

- **vital 1**：检索后接Product Support Agent，即新Agent节点。
  - 必需组1（组内OR）：
    - [learn/tutorials/workflow-101/lesson-08 L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/learn/tutorials/workflow-101/lesson-08.mdx#L42-L42) · `learn/tutorials/workflow-101/lesson-08#c3` · `learn/tutorials/workflow-101/lesson-08#p2`：完成本课后，整个工作流就是：`开始 → 知识检索 → Product Support Agent → 输出`
  - 必需组2（组内OR）：
    - [learn/tutorials/workflow-101/lesson-08 L60–60](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/learn/tutorials/workflow-101/lesson-08.mdx#L60-L60) · `learn/tutorials/workflow-101/lesson-08#c4` · `learn/tutorials/workflow-101/lesson-08#p3`：在知识检索节点之后点击 **+**，选择 **Agent**，再选择 **从空白开始**。
- **vital 2**：生产前需替换的凭据集合是DIFY_AGENT_SERVER_SECRET_KEY和DIFY_AGENT_API_TOKEN。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/agent L135–135](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/agent.mdx#L135-L135) · `self-host/use-dify/nodes/agent#c11` · `self-host/use-dify/nodes/agent#p9`：生产环境使用前，将 [`DIFY_AGENT_SERVER_SECRET_KEY`](/zh/self-host/deploy/configuration/environments#dify_agent_server_secret_key) 和 [`DIFY_AGENT_API_TOKEN`](/zh/self-host/deploy/configuration/environments#dify_agent_api_token) 替换为你自己的随机值。

## dev028 · multi/parallel_compare

停止对话为何可能成功却没停，工作流日志接口能给逐节点记录吗？

参考答案：停止时的user若与发起回复时不一致，操作会被静默忽略，虽返回成功也没停。工作流日志接口给运行级汇总，不是逐节点日志。

失败风险：把成功响应等同停止生效，或把运行级汇总当逐节点追踪。

预期行为/路由：answered / MULTI；小问数：2。

- **vital 1**：停止接口user不匹配时会被静默忽略。
  - 必需组1（组内OR）：
    - [api-reference/guides/end-user-identity L19–19](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/end-user-identity.mdx#L19-L19) · `api-reference/guides/end-user-identity#c1` · `api-reference/guides/end-user-identity#p1`：- **停止生成**：对话类应用的停止接口仅在 `user` 与发起回复的用户一致时生效。不一致时会被静默忽略：调用同样会成功，因此无法从响应中察觉。
- **vital 2**：工作流日志接口只返回运行级汇总，不提供逐节点执行日志。
  - 必需组1（组内OR）：
    - [api-reference/guides/workflow L55–55](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/workflow.mdx#L55-L55) · `api-reference/guides/workflow#c5` · `api-reference/guides/workflow#p4`：- **[获取工作流日志](/zh/api-reference/workflow-runs/list-workflow-logs)**：返回运行级别的汇总信息（状态、token 用量、步骤数、耗时），而非逐节点的执行日志；可按关键词、状态、时间范围或触发运行的用户筛选。

## dev029 · multi/parallel_compare

按语义和按字段规则分流分别选什么节点；后者怎样按顺序增设后续分支？

参考答案：语义分类用问题分类器，由大语言模型理解输入并选择分类；字段规则用If-Else评估变量条件。若IF不满足，可添加多个ELIF分支，按顺序检查附加条件。

失败风险：只答两个节点名字，遗漏多ELIF及IF为假后顺序检查。

预期行为/路由：answered / MULTI；小问数：3。

- **vital 1**：按输入语义判断分类应选问题分类器。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/question-classifier L7–7](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/question-classifier.mdx#L7-L7) · `self-host/use-dify/nodes/question-classifier#c0` · `self-host/use-dify/nodes/question-classifier#p0`：问题分类器节点对用户输入进行智能分类，将对话路由到不同的工作流路径。无需构建复杂的条件逻辑，只需定义分类，让大语言模型基于语义理解判断最契合的一项。
- **vital 2**：按预定义变量条件判断分支应选If-Else。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/ifelse L8–8](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/ifelse.mdx#L8-L8) · `self-host/use-dify/nodes/ifelse#c0` · `self-host/use-dify/nodes/ifelse#p0`：If-Else 节点通过根据你定义的条件将执行路由到不同路径，为你的工作流添加决策逻辑。它评估变量并确定你的工作流应该遵循哪个分支。
- **vital 3**：If-Else可以添加多个ELIF分支，在IF为假后按顺序检查附加条件。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/ifelse L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/ifelse.mdx#L20-L20) · `self-host/use-dify/nodes/ifelse#c1` · `self-host/use-dify/nodes/ifelse#p1`：**ELIF 路径** 在 IF 条件为假时提供按顺序检查的附加条件。你可以添加多个 ELIF 分支来处理复杂逻辑。

## dev030 · multi/parallel_compare

知识流水线授权数据源：云版默认OAuth客户端要准备什么？自部署要先备什么、在Dify里填什么？

参考答案：云版默认OAuth客户端使用Dify预先配置并维护的参数，无需额外设置即可添加凭据。自部署文档给出的流程是先在第三方平台注册OAuth应用，再在Dify的自定义客户端设置里填入Client ID和Client Secret。云版也提供自定义方式，这里比较的是云版默认客户端与自部署文档给出的流程。

失败风险：把云版默认参数套给自部署，或漏掉第三方应用注册与Client ID/Client Secret。

预期行为/路由：answered / MULTI；小问数：3。

- **vital 1**：云版默认OAuth客户端使用Dify预置并维护的参数，无需额外设置。
  - 必需组1（组内OR）：
    - [cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source L100–100](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx#L100-L100) · `cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source#c6` · `cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source#p6`：默认客户端使用 Dify 预先配置并维护的 OAuth 参数，无需任何额外设置，即可一键添加凭据。
- **vital 2**：自部署授权数据源前需先在第三方平台注册OAuth应用。
  - 必需组1（组内OR）：
    - [self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source L92–92](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx#L92-L92) · `self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source#c6` · `self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source#p6`：先在第三方平台注册一个 OAuth 应用
- **vital 3**：自部署在Dify自定义客户端中填写Client ID和Client Secret。
  - 必需组1（组内OR）：
    - [self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source L105–105](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx#L105-L105) · `self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source#c7` · `self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source#p6`：输入 **Client ID** 和 **Client Secret**

## dev031 · refuse_correct/out_of_database

Webhook重复投递时，平台按哪个字段去重、记录留多久？

参考答案：冻结资料没有规定Webhook内置去重键或去重记录保留期，无法给出这两个具体参数。这只能说明资料不足，不能推出产品一定没有去重。

失败风险：编造event_id或24小时等默认值。

预期行为/路由：refused / None；小问数：2。

- 边界反证、可接受行为与不同解释见evidence.json该题。

## dev032 · refuse_correct/false_premise

模板表单会强制执行required，只标必填就能挡住空提交，对吗？

参考答案：不对。模板表单里的HTML5验证属性required不会强制生效，不能仅凭该属性保证拦住空提交。这里不把结论扩展到其他节点或服务端自定义验证。

失败风险：把浏览器普通HTML表单行为套到Dify模板表单。

预期行为/路由：corrects_premise / None；小问数：1。

- 边界反证、可接受行为与不同解释见evidence.json该题。
