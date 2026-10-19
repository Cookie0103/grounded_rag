# batch-01审阅稿

固定语料：langgenius/dify-docs @ c80a31868611b673bd77725a6310c685068a585e（CC BY 4.0）。新70为dev021～090，旧20独立回归。题目为交审草案，未运行完整系统、无检索基线或付费评分。原样单次检索的实际状态见validation.json和retrieval-selftest.jsonl。

等价来源组内OR、必要来源组间AND；现有正式评分加载器尚不保留gold_doc_groups。静态符合条件和候选召回不等于难度、答案效果或人工审核通过。

| ID | 行为 / 子类 | vital数 | 预期路由 | 题目 |
|---|---|---:|---|---|
| dev021 | 单跳 / 短问 | 2 | SINGLE | Workflow受理和结束各看哪帧？ |
| dev022 | 单跳 / 同义改写 | 2 | SINGLE | 不重跑前面的步骤，怎么换一份中间结果只测后面的步骤？ |
| dev023 | 单跳 / 数值/表格 | 3 | SINGLE | 外部知识检索请求体的顶层必填字段有哪些？ |
| dev024 | 单跳 / 易混 | 2 | SINGLE | 一批独立输入逐项处理，失败仍续跑怎么配，失败项输出什么？ |
| dev025 | 多跳 / 分散/有序 | 3 | MULTI | 云版知识库存储按什么计量、满额还能编辑分段吗、删文档后为何额度没立刻降？ |
| dev026 | 多跳 / 分散/有序 | 3 | MULTI | 启动Dify1.17.1前，Weaviate逐级升级时，备份用什么复制选项、总量用哪种查询、失败回退时数据卷怎么办？ |
| dev027 | 多跳 / 链式 | 2 | MULTI | 自建Dify邮件助理第8课里，检索后是什么、上线前哪些内置凭据要换？ |
| dev028 | 多跳 / 并列/比较 | 2 | MULTI | 停止对话为何可能成功却没停，工作流日志接口能给逐节点记录吗？ |
| dev029 | 多跳 / 并列/比较 | 3 | MULTI | 按语义和按字段规则分流分别选什么节点；后者怎样按顺序增设后续分支？ |
| dev030 | 多跳 / 并列/比较 | 4 | MULTI | 知识流水线接数据源做OAuth授权，云版默认客户端和自部署的准备流程有何不同？ |
| dev031 | 拒答与纠正 / 库内缺依据 | 0 | null | Webhook重复投递时，平台按哪个字段去重、记录留多久？ |
| dev032 | 拒答与纠正 / 错误前提 | 0 | null | 模板表单会强制执行required，只标必填就能挡住空提交，对吗？ |

## dev021：Workflow受理和结束各看哪帧？

参考答案：受理看首个data事件workflow_started；Workflow正常结束看workflow_finished。第一帧ping只是保活。

版本：未限定；预期行为：answered；最可能失败：将ping当受理信号，或把Chatbot的message_end套为Workflow终止事件。。

