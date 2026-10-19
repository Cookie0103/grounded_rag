# 第一批12题 · 修订版

日期：2026-10-19。冻结语料：langgenius/dify-docs @ c80a31868611b673bd77725a6310c685068a585e（CC BY 4.0）。

这些题计入新70道开发题，旧20题另作回归，30道测试题保持隔离。本轮只制作题目与独立参考依据，没有运行RAG、基线或评分。所有guessable_without_docs均为null，留待无检索基线回填。

原文行号、块和父块已按本地182篇语料核对。语义难度与链式独立性仍待Claude/作者审题，静态检查不能证明Naive RAG一定答不出。

**运行前的限制**：孪生来源在gold_doc_groups中按组内OR列为等价金标；gold_docs只保留每组代表。现有加载器会忽略OR字段，正式评分前必须适配，不能直接拿默认Recall@5当正式分数。纠正前提没有独立路由，dev032的expected_route为null，需评最终纠正行为。

| ID | 行为 / 子类 | 小问数 | vital数 | 预期路由 | 题目 |
|---|---|---:|---:|---|---|
| dev021 | 单跳 / 短问 | 1 | 1 | SINGLE | Workflow受理信号是哪帧？ |
| dev022 | 单跳 / 同义改写 | 1 | 2 | SINGLE | 不重跑前面的步骤，怎么换一份中间结果只测后面的步骤？ |
| dev023 | 单跳 / 数值/配置/表格 | 1 | 3 | SINGLE | 外部知识检索请求体的顶层必填字段有哪些？ |
| dev024 | 单跳 / 相邻易混 | 1 | 1 | SINGLE | 一批独立输入逐项处理，失败后要占位续跑，怎么配？ |
| dev025 | 多跳 / 分散证据/有序步骤 | 3 | 3 | MULTI | 云版知识库存储按什么计量、满额还能编辑分段吗、删文档后为何额度没立刻降？ |
| dev026 | 多跳 / 分散证据/有序步骤 | 3 | 3 | MULTI | 启动Dify1.17.1前，Weaviate逐级升级时，备份用什么复制选项、总量用哪种查询、失败回退时数据卷怎么办？ |
| dev027 | 多跳 / 链式 | 2 | 2 | MULTI | 自建Dify邮件助理第8课里，检索后是什么、上线前哪些内置凭据要换？ |
| dev028 | 多跳 / 并列跨篇/比较 | 2 | 2 | MULTI | 停止对话为何可能成功却没停，工作流日志接口能给逐节点记录吗？ |
| dev029 | 多跳 / 并列跨篇/比较 | 2 | 2 | MULTI | 按语义分流和按字段规则分流，分别选什么节点？ |
| dev030 | 多跳 / 并列跨篇/比较 | 2 | 4 | MULTI | Sandbox与社区版建即用型知识库时，批量文件数和单文件大小各上限多少？ |
| dev031 | 拒答与纠正 / 库内缺依据 | 2 | 0 | REFUSE | Webhook重复投递时，平台按哪个字段去重、记录留多久？ |
| dev032 | 拒答与纠正 / 错误前提 | 1 | 0 | null：纠正前提 | 模板表单会强制执行required，只标必填就能挡住空提交，对吗？ |

## dev021 · Workflow受理信号是哪帧？

**参考答案**：应等到首个data事件workflow_started。第一帧ping只用于保活，不能当作业务受理信号。

行为：单跳；子类：短问；edition：null；小问数：1。

**必答点与依据**：

