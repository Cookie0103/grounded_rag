# 新70题 · 首批12题待审题卡

dev021～dev032计入新70道开发题，旧20道只作回归。以下答案来自冻结原文，尚未运行RAG或基线，也未人工校准。

## 文件

- questions.jsonl：可由现有Question加载的12行数据。
- evidence.json：参考答案、原子要点、原文路径/行号、真实chunk/父块、难度与边界核查。
- validation.json：数量、长度、路由、文档复用与格式检查结果。

本批11/12题不超过40字符；12篇金标文档，连同边界核查/干扰来源共18篇；四大目录均有来源，同篇最多2题。70题的至少50篇覆盖尚未完成。

| ID | 类型/难点 | 小问数 | 预期首路由 | 题目 |
|---|---|---:|---|---|
| dev021 | fact_single / short_fact | 1 | SINGLE | Workflow流首帧能算受理成功吗？ |
| dev022 | fact_single / lexical_gap | 1 | SINGLE | 不重跑前面的步骤，怎么换一份中间结果只测后面的步骤？ |
| dev023 | fact_single / table_schema | 1 | SINGLE | 外部知识检索请求体的顶层必填字段有哪些？ |
| dev024 | fact_single / neighbor_confusion | 1 | SINGLE | 一批独立输入逐项处理，失败后要占位续跑，怎么配？ |
| dev025 | summary / scattered_evidence | 3 | MULTI | 云版知识库存储按什么计量、满额还能编辑分段吗、删文档后为何额度没立刻降？ |
| dev026 | summary / ordered_steps | 2 | MULTI | Workflow因Web表单暂停，原流已关且form_token和workflow_run_id已保存。怎样提交本地附件并恢复监听？ |
| dev027 | reasoning / chain_bridge | 2 | MULTI | Dify工作流入门第9课用哪个节点固定邮件排版，邮箱字段未定义时如何给默认文字？ |
| dev028 | reasoning / parallel_evidence | 2 | MULTI | 停止对话为何可能成功却没停，工作流日志接口能给逐节点记录吗？ |
| dev029 | reasoning / comparison_choice | 2 | MULTI | 调试替换中间值和聊天跨轮保存偏好，分别该用什么能力？ |
| dev030 | version / edition_conflict | 2 | MULTI | Dify云版支持哪些登录方式，同邮箱切换方式会另建账户吗？ |
| dev031 | unanswerable / absence_check | 2 | MULTI | Webhook重复投递时，平台按哪个字段去重、记录留多久？ |
| dev032 | unanswerable / false_premise | 1 | SINGLE | 既然Dify会认证API的user，填别人的账号ID也不会越权吧？ |

## dev021 · Workflow流首帧能算受理成功吗？

类型：fact_single；版本标签：通用/不限定；小问数：1；预期首路由：SINGLE。

**参考答案**：不能。Workflow流第一帧固定是保活ping，不代表运行已经受理；应等待首个data事件workflow_started。

**必答点与来源**：