1. **vital**：首个data事件workflow_started表示Workflow运行已受理。
   - [api-reference/guides/streaming L27–27](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx#L27-L27)；`api-reference/guides/streaming#c2` / `api-reference/guides/streaming#p2`。

     > Chatflow 应用和 Workflow 应用的事件流第一帧固定是 `ping`，运行期间还会约每 10 秒到达一次。不要把第一帧当作运行已受理的信号，应以第一个 `data:` 事件（`workflow_started`）为准。

2. **vital**：Workflow应用以workflow_finished作为终止事件。
   - [api-reference/guides/streaming L78–78](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx#L78-L78)；`api-reference/guides/streaming#c5` / `api-reference/guides/streaming#p3`。

     >     - Workflow 应用为 `workflow_finished`

备注：改为明确询问受理与终止两个不同阶段；未把首帧ping和受理信号的正反表述充作独立事实。


## dev022：不重跑前面的步骤，怎么换一份中间结果只测后面的步骤？

参考答案：在底部变量检查器中编辑可修改的中间变量值，再单独运行下游节点；下游用改后的值，不必重跑前面的步骤。

版本：未限定；预期行为：answered；最可能失败：只会全流程重跑或修改节点配置。。

1. **vital**：在变量检查器中编辑可修改的中间变量值。
   - [self-host/use-dify/debug/variable-inspect L15–15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L15-L15)；`self-host/use-dify/debug/variable-inspect#c1` / `self-host/use-dify/debug/variable-inspect#p1`。

     > 任何节点运行后，其输出变量会出现在屏幕底部的检查器面板中。点击任何变量可查看其完整内容。

   - [self-host/use-dify/debug/variable-inspect L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L23-L23)；`self-host/use-dify/debug/variable-inspect#c2` / `self-host/use-dify/debug/variable-inspect#p2`。

     > 你可以通过点击大多数变量值来编辑它们。当你运行下游节点时，它们将使用你编辑的值而不是原始值。这让你可以测试不同场景，而无需重新运行整个工作流。

2. **vital**：单独运行下游节点时会使用编辑后的值，无需重跑上游。
   - [self-host/use-dify/debug/variable-inspect L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L23-L23)；`self-host/use-dify/debug/variable-inspect#c2` / `self-host/use-dify/debug/variable-inspect#p2`。

     > 你可以通过点击大多数变量值来编辑它们。当你运行下游节点时，它们将使用你编辑的值而不是原始值。这让你可以测试不同场景，而无需重新运行整个工作流。

备注：两个vital分别是修改位置和下游运行语义，不把同一事实换句话说两遍。


## dev023：外部知识检索请求体的顶层必填字段有哪些？

参考答案：顶层必填字段有knowledge_id、query、retrieval_setting。嵌套参数不算顶层字段。

版本：未限定；预期行为：answered；最可能失败：把top_k等嵌套参数误列为顶层字段。。

1. **vital**：顶层必填字段包括knowledge_id。
   等价来源（任一成立）：
   - [self-host/use-dify/knowledge/external-knowledge-api L34–34](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L34-L34)；`self-host/use-dify/knowledge/external-knowledge-api#c3` / `self-host/use-dify/knowledge/external-knowledge-api#p3`。

     > | `knowledge_id` | 是 | string | 外部系统中知识源的标识符，即连接时填写的 **外部知识库 ID** 字段的值，用于将查询路由到正确的知识源。 |

   - [cloud/use-dify/knowledge/external-knowledge-api L34–34](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/external-knowledge-api.mdx#L34-L34)；`cloud/use-dify/knowledge/external-knowledge-api#c3` / `cloud/use-dify/knowledge/external-knowledge-api#p3`。

     > | `knowledge_id` | 是 | string | 外部系统中知识源的标识符，即连接时填写的 **外部知识库 ID** 字段的值，用于将查询路由到正确的知识源。 |

2. **vital**：顶层必填字段包括query。
   等价来源（任一成立）：
   - [self-host/use-dify/knowledge/external-knowledge-api L35–35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L35-L35)；`self-host/use-dify/knowledge/external-knowledge-api#c3` / `self-host/use-dify/knowledge/external-knowledge-api#p3`。

     > | `query` | 是 | string | 用户的搜索查询。 |

   - [cloud/use-dify/knowledge/external-knowledge-api L35–35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/external-knowledge-api.mdx#L35-L35)；`cloud/use-dify/knowledge/external-knowledge-api#c3` / `cloud/use-dify/knowledge/external-knowledge-api#p3`。

     > | `query` | 是 | string | 用户的搜索查询。 |

3. **vital**：顶层必填字段包括retrieval_setting。
   等价来源（任一成立）：
   - [self-host/use-dify/knowledge/external-knowledge-api L36–36](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L36-L36)；`self-host/use-dify/knowledge/external-knowledge-api#c3` / `self-host/use-dify/knowledge/external-knowledge-api#p3`。

     > | `retrieval_setting` | 是 | object | 检索参数。详见 [下文](#retrieval_setting)。 |

   - [cloud/use-dify/knowledge/external-knowledge-api L36–36](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/external-knowledge-api.mdx#L36-L36)；`cloud/use-dify/knowledge/external-knowledge-api#c3` / `cloud/use-dify/knowledge/external-knowledge-api#p3`。

     > | `retrieval_setting` | 是 | object | 检索参数。详见 [下文](#retrieval_setting)。 |

备注：gold_doc_groups组内OR：任一等价来源命中即可，不要求两版同时召回；现有平面gold_docs仅保留代表来源，正式评分前需适配OR组。


## dev024：一批独立输入逐项处理，失败仍续跑怎么配，失败项输出什么？

参考答案：用迭代节点，错误处理选“错误时继续”；失败元素在输出数组中用null占位，其余项继续处理。

版本：未限定；预期行为：answered；最可能失败：把循环当独立数组处理，或误选移除失败结果。。

1. **vital**：采用迭代节点的“错误时继续”处理策略。
   - [self-host/use-dify/nodes/iteration L73–73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/iteration.mdx#L73-L73)；`self-host/use-dify/nodes/iteration#c5` / `self-host/use-dify/nodes/iteration#p5`。

     > **错误时继续** - 跳过失败的项目并继续处理，为失败的元素输出 null

2. **vital**：失败元素在输出数组中用null占位。
   - [self-host/use-dify/nodes/iteration L77–80](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/iteration.mdx#L77-L80)；`self-host/use-dify/nodes/iteration#c5` / `self-host/use-dify/nodes/iteration#p5`。

     > 输入输出对应示例：
     > - 输入：`[1, 2, 3]`
     > - 错误时继续的输出：`[result-1, null, result-3]`
     > - 移除失败的输出：`[result-1, result-3]`

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "distractor_docs": [
    "self-host/use-dify/nodes/loop"
  ]
}
```

</details>

备注：题干分别问配置选择和输出结构；两条vital是操作与结果表示，不是续跑/不终止的正反重复。


## dev025：云版知识库存储按什么计量、满额还能编辑分段吗、删文档后为何额度没立刻降？

参考答案：按文档产生的向量数量计量。满额会拦截编辑分段。删文档后账单用量延迟刷新，资料没有给出固定刷新秒数。

版本：cloud；预期行为：answered；最可能失败：按文件体积算用量或凭数字未降就断言删除无效。。

1. **vital**：存储用量取决于文档产生的向量数量。
   - [cloud/use-dify/knowledge/knowledge-storage-limit L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L23-L23)；`cloud/use-dify/knowledge/knowledge-storage-limit#c1` / `cloud/use-dify/knowledge/knowledge-storage-limit#p1`。

     > 用量取决于文档产生的向量数量，而非文件本身的大小。分段越多，产生的向量就越多。

2. **vital**：额度满时，编辑分段会被拦截。
   - [cloud/use-dify/knowledge/knowledge-storage-limit L49–49](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L49-L49)；`cloud/use-dify/knowledge/knowledge-storage-limit#c3` / `cloud/use-dify/knowledge/knowledge-storage-limit#p3`。

     > 上传文档、新增或编辑分段、恢复已归档文档，以及修改分段设置等重新索引操作都会被拦截，以 **经济** 方式索引的知识库也不例外。

3. **vital**：删除后账单用量数字延迟刷新。
   - [cloud/use-dify/knowledge/knowledge-storage-limit L59–59](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L59-L59)；`cloud/use-dify/knowledge/knowledge-storage-limit#c4` / `cloud/use-dify/knowledge/knowledge-storage-limit#p4`。

     > **设置** > **账单** 中的用量数字延迟刷新，删除后要过一段时间才会下降。


## dev026：启动Dify1.17.1前，Weaviate逐级升级时，备份用什么复制选项、总量用哪种查询、失败回退时数据卷怎么办？

参考答案：离线备份用cp -a保留数据卷属性；总对象数用GraphQL Aggregate查询，不用分页接口的totalResults。中途失败回退时，除回退镜像外，还必须还原初始数据卷备份，不能让旧镜像直接读新版本写过的卷。

版本：未限定；预期行为：answered；最可能失败：备份丢权限、拿分页大小当总量，或只退镜像不还原卷。。

1. **vital**：离线复制备份数据卷时使用cp -a。
   - [self-host/deploy/troubleshooting/weaviate-server-migration-path L51–51](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-server-migration-path.mdx#L51-L51)；`self-host/deploy/troubleshooting/weaviate-server-migration-path#c4` / `self-host/deploy/troubleshooting/weaviate-server-migration-path#p2`。

     > `cp -a` 会保留属主、权限和时间戳。用 `sudo` 执行的普通 `cp -r` 会改写这些属性，可能导致还原后的数据卷无法被 Weaviate 容器读取。

2. **vital**：对象总量使用GraphQL的Aggregate查询。
   - [self-host/deploy/troubleshooting/weaviate-server-migration-path L210–210](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-server-migration-path.mdx#L210-L210)；`self-host/deploy/troubleshooting/weaviate-server-migration-path#c18` / `self-host/deploy/troubleshooting/weaviate-server-migration-path#p7`。

     > 不要用 `GET /v1/objects?class=...&limit=1` 统计对象数量。它的 `totalResults` 字段返回的是当前页的大小，而不是集合的总量，因此 `limit=1` 时永远显示 `1`。请使用上面的 `Aggregate` 查询。

3. **vital**：失败回退时还原初始备份的数据卷。
   - [self-host/deploy/troubleshooting/weaviate-server-migration-path L217–217](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-server-migration-path.mdx#L217-L217)；`self-host/deploy/troubleshooting/weaviate-server-migration-path#c19` / `self-host/deploy/troubleshooting/weaviate-server-migration-path#p8`。

     > 启动 Dify 1.17.1 前，先把 Weaviate 镜像改回 `semitechnologies/weaviate:1.27.0`，然后还原初始备份：

备注：替换原dev026。三条必答点来自备份、逐级验证、回滚三个不同父块；不要求背未问的全套命令。


## dev027：自建Dify邮件助理第8课里，检索后是什么、上线前哪些内置凭据要换？

参考答案：第8课在知识检索后接Product Support Agent，使用从空白开始的新Agent。其节点说明要求生产使用前，把DIFY_AGENT_SERVER_SECRET_KEY和DIFY_AGENT_API_TOKEN换成自己的随机值。

版本：未限定；预期行为：answered；最可能失败：只停在课程摘要，或查到经典Agent配置而遗漏新Agent运行时凭据。。

1. **vital**：检索后接Product Support Agent，即新Agent节点。
   - [learn/tutorials/workflow-101/lesson-08 L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/learn/tutorials/workflow-101/lesson-08.mdx#L42-L42)；`learn/tutorials/workflow-101/lesson-08#c3` / `learn/tutorials/workflow-101/lesson-08#p2`。

     > 完成本课后，整个工作流就是：`开始 → 知识检索 → Product Support Agent → 输出`

   - [learn/tutorials/workflow-101/lesson-08 L60–60](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/learn/tutorials/workflow-101/lesson-08.mdx#L60-L60)；`learn/tutorials/workflow-101/lesson-08#c4` / `learn/tutorials/workflow-101/lesson-08#p3`。

     > 在知识检索节点之后点击 **+**，选择 **Agent**，再选择 **从空白开始**。

2. **vital**：生产前需替换的凭据集合是DIFY_AGENT_SERVER_SECRET_KEY和DIFY_AGENT_API_TOKEN。
   - [self-host/use-dify/nodes/agent L135–135](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/agent.mdx#L135-L135)；`self-host/use-dify/nodes/agent#c11` / `self-host/use-dify/nodes/agent#p9`。

     > 生产环境使用前，将 [`DIFY_AGENT_SERVER_SECRET_KEY`](/zh/self-host/deploy/configuration/environments#dify_agent_server_secret_key) 和 [`DIFY_AGENT_API_TOKEN`](/zh/self-host/deploy/configuration/environments#dify_agent_api_token) 替换为你自己的随机值。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "chain": {
    "first_document": "learn/tutorials/workflow-101/lesson-08",
    "bridge_entity": "新Agent / Product Support Agent",
    "second_document": "self-host/use-dify/nodes/agent",
    "second_document_answer_keywords": [
      "Agent",
      "新 Agent",
      "DIFY_AGENT_SERVER_SECRET_KEY",
      "DIFY_AGENT_API_TOKEN",
      "Docker Compose",
      "随机值"
    ],
    "dependency": "指定课程和检索后位置只在第一篇确定组件；第一篇不给两个凭据字段。第二篇不知道第8课用哪个组件。课程明确从空白创建，无需选择经典推理策略，对应新Agent小节。",
    "derived_query": "新Agent Docker Compose 生产环境 默认凭据"
  }
}
```

</details>

备注：替换原dev027；关键词来自第二篇相关小节，题干不提供Agent、密钥字段或运行时名称。


## dev028：停止对话为何可能成功却没停，工作流日志接口能给逐节点记录吗？

参考答案：停止时的user若与发起回复时不一致，操作会被静默忽略，虽返回成功也没停。工作流日志接口给运行级汇总，不是逐节点日志。

版本：未限定；预期行为：answered；最可能失败：把成功响应等同停止生效，或把运行级汇总当逐节点追踪。。

1. **vital**：停止接口user不匹配时会被静默忽略。
   - [api-reference/guides/end-user-identity L19–19](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/end-user-identity.mdx#L19-L19)；`api-reference/guides/end-user-identity#c1` / `api-reference/guides/end-user-identity#p1`。

     > - **停止生成**：对话类应用的停止接口仅在 `user` 与发起回复的用户一致时生效。不一致时会被静默忽略：调用同样会成功，因此无法从响应中察觉。

2. **vital**：工作流日志接口只返回运行级汇总，不提供逐节点执行日志。
   - [api-reference/guides/workflow L55–55](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/workflow.mdx#L55-L55)；`api-reference/guides/workflow#c5` / `api-reference/guides/workflow#p4`。

     > - **[获取工作流日志](/zh/api-reference/workflow-runs/list-workflow-logs)**：返回运行级别的汇总信息（状态、token 用量、步骤数、耗时），而非逐节点的执行日志；可按关键词、状态、时间范围或触发运行的用户筛选。

备注：原dev028前两条合并成一个条件事实，不重复计分。


## dev029：按语义和按字段规则分流分别选什么节点；后者怎样按顺序增设后续分支？

参考答案：语义分类用问题分类器，由大语言模型理解输入并选择分类；字段规则用If-Else评估变量条件。若IF不满足，可添加多个ELIF分支，按顺序检查附加条件。

版本：未限定；预期行为：answered；最可能失败：只答两个节点名字，遗漏多ELIF及IF为假后顺序检查。。

1. **vital**：按输入语义判断分类应选问题分类器。
   - [self-host/use-dify/nodes/question-classifier L7–7](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/question-classifier.mdx#L7-L7)；`self-host/use-dify/nodes/question-classifier#c0` / `self-host/use-dify/nodes/question-classifier#p0`。

     > 问题分类器节点对用户输入进行智能分类，将对话路由到不同的工作流路径。无需构建复杂的条件逻辑，只需定义分类，让大语言模型基于语义理解判断最契合的一项。

2. **vital**：按预定义变量条件判断分支应选If-Else。
   - [self-host/use-dify/nodes/ifelse L8–8](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/ifelse.mdx#L8-L8)；`self-host/use-dify/nodes/ifelse#c0` / `self-host/use-dify/nodes/ifelse#p0`。

     > If-Else 节点通过根据你定义的条件将执行路由到不同路径，为你的工作流添加决策逻辑。它评估变量并确定你的工作流应该遵循哪个分支。

3. **vital**：If-Else可以添加多个ELIF分支，在IF为假后按顺序检查附加条件。
   - [self-host/use-dify/nodes/ifelse L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/ifelse.mdx#L20-L20)；`self-host/use-dify/nodes/ifelse#c1` / `self-host/use-dify/nodes/ifelse#p1`。

     > **ELIF 路径** 在 IF 条件为假时提供按顺序检查的附加条件。你可以添加多个 ELIF 分支来处理复杂逻辑。

备注：重写dev029，移除与dev022重复的调试改值事实。两篇各给一种选择的依据。；冻结分类器页没有可据的类别数上限，因此采用If-Else的多ELIF与顺序检查细节，合计3条独立vital。


## dev030：知识流水线接数据源做OAuth授权，云版默认客户端和自部署的准备流程有何不同？

参考答案：云版默认客户端使用Dify预先配置并维护的OAuth参数，无需额外设置即可一键添加凭据。自部署文档给出的流程是先在第三方平台注册OAuth应用，再在Dify的自定义客户端设置中填写Client ID和Client Secret，点击“保存并授权”。云版也提供自定义方式，这里比较其默认方式与自部署文档的流程。

版本：未限定；预期行为：answered；最可能失败：把云版默认参数套给自部署，漏掉第三方应用注册或客户端凭据；反过来声称云版不能自定义。。

1. **vital**：云版默认OAuth客户端使用Dify预置并维护的参数，无需额外设置即可添加凭据。
   - [cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source L100–100](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx#L100-L100)；`cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source#c6` / `cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source#p6`。

     >     默认客户端使用 Dify 预先配置并维护的 OAuth 参数，无需任何额外设置，即可一键添加凭据。

2. **vital**：自部署授权数据源前需在第三方平台注册OAuth应用。
   - [self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source L92–92](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx#L92-L92)；`self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source#c6` / `self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source#p6`。

     > 使用自定义 OAuth 客户端授权数据源：先在第三方平台注册一个 OAuth 应用，再将其 **Client ID** 和 **Client Secret** 填入 Dify。当你有特定的安全或合规要求时，这种方式尤为适用。

3. **vital**：自部署在Dify自定义客户端中填写Client ID和Client Secret。
   - [self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source L105–105](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx#L105-L105)；`self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source#c7` / `self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source#p6`。

     > 2. 点击 **自定义**，输入 **Client ID** 和 **Client Secret**。点击 **保存并授权**完成 OAuth 授权流程。

4. **vital**：填写自定义客户端参数后，点击“保存并授权”完成OAuth授权。
   - [self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source L105–105](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx#L105-L105)；`self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source#c7` / `self-host/use-dify/knowledge/knowledge-pipeline/authorize-data-source#p6`。

     > 2. 点击 **自定义**，输入 **Client ID** 和 **Client Secret**。点击 **保存并授权**完成 OAuth 授权流程。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "boundary_evidence": [
    {
      "any_of": [
        {
          "document_id": "cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source",
          "heading_path": "数据源授权 > 授权方式和流程 > OAuth 授权",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx#L104-L104",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx",
          "raw_line_start": 104,
          "raw_line_end": 104,
          "original_excerpt": "    自定义客户端允许你在第三方平台注册自己的 OAuth 应用并填入其参数。适用于没有默认客户端的数据源，或你有特定安全、合规要求的场景。",
          "direct_evidence": {
            "chunk_id": "cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source#c6",
            "excerpt": "自定义客户端允许你在第三方平台注册自己的 OAuth 应用并填入其参数。适用于没有默认客户端的数据源，或你有特定安全、合规要求的场景。",
            "text": "OAuth 是一种开放标准的授权协议，允许用户在不暴露密码的情况下，授权第三方应用访问其在特定服务提供商上的资源。Dify 提供两种 OAuth 授权配置方式：默认配置和自定义配置。\n\n#### 授权流程\n\n1. 在数据源配置界面，选择对应的数据源，点击右侧的 **配置**，选择 **添加 OAuth**。\n\n2. 在授权页面中查看并确认权限范围后，点击 **允许访问**。\n\n#### OAuth 客户端设置\nDify 提供默认和自定义两种 OAuth 客户端配置方式。\n\n**默认**\n默认客户端使用 Dify 预先配置并维护的 OAuth 参数，无需任何额外设置，即可一键添加凭据。\n\n**自定义**\n自定义客户端允许你在第三方平台注册自己的 OAuth 应用并填入其参数。适用于没有默认客户端的数据源，或你有特定安全、合规要求的场景。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source#p6",
            "heading_path": "数据源授权 > 授权方式和流程 > OAuth 授权",
            "text": "OAuth 是一种开放标准的授权协议，允许用户在不暴露密码的情况下，授权第三方应用访问其在特定服务提供商上的资源。Dify 提供两种 OAuth 授权配置方式：默认配置和自定义配置。\n\n#### 授权流程\n\n1. 在数据源配置界面，选择对应的数据源，点击右侧的 **配置**，选择 **添加 OAuth**。\n\n2. 在授权页面中查看并确认权限范围后，点击 **允许访问**。\n\n#### OAuth 客户端设置\nDify 提供默认和自定义两种 OAuth 客户端配置方式。\n\n**默认**\n默认客户端使用 Dify 预先配置并维护的 OAuth 参数，无需任何额外设置，即可一键添加凭据。\n\n**自定义**\n自定义客户端允许你在第三方平台注册自己的 OAuth 应用并填入其参数。适用于没有默认客户端的数据源，或你有特定安全、合规要求的场景。\n\n**授权流程**\n\n1. 在数据源配置界面，选择对应的数据源，点击右侧的 **配置**，选择 **添加 OAuth** 右侧的 **设置图标**，进入 OAuth 客户端设置。\n\n2. 点击 **自定义**，输入 **Client ID** 和 **Client Secret**。点击 **保存并授权**完成 OAuth 授权流程。",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 1104,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "reconstruct_verified": true,
          "verification_method": "冻结原文与生产清洗/切块重建；本机182篇、2090子块和1252父块已全量只读比对一致",
          "source_file_sha256": "63c4a5deaef95073f7fc2fc09a6d37d17e543acd0c345394ee5343d19e6bbf0a"
        }
      ]
    }
  ]
}
```

</details>

- 边界来源：[cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source L104–104](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx#L104-L104)；`cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source#c6` / `cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source#p6`。

备注：重写dev030为真正跨两版对照，不再拿云版登录的一句话充多跳。每个限制各自计一个vital；edition为null，版本由题干给出。；整体替换上传数值题。差异限定为冻结文档明确写出的云版默认方式与自部署自定义流程；不推断自部署运行时绝不存在默认客户端。


## dev031：Webhook重复投递时，平台按哪个字段去重、记录留多久？

参考答案：冻结资料没有规定Webhook内置去重键或去重记录保留期，无法给出这两个具体参数。这只能说明资料不足，不能推出产品一定没有去重。

版本：未限定；预期行为：refused；最可能失败：编造event_id或24小时等默认值。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "boundary_evidence": [
    {
      "any_of": [
        {
          "document_id": "self-host/use-dify/nodes/trigger/webhook-trigger",
          "heading_path": "Webhook 触发器",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/trigger/webhook-trigger.mdx#L32-L32",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/trigger/webhook-trigger.mdx",
          "raw_line_start": 32,
          "raw_line_end": 32,
          "original_excerpt": "3. 当订阅的事件发生时，外部系统会将包含事件数据的 HTTP 请求发送到先前提供的 webhook URL。一旦请求被成功接收和处理，你的 Workflow 会被触发，而提取到的事件数据也将成为下游节点可引用的变量。",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/nodes/trigger/webhook-trigger#c1",
            "excerpt": "3. 当订阅的事件发生时，外部系统会将包含事件数据的 HTTP 请求发送到先前提供的 webhook URL。一旦请求被成功接收和处理，你的 Workflow 会被触发，而提取到的事件数据也将成为下游节点可引用的变量。",
            "text": "1. 在 Workflow 中添加 Webhook 触发器后，系统将自动生成一个 webhook URL 作为监听外部 HTTP 请求的专用端点。\n\n    **说明：**\n    将 `TRIGGER_URL` 环境变量（默认 `http://localhost`）设为此 URL 应使用的基础前缀。将其指向调用该 webhook 的外部系统可访问的公共域名或 IP 地址。\n\n2. 你使用此 URL 在外部系统中创建一个 webhook，订阅期望关注的事件。然后，在 Dify 中配置 Webhook 触发器，定义其如何处理接收到的请求并提取请求中的事件数据。\n\n    **注意：**\n    在测试场景中，请始终使用测试专用的 webhook URL，以分离测试与生产数据。\n\n3. 当订阅的事件发生时，外部系统会将包含事件数据的 HTTP 请求发送到先前提供的 webhook URL。一旦请求被成功接收和处理，你的 Workflow 会被触发，而提取到的事件数据也将成为下游节点可引用的变量。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/nodes/trigger/webhook-trigger#p0",
            "heading_path": "Webhook 触发器",
            "text": "**说明：**\n触发器仅适用于 Workflow 应用。\n\nWebhook 允许一个系统自动向另一个系统发送实时数据。当某个特定事件发生时，源系统将事件详情打包进一个 HTTP 请求，并发送至目标系统的指定 URL。\n\n遵循相同的机制，Webhook 触发器能够让 Workflow 在外部事件发生时自动运行：\n\n1. 在 Workflow 中添加 Webhook 触发器后，系统将自动生成一个 webhook URL 作为监听外部 HTTP 请求的专用端点。\n\n    **说明：**\n    将 `TRIGGER_URL` 环境变量（默认 `http://localhost`）设为此 URL 应使用的基础前缀。将其指向调用该 webhook 的外部系统可访问的公共域名或 IP 地址。\n\n2. 你使用此 URL 在外部系统中创建一个 webhook，订阅期望关注的事件。然后，在 Dify 中配置 Webhook 触发器，定义其如何处理接收到的请求并提取请求中的事件数据。\n\n    **注意：**\n    在测试场景中，请始终使用测试专用的 webhook URL，以分离测试与生产数据。\n\n3. 当订阅的事件发生时，外部系统会将包含事件数据的 HTTP 请求发送到先前提供的 webhook URL。一旦请求被成功接收和处理，你的 Workflow 会被触发，而提取到的事件数据也将成为下游节点可引用的变量。\n\n**提示：**\n若目标外部系统有可用的触发器集成，推荐使用 集成触发器。",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 500,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "reconstruct_verified": true,
          "verification_method": "冻结原文与生产清洗/切块重建；本机182篇、2090子块和1252父块已全量只读比对一致",
          "source_file_sha256": "eb1d110ae820e65689f40740c8f7364a803115b9e06d893d3e00963541986dce"
        }
      ]
    },
    {
      "any_of": [
        {
          "document_id": "self-host/use-dify/nodes/trigger/plugin-trigger",
          "heading_path": "集成触发器 > 创建订阅",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/trigger/plugin-trigger.mdx#L34-L34",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/trigger/plugin-trigger.mdx",
          "raw_line_start": 34,
          "raw_line_end": 34,
          "original_excerpt": "订阅是一个用于监听外部系统事件的 webhook。每个触发器集成在每个工作空间中最多支持 10 个订阅。",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/nodes/trigger/plugin-trigger#c2",
            "excerpt": "订阅是一个用于监听外部系统事件的 webhook。每个触发器集成在每个工作空间中最多支持 10 个订阅。",
            "text": "订阅是一个用于监听外部系统事件的 webhook。每个触发器集成在每个工作空间中最多支持 10 个订阅。\n\n**什么是 webhook？**\nWebhook 允许一个系统自动向另一个系统发送实时数据。当某个事件发生时，源系统将事件详情打包为 HTTP 请求，发送至目标系统提供的 URL。\n\n**注意：**\n**前提条件：设置回调 URL 基础前缀**\n\nDify 通过将 `TRIGGER_URL` 环境变量与触发器集成专属路径拼接，生成每个订阅的回调 URL。该变量默认值为 `http://localhost`，外部系统无法访问。创建订阅前，将 `TRIGGER_URL` 设为外部系统可访问的公共域名或 IP 地址，然后重启 Dify。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/nodes/trigger/plugin-trigger#p2",
            "heading_path": "集成触发器 > 创建订阅",
            "text": "订阅是一个用于监听外部系统事件的 webhook。每个触发器集成在每个工作空间中最多支持 10 个订阅。\n\n**什么是 webhook？**\nWebhook 允许一个系统自动向另一个系统发送实时数据。当某个事件发生时，源系统将事件详情打包为 HTTP 请求，发送至目标系统提供的 URL。\n\n**注意：**\n**前提条件：设置回调 URL 基础前缀**\n\nDify 通过将 `TRIGGER_URL` 环境变量与触发器集成专属路径拼接，生成每个订阅的回调 URL。该变量默认值为 `http://localhost`，外部系统无法访问。创建订阅前，将 `TRIGGER_URL` 设为外部系统可访问的公共域名或 IP 地址，然后重启 Dify。\n\nDify 支持两种创建订阅的方式，具体取决于触发器集成支持的选项。\n\n- **自动**：你选择要订阅的事件，Dify 在外部系统中自动创建 webhook。这需要先通过 OAuth 或 API key 授权，以便 Dify 代表你完成配置。\n- **手动**：你使用 Dify 提供的回调 URL 自行在外部系统中创建 webhook，无需授权。\n\n**OAuth（自动）**\n1. 选择 **通过 OAuth 创建** > **自定义**。\n2. 在外部系统中，使用 Dify 提供的回调 URL 创建一个 OAuth 应用。\n3. 返回 Dify，输入应用的客户端 ID 和客户端密钥，然后点击 **保存并授权**。\n    **说明：** 保存后，同一凭据可在后续订阅中复用。\n4. 填写订阅名称，选择要订阅的事件，并配置其他必需设置。\n\n    **提示：**\n    建议订阅所有可用事件。触发器只会响应订阅中涵盖的事件，因此一个涵盖广泛的订阅可被后续添加的触发器复用，无需再创建新订阅。\n5. 点击 **创建**。\n\n**API Key（自动）**\n1. 选择 **通过 API Key 创建**。\n2. 输入所需的验证信息，然后点击 **验证**。\n3. 填写订阅名称，选择要订阅的事件，并配置其他必需设置。\n\n    **提示：**\n    建议订阅所有可用事件。触发器只会响应订阅中涵盖的事件，因此一个涵盖广泛的订阅可被后续添加的触发器复用，无需再创建新订阅。\n4. 点击 **创建**。\n\n**粘贴 URL 创建新订阅（手动）**\n1. 选择 **粘贴 URL 以创建新订阅**。\n2. 填写订阅名称，并使用 Dify 提供的回调 URL 在外部系统中创建 webhook。\n3. （可选）测试：触发一个已订阅的事件，然后在 **手动设置** 页面底部的 **请求日志** 中查看接收到的请求和 Dify 的响应。\n\n4. 点击 **创建**。",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 520,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "reconstruct_verified": true,
          "verification_method": "冻结原文与生产清洗/切块重建；本机182篇、2090子块和1252父块已全量只读比对一致",
          "source_file_sha256": "cf6ea56bf6a86cd3d6e8ce7be40ffcb858e6e9c94c2aa8c0b196b02e1960bbda"
        }
      ]
    }
  ]
}
```

</details>

- 边界来源：[self-host/use-dify/nodes/trigger/webhook-trigger L32–32](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/trigger/webhook-trigger.mdx#L32-L32)；`self-host/use-dify/nodes/trigger/webhook-trigger#c1` / `self-host/use-dify/nodes/trigger/webhook-trigger#p0`。

- 边界来源：[self-host/use-dify/nodes/trigger/plugin-trigger L34–34](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/trigger/plugin-trigger.mdx#L34-L34)；`self-host/use-dify/nodes/trigger/plugin-trigger#c2` / `self-host/use-dify/nodes/trigger/plugin-trigger#p2`。

备注：按复审要求取消REFUSE路由标签，其余题意与无依据金标保持。


## dev032：模板表单会强制执行required，只标必填就能挡住空提交，对吗？

参考答案：不对。模板表单里的HTML5验证属性required不会强制生效，不能仅凭该属性保证拦住空提交。这里不把结论扩展到其他节点或服务端自定义验证。

版本：未限定；预期行为：corrects_premise；最可能失败：把浏览器普通HTML表单行为套到Dify模板表单。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "boundary_evidence": [
    {
      "any_of": [
        {
          "document_id": "self-host/use-dify/nodes/template",
          "heading_path": "模板转换 > 交互式表单 > 支持的输入类型",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/template.mdx#L151-L151",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/template.mdx",
          "raw_line_start": 151,
          "raw_line_end": 151,
          "original_excerpt": "- HTML5 验证属性 `required`、`min`、`max` 和 `pattern` 不会强制生效。",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/nodes/template#c13",
            "excerpt": "- HTML5 验证属性 `required`、`min`、`max` 和 `pattern` 不会强制生效。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/nodes/template#p9",
            "heading_path": "模板转换 > 交互式表单 > 支持的输入类型",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 3540,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "source_file_sha256": "f0aa77bad2d01c6111c3e5f5dec8bdc12002dc323ada624cfc2ba52b354965ab"
        }
      ]
    }
  ]
}
```

</details>

- 边界来源：[self-host/use-dify/nodes/template L151–151](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/template.mdx#L151-L151)；`self-host/use-dify/nodes/template#c13` / `self-host/use-dify/nodes/template#p9`。

备注：替换常识安全题dev032，使用产品专有的模板表单例外。不给不存在的CORRECT路由标签。