- **vital**：首个data事件workflow_started表示Workflow运行已受理。
  - [原文L27–27](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx#L27-L27)；子块 `api-reference/guides/streaming#c2`；父块 `api-reference/guides/streaming#p2`。原句：Chatflow 应用和 Workflow 应用的事件流第一帧固定是 `ping`，运行期间还会约每 10 秒到达一次。不要把第一帧当作运行已受理的信号，应以第一个 `data:` 事件（`workflow_started`）为准。
- **okay**：第一帧ping只表示连接保活。
  - [原文L27–27](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx#L27-L27)；子块 `api-reference/guides/streaming#c2`；父块 `api-reference/guides/streaming#p2`。原句：Chatflow 应用和 Workflow 应用的事件流第一帧固定是 `ping`，运行期间还会约每 10 秒到达一次。不要把第一帧当作运行已受理的信号，应以第一个 `data:` 事件（`workflow_started`）为准。

**最可能失败**：把HTTP连接或ping当成运行已受理。

**审题说明**：保留为短问校准题；同一句中的受理判断只设一个vital，不假称多跳。

## dev022 · 不重跑前面的步骤，怎么换一份中间结果只测后面的步骤？

**参考答案**：在底部变量检查器中编辑可修改的中间变量值，再单独运行下游节点；下游用改后的值，不必重跑前面的步骤。

行为：单跳；子类：同义改写；edition：null；小问数：1。

**必答点与依据**：

- **vital**：在变量检查器中编辑可修改的中间变量值。
  - [原文L15–15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L15-L15)；子块 `self-host/use-dify/debug/variable-inspect#c1`；父块 `self-host/use-dify/debug/variable-inspect#p1`。原句：任何节点运行后，其输出变量会出现在屏幕底部的检查器面板中。点击任何变量可查看其完整内容。
  - [原文L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L23-L23)；子块 `self-host/use-dify/debug/variable-inspect#c2`；父块 `self-host/use-dify/debug/variable-inspect#p2`。原句：你可以通过点击大多数变量值来编辑它们。当你运行下游节点时，它们将使用你编辑的值而不是原始值。这让你可以测试不同场景，而无需重新运行整个工作流。
- **vital**：单独运行下游节点时会使用编辑后的值，无需重跑上游。
  - [原文L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L23-L23)；子块 `self-host/use-dify/debug/variable-inspect#c2`；父块 `self-host/use-dify/debug/variable-inspect#p2`。原句：你可以通过点击大多数变量值来编辑它们。当你运行下游节点时，它们将使用你编辑的值而不是原始值。这让你可以测试不同场景，而无需重新运行整个工作流。

**最可能失败**：只会全流程重跑或修改节点配置。

**审题说明**：两个vital分别是修改位置和下游运行语义，不把同一事实换句话说两遍。

## dev023 · 外部知识检索请求体的顶层必填字段有哪些？

**参考答案**：顶层必填字段有knowledge_id、query、retrieval_setting。嵌套参数不算顶层字段。

行为：单跳；子类：数值/配置/表格；edition：null；小问数：1。

**必答点与依据**：

- **vital**：顶层必填字段包括knowledge_id。
  - [原文L34–34](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L34-L34)；子块 `self-host/use-dify/knowledge/external-knowledge-api#c3`；父块 `self-host/use-dify/knowledge/external-knowledge-api#p3`。原句：| `knowledge_id` | 是 | string | 外部系统中知识源的标识符，即连接时填写的 **外部知识库 ID** 字段的值，用于将查询路由到正确的知识源。 |
  - [原文L34–34](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/external-knowledge-api.mdx#L34-L34)；子块 `cloud/use-dify/knowledge/external-knowledge-api#c3`；父块 `cloud/use-dify/knowledge/external-knowledge-api#p3`。原句：| `knowledge_id` | 是 | string | 外部系统中知识源的标识符，即连接时填写的 **外部知识库 ID** 字段的值，用于将查询路由到正确的知识源。 |
  - 上述来源等价，命中其中一项即可。
- **vital**：顶层必填字段包括query。
  - [原文L35–35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L35-L35)；子块 `self-host/use-dify/knowledge/external-knowledge-api#c3`；父块 `self-host/use-dify/knowledge/external-knowledge-api#p3`。原句：| `query` | 是 | string | 用户的搜索查询。 |
  - [原文L35–35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/external-knowledge-api.mdx#L35-L35)；子块 `cloud/use-dify/knowledge/external-knowledge-api#c3`；父块 `cloud/use-dify/knowledge/external-knowledge-api#p3`。原句：| `query` | 是 | string | 用户的搜索查询。 |
  - 上述来源等价，命中其中一项即可。
- **vital**：顶层必填字段包括retrieval_setting。
  - [原文L36–36](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L36-L36)；子块 `self-host/use-dify/knowledge/external-knowledge-api#c3`；父块 `self-host/use-dify/knowledge/external-knowledge-api#p3`。原句：| `retrieval_setting` | 是 | object | 检索参数。详见 [下文](#retrieval_setting)。 |
  - [原文L36–36](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/external-knowledge-api.mdx#L36-L36)；子块 `cloud/use-dify/knowledge/external-knowledge-api#c3`；父块 `cloud/use-dify/knowledge/external-knowledge-api#p3`。原句：| `retrieval_setting` | 是 | object | 检索参数。详见 [下文](#retrieval_setting)。 |
  - 上述来源等价，命中其中一项即可。

**最可能失败**：把top_k等嵌套参数误列为顶层字段。

**审题说明**：gold_doc_groups组内OR：任一等价来源命中即可，不要求两版同时召回；现有平面gold_docs仅保留代表来源，正式评分前需适配OR组。

## dev024 · 一批独立输入逐项处理，失败后要占位续跑，怎么配？

**参考答案**：用迭代节点，错误处理选“错误时继续”；失败项保留null占位，其余项继续。

行为：单跳；子类：相邻易混；edition：null；小问数：1。

**必答点与依据**：

- **vital**：采用迭代节点的“错误时继续”处理策略。
  - [原文L8–8](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/iteration.mdx#L8-L8)；子块 `self-host/use-dify/nodes/iteration#c0`；父块 `self-host/use-dify/nodes/iteration#p0`。原句：迭代节点通过对每个元素按顺序或并行运行相同的工作流步骤来处理数组。用于批处理任务，这些任务若作为单一操作会遇到限制或效率低下的问题。
  - [原文L73–73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/iteration.mdx#L73-L73)；子块 `self-host/use-dify/nodes/iteration#c5`；父块 `self-host/use-dify/nodes/iteration#p5`。原句：**错误时继续** - 跳过失败的项目并继续处理，为失败的元素输出 null
- **okay**：失败元素的结果用null占位。
  - [原文L73–73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/iteration.mdx#L73-L73)；子块 `self-host/use-dify/nodes/iteration#c5`；父块 `self-host/use-dify/nodes/iteration#p5`。原句：**错误时继续** - 跳过失败的项目并继续处理，为失败的元素输出 null

**相邻干扰**：迭代逐项处理数组；循环的后一步基于前一步结果。占位续跑在迭代页“错误时继续”明示。

干扰原句：[出处](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/loop.mdx#L8-L8)：循环节点执行重复性工作流，每个循环都基于前一个循环的结果进行构建。与迭代处理数组元素独立不同，循环创建的是随着每次重复而演进的渐进式工作流。（`self-host/use-dify/nodes/loop#c0`，父块`self-host/use-dify/nodes/loop#p0`）。

**最可能失败**：把循环当独立数组处理，或误选移除失败结果。

**审题说明**：配置选择只设一个vital；占位结果用于复核，不再拆成第二个得分点。

## dev025 · 云版知识库存储按什么计量、满额还能编辑分段吗、删文档后为何额度没立刻降？

**参考答案**：按文档产生的向量数量计量。满额会拦截编辑分段。删文档后账单用量延迟刷新，资料没有给出固定刷新秒数。

行为：多跳；子类：分散证据/有序步骤；edition：cloud；小问数：3。

**必答点与依据**：

- **vital**：存储用量取决于文档产生的向量数量。
  - [原文L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L23-L23)；子块 `cloud/use-dify/knowledge/knowledge-storage-limit#c1`；父块 `cloud/use-dify/knowledge/knowledge-storage-limit#p1`。原句：用量取决于文档产生的向量数量，而非文件本身的大小。分段越多，产生的向量就越多。
- **vital**：额度满时，编辑分段会被拦截。
  - [原文L49–49](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L49-L49)；子块 `cloud/use-dify/knowledge/knowledge-storage-limit#c3`；父块 `cloud/use-dify/knowledge/knowledge-storage-limit#p3`。原句：上传文档、新增或编辑分段、恢复已归档文档，以及修改分段设置等重新索引操作都会被拦截，以 **经济** 方式索引的知识库也不例外。
- **vital**：删除后账单用量数字延迟刷新。
  - [原文L59–59](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L59-L59)；子块 `cloud/use-dify/knowledge/knowledge-storage-limit#c4`；父块 `cloud/use-dify/knowledge/knowledge-storage-limit#p4`。原句：**设置** > **账单** 中的用量数字延迟刷新，删除后要过一段时间才会下降。

**分散父块**：3个（只数代表来源，不靠云/本地等价文档充数）。

**最可能失败**：按文件体积算用量或凭数字未降就断言删除无效。

## dev026 · 启动Dify1.17.1前，Weaviate逐级升级时，备份用什么复制选项、总量用哪种查询、失败回退时数据卷怎么办？

**参考答案**：离线备份用cp -a保留数据卷属性；总对象数用GraphQL Aggregate查询，不用分页接口的totalResults。中途失败回退时，除回退镜像外，还必须还原初始数据卷备份，不能让旧镜像直接读新版本写过的卷。

行为：多跳；子类：分散证据/有序步骤；edition：null；小问数：3。

**必答点与依据**：

- **vital**：离线复制备份数据卷时使用cp -a。
  - [原文L51–51](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-server-migration-path.mdx#L51-L51)；子块 `self-host/deploy/troubleshooting/weaviate-server-migration-path#c4`；父块 `self-host/deploy/troubleshooting/weaviate-server-migration-path#p2`。原句：`cp -a` 会保留属主、权限和时间戳。用 `sudo` 执行的普通 `cp -r` 会改写这些属性，可能导致还原后的数据卷无法被 Weaviate 容器读取。
- **vital**：对象总量使用GraphQL的Aggregate查询。
  - [原文L210–210](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-server-migration-path.mdx#L210-L210)；子块 `self-host/deploy/troubleshooting/weaviate-server-migration-path#c18`；父块 `self-host/deploy/troubleshooting/weaviate-server-migration-path#p7`。原句：不要用 `GET /v1/objects?class=...&limit=1` 统计对象数量。它的 `totalResults` 字段返回的是当前页的大小，而不是集合的总量，因此 `limit=1` 时永远显示 `1`。请使用上面的 `Aggregate` 查询。
- **vital**：失败回退时还原初始备份的数据卷。
  - [原文L217–217](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-server-migration-path.mdx#L217-L217)；子块 `self-host/deploy/troubleshooting/weaviate-server-migration-path#c19`；父块 `self-host/deploy/troubleshooting/weaviate-server-migration-path#p8`。原句：启动 Dify 1.17.1 前，先把 Weaviate 镜像改回 `semitechnologies/weaviate:1.27.0`，然后还原初始备份：

**分散父块**：3个（只数代表来源，不靠云/本地等价文档充数）。

**最可能失败**：备份丢权限、拿分页大小当总量，或只退镜像不还原卷。

**审题说明**：替换原dev026。三条必答点来自备份、逐级验证、回滚三个不同父块；不要求背未问的全套命令。

## dev027 · 自建Dify邮件助理第8课里，检索后是什么、上线前哪些内置凭据要换？

**参考答案**：第8课在知识检索后接Product Support Agent，使用从空白开始的新Agent。其节点说明要求生产使用前，把DIFY_AGENT_SERVER_SECRET_KEY和DIFY_AGENT_API_TOKEN换成自己的随机值。

行为：多跳；子类：链式；edition：null；小问数：2。

**必答点与依据**：

- **vital**：检索后接Product Support Agent，即新Agent节点。
  - [原文L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/learn/tutorials/workflow-101/lesson-08.mdx#L42-L42)；子块 `learn/tutorials/workflow-101/lesson-08#c3`；父块 `learn/tutorials/workflow-101/lesson-08#p2`。原句：完成本课后，整个工作流就是：`开始 → 知识检索 → Product Support Agent → 输出`
  - [原文L60–60](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/learn/tutorials/workflow-101/lesson-08.mdx#L60-L60)；子块 `learn/tutorials/workflow-101/lesson-08#c4`；父块 `learn/tutorials/workflow-101/lesson-08#p3`。原句：在知识检索节点之后点击 **+**，选择 **Agent**，再选择 **从空白开始**。
- **vital**：生产前需替换的凭据集合是DIFY_AGENT_SERVER_SECRET_KEY和DIFY_AGENT_API_TOKEN。
  - [原文L135–135](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/agent.mdx#L135-L135)；子块 `self-host/use-dify/nodes/agent#c11`；父块 `self-host/use-dify/nodes/agent#p9`。原句：生产环境使用前，将 [`DIFY_AGENT_SERVER_SECRET_KEY`](/zh/self-host/deploy/configuration/environments#dify_agent_server_secret_key) 和 [`DIFY_AGENT_API_TOKEN`](/zh/self-host/deploy/configuration/environments#dify_agent_api_token) 替换为你自己的随机值。

**链式桥接**：指定课程和检索后位置只在第一篇确定组件；第一篇不给两个凭据字段。第二篇不知道第8课用哪个组件。课程明确从空白创建，无需选择经典推理策略，对应新Agent小节。

第一篇：`learn/tutorials/workflow-101/lesson-08` → 新Agent / Product Support Agent → 第二篇：`self-host/use-dify/nodes/agent`。

第二篇答案相关关键词（已核对题干均不含）：`Agent`、`新 Agent`、`DIFY_AGENT_SERVER_SECRET_KEY`、`DIFY_AGENT_API_TOKEN`、`Docker Compose`、`随机值`。

**最可能失败**：只停在课程摘要，或查到经典Agent配置而遗漏新Agent运行时凭据。

**审题说明**：替换原dev027；关键词来自第二篇相关小节，题干不提供Agent、密钥字段或运行时名称。

## dev028 · 停止对话为何可能成功却没停，工作流日志接口能给逐节点记录吗？

**参考答案**：停止时的user若与发起回复时不一致，操作会被静默忽略，虽返回成功也没停。工作流日志接口给运行级汇总，不是逐节点日志。

行为：多跳；子类：并列跨篇/比较；edition：null；小问数：2。

**必答点与依据**：

- **vital**：停止接口user不匹配时会被静默忽略。
  - [原文L19–19](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/end-user-identity.mdx#L19-L19)；子块 `api-reference/guides/end-user-identity#c1`；父块 `api-reference/guides/end-user-identity#p1`。原句：- **停止生成**：对话类应用的停止接口仅在 `user` 与发起回复的用户一致时生效。不一致时会被静默忽略：调用同样会成功，因此无法从响应中察觉。
- **vital**：工作流日志接口只返回运行级汇总，不提供逐节点执行日志。
  - [原文L55–55](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/workflow.mdx#L55-L55)；子块 `api-reference/guides/workflow#c5`；父块 `api-reference/guides/workflow#p4`。原句：- **[获取工作流日志](/zh/api-reference/workflow-runs/list-workflow-logs)**：返回运行级别的汇总信息（状态、token 用量、步骤数、耗时），而非逐节点的执行日志；可按关键词、状态、时间范围或触发运行的用户筛选。

**最可能失败**：把成功响应等同停止生效，或把运行级汇总当逐节点追踪。

**审题说明**：原dev028前两条合并成一个条件事实，不重复计分。

## dev029 · 按语义分流和按字段规则分流，分别选什么节点？

**参考答案**：语义分类选问题分类器，由大语言模型理解输入并挑选分类；明确字段或变量的比较规则选If-Else。

行为：多跳；子类：并列跨篇/比较；edition：null；小问数：2。

**必答点与依据**：

- **vital**：按输入语义判断分类应选问题分类器。
  - [原文L7–7](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/question-classifier.mdx#L7-L7)；子块 `self-host/use-dify/nodes/question-classifier#c0`；父块 `self-host/use-dify/nodes/question-classifier#p0`。原句：问题分类器节点对用户输入进行智能分类，将对话路由到不同的工作流路径。无需构建复杂的条件逻辑，只需定义分类，让大语言模型基于语义理解判断最契合的一项。
- **vital**：按预定义变量条件判断分支应选If-Else。
  - [原文L8–8](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/ifelse.mdx#L8-L8)；子块 `self-host/use-dify/nodes/ifelse#c0`；父块 `self-host/use-dify/nodes/ifelse#p0`。原句：If-Else 节点通过根据你定义的条件将执行路由到不同路径，为你的工作流添加决策逻辑。它评估变量并确定你的工作流应该遵循哪个分支。

**最可能失败**：混淆模型语义分类与确定性的条件比较。

**审题说明**：重写dev029，移除与dev022重复的调试改值事实。两篇各给一种选择的依据。

## dev030 · Sandbox与社区版建即用型知识库时，批量文件数和单文件大小各上限多少？

**参考答案**：Sandbox：每批最多1个文件、单个最大15 MB。社区版默认：每批最多5个文件、单个最大15 MB；社区版可通过相应环境变量调整，故这里报文档默认值。

行为：多跳；子类：并列跨篇/比较；edition：null；小问数：2。

**必答点与依据**：

- **vital**：Sandbox单次上传上限为1个文件。
  - [原文L21–21](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/create-knowledge/import-text-data/readme.mdx#L21-L21)；子块 `cloud/use-dify/knowledge/create-knowledge/import-text-data/readme#c0`；父块 `cloud/use-dify/knowledge/create-knowledge/import-text-data/readme#p0`。原句：| 单次上传文件数 | 1 | 50 |
- **vital**：Sandbox单文件大小上限为15 MB。
  - [原文L22–22](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/create-knowledge/import-text-data/readme.mdx#L22-L22)；子块 `cloud/use-dify/knowledge/create-knowledge/import-text-data/readme#c0`；父块 `cloud/use-dify/knowledge/create-knowledge/import-text-data/readme#p0`。原句：| 单个文件大小 | 15 MB | 50 MB |
- **vital**：社区版默认单次上传上限为5个文件。
  - [原文L17–17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/readme.mdx#L17-L17)；子块 `self-host/use-dify/knowledge/create-knowledge/import-text-data/readme#c0`；父块 `self-host/use-dify/knowledge/create-knowledge/import-text-data/readme#p0`。原句：- 单次最多可上传 5 个文件（通过 `UPLOAD_FILE_BATCH_LIMIT` 设置）
- **vital**：社区版默认单文件大小上限为15 MB。
  - [原文L19–19](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/readme.mdx#L19-L19)；子块 `self-host/use-dify/knowledge/create-knowledge/import-text-data/readme#c0`；父块 `self-host/use-dify/knowledge/create-knowledge/import-text-data/readme#p0`。原句：- 单个文件最大支持 15 MB（通过 `UPLOAD_FILE_SIZE_LIMIT` 设置）

**版本对照原句**：

- [cloud/use-dify/knowledge/create-knowledge/import-text-data/readme L21](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/create-knowledge/import-text-data/readme.mdx#L21-L21)：| 单次上传文件数 | 1 | 50 |
- [self-host/use-dify/knowledge/create-knowledge/import-text-data/readme L17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/readme.mdx#L17-L17)：- 单次最多可上传 5 个文件（通过 `UPLOAD_FILE_BATCH_LIMIT` 设置）

**最可能失败**：把云版付费套餐50个/50 MB套给Sandbox，或混用社区默认值。

**审题说明**：重写dev030为真正跨两版对照，不再拿云版登录的一句话充多跳。每个限制各自计一个vital；edition为null，版本由题干给出。

## dev031 · Webhook重复投递时，平台按哪个字段去重、记录留多久？

**参考答案**：冻结资料没有规定Webhook内置去重键或去重记录保留期，无法给出这两个具体参数。这只能说明资料不足，不能推出产品一定没有去重。

行为：拒答与纠正；子类：库内缺依据；edition：null；小问数：2。

**必答点与依据**：

按边界行为检查，不用空nuggets算满分。预期：refused。
- 边界依据：[原文L32–32](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/trigger/webhook-trigger.mdx#L32-L32)；`self-host/use-dify/nodes/trigger/webhook-trigger#c1`；父块 `self-host/use-dify/nodes/trigger/webhook-trigger#p0`。原句：3. 当订阅的事件发生时，外部系统会将包含事件数据的 HTTP 请求发送到先前提供的 webhook URL。一旦请求被成功接收和处理，你的 Workflow 会被触发，而提取到的事件数据也将成为下游节点可引用的变量。
- 边界依据：[原文L34–34](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/trigger/plugin-trigger.mdx#L34-L34)；`self-host/use-dify/nodes/trigger/plugin-trigger#c2`；父块 `self-host/use-dify/nodes/trigger/plugin-trigger#p2`。原句：订阅是一个用于监听外部系统事件的 webhook。每个触发器集成在每个工作空间中最多支持 10 个订阅。

**缺答案核查**：对全部182篇原文与清洗文本分别全文搜索，下列10项均为0命中：`去重键`、`事件去重`、`投递去重`、`幂等`、`去重窗口`、`去重记录`、`dedup`、`idempotency`、`event_id`、`delivery_id`。

- `self-host/use-dify/nodes/trigger/webhook-trigger`：说明请求触发、请求体变量和测试生产URL，未定义重复投递的去重键或保留期限。
- `self-host/use-dify/nodes/trigger/plugin-trigger`：说明集成事件订阅与webhook接收，未定义平台事件去重字段或窗口。
- `self-host/use-dify/nodes/trigger/overview`：说明触发方式和工作流入口，不含事件去重状态或保留策略。

**最可能失败**：编造event_id或24小时等默认值。

## dev032 · 模板表单会强制执行required，只标必填就能挡住空提交，对吗？

**参考答案**：不对。模板表单里的HTML5验证属性required不会强制生效，不能仅凭该属性保证拦住空提交。这里不把结论扩展到其他节点或服务端自定义验证。

行为：拒答与纠正；子类：错误前提；edition：null；小问数：1。

**必答点与依据**：

按边界行为检查，不用空nuggets算满分。预期：corrects_premise。
- 边界依据：[原文L151–151](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/template.mdx#L151-L151)；`self-host/use-dify/nodes/template#c13`；父块 `self-host/use-dify/nodes/template#p9`。原句：- HTML5 验证属性 `required`、`min`、`max` 和 `pattern` 不会强制生效。

**最可能失败**：把浏览器普通HTML表单行为套到Dify模板表单。

**审题说明**：替换常识安全题dev032，使用产品专有的模板表单例外。不给不存在的CORRECT路由标签。

## 给Claude的核查顺序

1. 先读requirements-review-v2.txt与revision-log.md，确认这次行为比例及修订要求。
2. 逐题读本审阅稿，再用evidence.json的原文行号、子块、父块复核。
3. 重点审三道链式题dev027/dev038/dev039的桥接是否必要；审dev023/dev033/dev041的等价来源和OR口径；审dev026/dev041/dev042的三个父块。
4. 用validation.json、twin-comparisons.json、fact-ledger.json检查机器条件和事实重复。不要用题型QUOTAS替代本次行为配额。
5. 仅审题，不跑RAG，不读封存30题。独立审题通过后再实现评分兼容并运行。