- 1. Workflow事件流第一帧为ping，不能据此判定运行已受理。 [原文L27～27](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx#L27-L27) · `api-reference/guides/streaming#c2`
- 2. 应以首个data事件workflow_started作为运行已受理的信号。 [原文L27～27](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx#L27-L27) · `api-reference/guides/streaming#c2`

**最可能答错处**：把HTTP/SSE连接成功或ping误当作业务运行已经开始。

**审题说明**：

## dev022 · 不重跑前面的步骤，怎么换一份中间结果只测后面的步骤？

类型：fact_single；版本标签：self_host；小问数：1；预期首路由：SINGLE。

**参考答案**：在底部变量检查器里找到前面步骤的输出，点击可编辑的变量值并修改，再只运行要测试的下游节点。下游使用改后的值，不必重跑上游。

**必答点与来源**：

- 1. 使用变量检查器编辑可修改的中间变量值。 [原文L15～15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L15-L15) · `self-host/use-dify/debug/variable-inspect#c1`；[原文L23～23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L23-L23) · `self-host/use-dify/debug/variable-inspect#c2`
- 2. 随后只运行下游节点，下游会使用编辑后的值而非原值，无需重跑整个工作流。 [原文L23～23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L23-L23) · `self-host/use-dify/debug/variable-inspect#c2`

**最可能答错处**：把修改节点配置、重新全流程运行当成唯一办法，未定位到调试缓存。

**审题说明**：题干不出现官方名称‘变量检查器’；不把‘最后运行记录不变’设为未问的必答点。

## dev023 · 外部知识检索请求体的顶层必填字段有哪些？

类型：fact_single；版本标签：self_host；小问数：1；预期首路由：SINGLE。

**参考答案**：三个顶层必填字段是knowledge_id（string，知识源标识）、query（string，搜索查询）和retrieval_setting（object，检索参数）。metadata_condition是可选字段。

**必答点与来源**：

- 1. 顶层必填字段包括knowledge_id。 [原文L34～34](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L34-L34) · `self-host/use-dify/knowledge/external-knowledge-api#c3`
- 2. 顶层必填字段包括query。 [原文L35～35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L35-L35) · `self-host/use-dify/knowledge/external-knowledge-api#c3`
- 3. 顶层必填字段包括retrieval_setting。 [原文L36～36](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/external-knowledge-api.mdx#L36-L36) · `self-host/use-dify/knowledge/external-knowledge-api#c3`

**最可能答错处**：混淆顶层与嵌套字段，把top_k当顶层字段，或把metadata_condition列为必填。

**审题说明**：数值/配置/表格子类中的表格题；只要求正确列出顶层必填字段，类型和含义供参考，不把未问的类型、嵌套参数设为必答。

## dev024 · 一批独立输入逐项处理，失败后要占位续跑，怎么配？

类型：fact_single；版本标签：self_host；小问数：1；预期首路由：SINGLE。

**参考答案**：用迭代节点处理数组，错误处理选‘错误时继续’；失败项输出null，其余项继续。例如第二项失败时得到[result-1, null, result-3]。不要选‘移除失败结果’。

**必答点与来源**：

- 1. 使用迭代节点逐项处理输入数组。 [原文L8～8](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/iteration.mdx#L8-L8) · `self-host/use-dify/nodes/iteration#c0`
- 2. 错误处理选择‘错误时继续’。 [原文L73～73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/iteration.mdx#L73-L73) · `self-host/use-dify/nodes/iteration#c5`
- 3. 失败元素输出null，以保留该失败项的占位而非从结果中移除。 [原文L73～73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/iteration.mdx#L73-L73) · `self-host/use-dify/nodes/iteration#c5`；[原文L79～79](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/iteration.mdx#L79-L79) · `self-host/use-dify/nodes/iteration#c5`

**最可能答错处**：混淆循环与迭代，或误选移除失败结果导致输入输出位置不再对应。

**审题说明**：

**干扰文档**：self-host/use-dify/nodes/loop；同一nodes目录的循环基于前次结果逐步演进，迭代处理独立数组元素；迭代页内‘移除失败结果’也是强干扰项。

## dev025 · 云版知识库存储按什么计量、满额还能编辑分段吗、删文档后为何额度没立刻降？

类型：summary；版本标签：cloud；小问数：3；预期首路由：MULTI。

**参考答案**：存储用量取决于文档产生的向量数量，不是上传文件本身的大小；额度满后不能编辑分段，经济索引也不例外；删文档后账单数字会延迟刷新，不会立即下降。资料没有给出固定几秒或几分钟的刷新期限。

**必答点与来源**：

- 1. 存储用量取决于文档产生的向量数量，而非原始文件大小。 [原文L23～23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L23-L23) · `cloud/use-dify/knowledge/knowledge-storage-limit#c1`
- 2. 存储额度已满时，编辑分段操作会被拦截。 [原文L49～49](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L49-L49) · `cloud/use-dify/knowledge/knowledge-storage-limit#c3`
- 3. 删除文档后，账单中的用量数字延迟刷新，要过一段时间才会下降。 [原文L59～59](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L59-L59) · `cloud/use-dify/knowledge/knowledge-storage-limit#c4`

**最可能答错处**：按原始文件大小计算占用，认为经济索引能绕过满额限制，或凭界面未立即下降就断言删除没有释放空间。

**审题说明**：三个必答点分别来自三个不同H2章节和三个不同子块，不把相邻同一句拆成‘分散证据’。不额外要求报告套餐容量或未给出的刷新秒数。

## dev026 · Workflow因Web表单暂停，原流已关且form_token和workflow_run_id已保存。怎样提交本地附件并恢复监听？

类型：summary；版本标签：通用/不限定；小问数：2；预期首路由：MULTI。

**参考答案**：按顺序：①用form_token获取表单定义，确认输入与可选action；②用同一user上传本地附件，保存id为upload_file_id；③凭form_token提交输入（本地文件引用upload_file_id）、允许的action及user；④原流已关闭，提交后以workflow_run_id和启动时的同一user重新连接工作流事件流，继续监听。

**必答点与来源**：

- 1. 先凭form_token获取人工介入表单定义，以确定输入字段与可用action。 [原文L28～28](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/human-input-flow.mdx#L28-L28) · `api-reference/guides/human-input-flow#c2`
- 2. 本地附件先上传，保存返回的id并在提交时作为upload_file_id引用。 [原文L33～33](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/human-input-flow.mdx#L33-L33) · `api-reference/guides/human-input-flow#c2`
- 3. 使用form_token提交表单输入、定义中允许的action及user；执行、上传、提交沿用同一user。 [原文L38～38](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/human-input-flow.mdx#L38-L38) · `api-reference/guides/human-input-flow#c3`；[原文L33～33](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/human-input-flow.mdx#L33-L33) · `api-reference/guides/human-input-flow#c2`
- 4. 提交后用保存的workflow_run_id及启动运行时的同一user重新打开事件流。 [原文L47～47](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/human-input-flow.mdx#L47-L47) · `api-reference/guides/human-input-flow#c4`

**最可能答错处**：把form_token当文件ID或运行ID，漏掉先上传本地文件，或用新的user恢复监听。

**审题说明**：题干明确Web投递、本地文件、原流关闭和已保存两个标识符；不要求未问的远程URL模式或多暂停参数。；原文推荐先获取定义再上传；评分只强制获取定义、上传文件都在提交前完成，且提交后恢复监听。允许先上传再取定义的等价有效顺序。

## dev027 · Dify工作流入门第9课用哪个节点固定邮件排版，邮箱字段未定义时如何给默认文字？

类型：reasoning；版本标签：self_host；小问数：2；预期首路由：MULTI。

**参考答案**：第9课用的是模板转换节点。定位到这个节点后，可用Jinja2的default过滤器处理未定义字段，例如{{ user.email | default('No email provided') }}；默认文字可按需求替换。

**必答点与来源**：

- 1. 第9课使用模板转换节点固定邮件排版。 [原文L35～35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/learn/tutorials/workflow-101/lesson-09.mdx#L35-L35) · `learn/tutorials/workflow-101/lesson-09#c2`
- 2. 在该节点中用Jinja2的default过滤器为未定义邮箱字段提供默认文本，例如{{ user.email | default('No email provided') }}。 [原文L73～73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/template.mdx#L73-L73) · `self-host/use-dify/nodes/template#c6`；[原文L76～76](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/template.mdx#L76-L76) · `self-host/use-dify/nodes/template#c6`

**最可能答错处**：只总结第9课插入节点的步骤，没沿‘模板转换’继续查字段默认值；或误把空字符串与未定义字段混为一谈。

**审题说明**：这是文档导航型链式多跳；不是计算题，不声称所有一次检索系统都会失败。只考字段未定义，不扩展到空字符串/null的不同语义。

**链式关系**：第9课 → 模板转换 → 查询该节点的default过滤器。题干没有给出模板转换/Jinja2/default这三个桥接关键词。

## dev028 · 停止对话为何可能成功却没停，工作流日志接口能给逐节点记录吗？

类型：reasoning；版本标签：通用/不限定；小问数：2；预期首路由：MULTI。

**参考答案**：一种应优先核对的原因是停止接口的user与发起回复时不一致：此时停止会被静默忽略，调用仍可成功。工作流日志接口不能给逐节点记录，它只返回运行级汇总；逐节点事件应另行流式跟踪运行。

**必答点与来源**：

- 1. 先核对停止接口的user是否与发起该回复的用户一致。 [原文L19～19](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/end-user-identity.mdx#L19-L19) · `api-reference/guides/end-user-identity#c1`
- 2. user不一致时停止会被静默忽略，调用仍可返回成功。 [原文L19～19](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/end-user-identity.mdx#L19-L19) · `api-reference/guides/end-user-identity#c1`
- 3. 工作流日志接口提供运行级汇总，不是逐节点执行日志。 [原文L55～55](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/workflow.mdx#L55-L55) · `api-reference/guides/workflow#c5`

**最可能答错处**：把停止调用成功等同于业务成功，或用运行日志接口冒充逐节点执行轨迹。

**审题说明**：两个独立小问，不能伪称链式；user不一致只是明确有据的可能原因，不是所有故障的唯一原因。逐节点的替代API入口供参考，不列为题干未问的必答点。

## dev029 · 调试替换中间值和聊天跨轮保存偏好，分别该用什么能力？

类型：reasoning；版本标签：self_host；小问数：2；预期首路由：MULTI。

**参考答案**：前者用变量检查器，编辑中间变量后供下游重测；后者用变量赋值器写入会话变量，在同一聊天会话的多个轮次间保存偏好。不要把调试改值当作持久会话写入。

**必答点与来源**：

- 1. 调试替换中间值应使用变量检查器。 [原文L7～7](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L7-L7) · `self-host/use-dify/debug/variable-inspect#c0`；[原文L23～23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/variable-inspect.mdx#L23-L23) · `self-host/use-dify/debug/variable-inspect#c2`
- 2. 聊天中跨轮保存偏好应使用变量赋值器写入会话变量。 [原文L8～8](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/variable-assigner.mdx#L8-L8) · `self-host/use-dify/nodes/variable-assigner#c0`；[原文L18～18](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/variable-assigner.mdx#L18-L18) · `self-host/use-dify/nodes/variable-assigner#c1`

**最可能答错处**：把变量检查器的调试改值当成持久化会话记忆，或用会话赋值替代临时调试。

**审题说明**：两篇分别定义调试改值与会话写入，任一篇不能独自完整说明两种能力。只把两种能力的正确选择列为必答点，不加题干没问的‘最后运行记录’或跨会话寿命。变量检查器是调试界面，不能统称两个节点。

## dev030 · Dify云版支持哪些登录方式，同邮箱切换方式会另建账户吗？

类型：version；版本标签：cloud；小问数：2；预期首路由：MULTI。

**参考答案**：云版支持GitHub、Google和邮箱验证码。相同邮箱的登录方式会自动关联，例如先以某邮箱通过GitHub注册，再以同一邮箱验证码登录，识别为同一账户。

**必答点与来源**：

- 1. 云版可通过GitHub、Google或邮箱验证码登录。 [原文L13～13](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/personal-account-management.mdx#L13-L13) · `cloud/use-dify/workspace/personal-account-management#c1`
- 2. 邮箱地址相同的不同登录方式自动关联为同一账户，不因切换方式而另建独立账户。 [原文L13～13](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/personal-account-management.mdx#L13-L13) · `cloud/use-dify/workspace/personal-account-management#c1`

**最可能答错处**：将自部署版的邮箱密码登录套到云版，或把不同登录方式误当作不同账户。

**审题说明**：题干明确云版；隐藏edition后系统仍有可见版本线索。自部署说明给出邮箱密码，Enterprise另有OAuth/SAML，不把这一例外抹掉。

## dev031 · Webhook重复投递时，平台按哪个字段去重、记录留多久？

类型：unanswerable；版本标签：self_host；小问数：2；预期首路由：MULTI。

**参考答案**：冻结资料说明了Webhook接收请求与触发流程，但未规定内置去重使用的字段，也未给出去重记录的保留期限。因此无法给出这两个具体参数；这不等于证明产品一定没有去重能力。

**必答点与来源**：

本题没有事实nuggets，按边界行为评分；不能用空nugget把它算成满分。
- 核查依据：[原文](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/trigger/webhook-trigger.mdx#L32-L32)：3. 当订阅的事件发生时，外部系统会将包含事件数据的 HTTP 请求发送到先前提供的 webhook URL。一旦请求被成功接收和处理，你的 Workflow 会被触发，而提取到的事件数据也将成为下游节点可引用的变量。
- 核查依据：[原文](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/trigger/plugin-trigger.mdx#L34-L34)：订阅是一个用于监听外部系统事件的 webhook。每个触发器集成在每个工作空间中最多支持 10 个订阅。

**最可能答错处**：凭通用Webhook经验编造event_id、24小时等默认值，把日志或缓存TTL当成事件去重期限。

**审题说明**：预期首路由MULTI表示需要查两个参数，最终行为应承认资料不足；拒答行为与路由标签分开评。不能把‘去重能力未说明’改判为已知错误前提。

**缺答案核查**：182篇全库检索核心去重/幂等/事件ID词0命中；另检查‘重复’和TTL所有命中，并通读相关触发器页及配置段落，未找到所问策略。完整命中列表在evidence.json。不能推出‘产品一定没有去重’。

## dev032 · 既然Dify会认证API的user，填别人的账号ID也不会越权吧？

类型：unanswerable；版本标签：通用/不限定；小问数：1；预期首路由：SINGLE。

**参考答案**：前提不成立。Dify不会认证API的user，它是调用方自定义的终端用户标识；会话、文件等又以它划分范围，不能把填写该字段本身当作身份认证保证，因而不能据此断言不会越权。

**必答点与来源**：

本题没有事实nuggets，按边界行为评分；不能用空nugget把它算成满分。
- 核查依据：[原文](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/end-user-identity.mdx#L9-L9)：大多数应用接口都接受一个 `user` 字段：由你自己定义的标识符，表示这次调用代表哪位终端用户。Dify 不会对它做任何认证，为每个人选一个稳定的值（如账户 ID），并在每次调用中发送同一个值。
- 核查依据：[原文](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/end-user-identity.mdx#L17-L17)：- **会话**：列表、历史、重命名和删除都只作用于该用户自己的会话。
- 核查依据：[原文](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/end-user-identity.mdx#L18-L18)：- **文件**：上传的文件归上传者所有，换一个 `user` 引用该文件会失败。

**最可能答错处**：顺着错误前提承诺安全，或把user与已认证的API密钥混为一谈。

**审题说明**：只要求纠正认证前提并否定据此作安全保证；不要求凭资料推断某个具体部署必然存在可利用漏洞。

## 给Claude的审题入口

只审本目录12题及冻结原文；不要跑被测RAG，不读取封存题。逐题核对：题干是否独立成立、必答点是否确实被问到、原文与chunk能否支持、n_subasks与路由是否一致、链式是否真有桥接、负例是否缺充分核查。建议重点看dev026请求字段粒度、dev027链式真实性和dev031缺答案证据。

本批只交12题，等作者/Claude反馈后继续；不宣称已验证Naive一定失败或题集已冻结。原文按CC BY 4.0保留出处，问题及答案是改编。
