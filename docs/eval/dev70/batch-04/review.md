# batch-04 当前审阅稿

2026-10-20复审修订稿；逐项原因见repair-2026-10-20.json及revision-log.md。所有原样检索和数据库记录为修订前历史证据，本版本未复跑。

## dev068 · single/synonym

上游偶发失败，怎样让后续用备用文案照跑，文案类型有何要求？

参考答案：将节点错误处理设为“默认值”，失败时以备用值替代后继续运行；备用文案类型必须与该节点输出类型相同。

失败风险：把备用文案类型当作任意字符串，或把重试/失败分支误当默认值续跑。

预期行为/路由：answered / SINGLE；小问数：1。

- **vital 1**：选择默认值模式可在节点失败时用备用值继续运行。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/predefined-error-handling-logic L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/predefined-error-handling-logic.mdx#L23-L23) · `self-host/use-dify/build/predefined-error-handling-logic#c0` · `self-host/use-dify/build/predefined-error-handling-logic#p0`：<Accordion title="默认值">
  - 必需组2（组内OR）：
    - [self-host/use-dify/build/predefined-error-handling-logic L24–24](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/predefined-error-handling-logic.mdx#L24-L24) · `self-host/use-dify/build/predefined-error-handling-logic#c0` · `self-host/use-dify/build/predefined-error-handling-logic#p0`：当节点失败时，使用备用值代替。工作流继续运行。
- **vital 2**：备用值必须与节点输出类型相同。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/predefined-error-handling-logic L31–31](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/predefined-error-handling-logic.mdx#L31-L31) · `self-host/use-dify/build/predefined-error-handling-logic#c0` · `self-host/use-dify/build/predefined-error-handling-logic#p0`：- 默认值必须与节点的输出类型匹配，如果输出字符串，你的默认值也必须是字符串。

## dev069 · single/synonym

范例待审时能撤回吗，递交前插件来源和试跑环境有何要求？

参考答案：Pending状态可撤回到Draft，修改后重新提交。插件须直接从Dify市场安装；应用须在最新Community Edition上至少运行一次，以此核验兼容性。

失败风险：把Pending误认为不可撤回，或漏掉市场安装插件及最新版Community Edition实跑要求。

预期行为/路由：answered / SINGLE；小问数：1。

- **vital 1**：Pending状态的模板可撤回为Draft后修改并重新提交。
  - 必需组1（组内OR）：
    - [self-host/use-dify/publish/publish-to-marketplace L17–17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/publish-to-marketplace.mdx#L17-L17) · `self-host/use-dify/publish/publish-to-marketplace#c1` · `self-host/use-dify/publish/publish-to-marketplace#p1`：模板处于 **Pending** 状态时，可随时撤回。撤回后，模板将回到 **Draft** 状态，你可修改任意内容后重新提交。
- **vital 2**：提交前应用使用的所有插件须直接从市场安装。
  - 必需组1（组内OR）：
    - [self-host/use-dify/publish/publish-to-marketplace L21–21](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/publish-to-marketplace.mdx#L21-L21) · `self-host/use-dify/publish/publish-to-marketplace#c1` · `self-host/use-dify/publish/publish-to-marketplace#p1`：- 请确保应用中使用的所有插件都 **直接从市场安装**。
- **vital 3**：提交前应在最新Community Edition上至少运行一次应用。
  - 必需组1（组内OR）：
    - [self-host/use-dify/publish/publish-to-marketplace L22–22](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/publish-to-marketplace.mdx#L22-L22) · `self-host/use-dify/publish/publish-to-marketplace#c1` · `self-host/use-dify/publish/publish-to-marketplace#p1`：- 在最新 Community Edition 上至少运行一次应用，确认其正常工作。市场会根据最新 Community Edition 来审核应用模板的兼容性。

## dev070 · single/numeric_table

给Skill Builder的单条消息附文件，数量及图片、其他文件的大小上限各是多少？

参考答案：每条消息最多附10个文件；图片每个不超过10 MB，其他文件每个不超过15 MB。这些只给Builder提供上下文，不自动进入Skill文件树。

失败风险：把Skill导入包的50MB限额套给Builder消息附件，混淆附件数与单文件大小。

预期行为/路由：answered / SINGLE；小问数：1。

- **vital 1**：Skill Builder每条消息最多附加10个文件。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/skills L57–57](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/skills.mdx#L57-L57) · `self-host/use-dify/build/skills#c4` · `self-host/use-dify/build/skills#p2`：每条消息最多附加 10 个文件：图片不超过 10 MB，其他文件不超过 15 MB。这些文件只为 Skill Builder 提供上下文，不会成为 Skill 的一部分。要将文件加入 Skill，请通过文件树添加。
- **vital 2**：Skill Builder消息附件中图片每个不超过10 MB。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/skills L57–57](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/skills.mdx#L57-L57) · `self-host/use-dify/build/skills#c4` · `self-host/use-dify/build/skills#p2`：每条消息最多附加 10 个文件：图片不超过 10 MB，其他文件不超过 15 MB。这些文件只为 Skill Builder 提供上下文，不会成为 Skill 的一部分。要将文件加入 Skill，请通过文件树添加。
- **vital 3**：Skill Builder消息附件中其他文件每个不超过15 MB。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/skills L57–57](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/skills.mdx#L57-L57) · `self-host/use-dify/build/skills#c4` · `self-host/use-dify/build/skills#p2`：每条消息最多附加 10 个文件：图片不超过 10 MB，其他文件不超过 15 MB。这些文件只为 Skill Builder 提供上下文，不会成为 Skill 的一部分。要将文件加入 Skill，请通过文件树添加。

## dev071 · single/numeric_table

上传文件给外部存储该选哪种正文，非文本响应会变成什么变量？

参考答案：发送前序文件变量时选“二进制”请求正文；返回的二进制等非文本内容会成为文件变量，供后续节点使用。

失败风险：把上传正文选成JSON或表单，或将非文本响应当作普通字符串变量。

预期行为/路由：answered / SINGLE；小问数：1。

- **vital 1**：上传文件变量使用二进制请求正文。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/http-request L95–95](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/http-request.mdx#L95-L95) · `self-host/use-dify/nodes/http-request#c8` · `self-host/use-dify/nodes/http-request#p8`：**文件上传** 使用二进制请求正文选项。从先前节点选择文件变量，将文件发送到外部服务进行文档存储、媒体处理或备份。
- **vital 2**：二进制响应内容成为文件变量。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/http-request L85–85](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/http-request.mdx#L85-L85) · `self-host/use-dify/nodes/http-request#c7` · `self-host/use-dify/nodes/http-request#p7`：基于文本的响应（JSON、XML、HTML 等）被视为常规数据，而二进制内容则成为文件变量。

## dev072 · single/neighbor

思考混进答复时，哪些模型能分离？界面和API各怎么开，关掉后思考输出怎样？

参考答案：仅对用think标签包裹思考的模型生效。界面打开“启用推理标签分离”，API设reasoning_format=separated；打开后text保留回答、reasoning_content接收思考，关闭时reasoning_content为空。

失败风险：把分离功能推广到所有推理模型，或漏掉API的separated值及关闭时空输出。

预期行为/路由：answered / SINGLE；小问数：2。

- **vital 1**：界面通过启用推理标签分离开关分离思考与回答。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/llm L143–143](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/llm.mdx#L143-L143) · `self-host/use-dify/nodes/llm#c11` · `self-host/use-dify/nodes/llm#p10`：打开 **启用推理标签分离** 开关即可将两者分开：`text` 输出仅保留回答，思考过程则移至独立的 `reasoning_content` 输出变量。开关关闭时，`reasoning_content` 为空。
- **vital 2**：API开启分离时设置reasoning_format为separated。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/llm L145–145](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/llm.mdx#L145-L145) · `self-host/use-dify/nodes/llm#c11` · `self-host/use-dify/nodes/llm#p10`：开关打开时，`reasoning_format` 为 `separated`
- **vital 3**：关闭分离开关时reasoning_content为空。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/llm L143–143](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/llm.mdx#L143-L143) · `self-host/use-dify/nodes/llm#c11` · `self-host/use-dify/nodes/llm#p10`：打开 **启用推理标签分离** 开关即可将两者分开：`text` 输出仅保留回答，思考过程则移至独立的 `reasoning_content` 输出变量。开关关闭时，`reasoning_content` 为空。
- **vital 4**：分离设置仅适用于用think标签包裹推理内容的模型。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/llm L148–148](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/llm.mdx#L148-L148) · `self-host/use-dify/nodes/llm#c12` · `self-host/use-dify/nodes/llm#p10`：此设置仅对用 `<think>` 标签包裹推理内容的模型生效。

## dev073 · single/neighbor

每轮沿用上一稿再润色，该用什么节点？没设退出条件会何时停？

参考答案：用循环节点，因为每轮依赖前一轮结果；不设终止条件时会持续到达到最大循环次数。

失败风险：把前后依赖的反复润色当作独立迭代，或误称无退出条件会永远执行。

预期行为/路由：answered / SINGLE；小问数：1。

- **vital 1**：依赖上一轮结果继续处理应使用循环节点。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/loop L8–8](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/loop.mdx#L8-L8) · `self-host/use-dify/nodes/loop#c0` · `self-host/use-dify/nodes/loop#p0`：循环节点执行重复性工作流，每个循环都基于前一个循环的结果进行构建。与迭代处理数组元素独立不同，循环创建的是随着每次重复而演进的渐进式工作流。
- **vital 2**：未指定终止条件时，循环持续到最大循环次数。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/loop L53–53](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/loop.mdx#L53-L53) · `self-host/use-dify/nodes/loop#c3` · `self-host/use-dify/nodes/loop#p3`：当满足终止条件、达到最大次数或执行退出循环节点时，循环终止。如果未指定条件，循环将继续直到达到最大次数。

## dev074 · single/short

在哪查哪步最慢和单步最近的入出参？

参考答案：在应用运行历史的“追踪”查看每个节点耗时；单节点配置面板点“最后运行”，查看该节点最近输入、输出和时间详情。

失败风险：只给总耗时，遗漏节点追踪入口或把最后运行当作完整运行历史。

预期行为/路由：answered / SINGLE；小问数：1。

- **vital 1**：应用运行历史的追踪展示各节点耗时。
  - 必需组1（组内OR）：
    - [self-host/use-dify/debug/history-and-logs L44–44](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/history-and-logs.mdx#L44-L44) · `self-host/use-dify/debug/history-and-logs#c4` · `self-host/use-dify/debug/history-and-logs#p4`：准确显示工作流的执行过程，包括哪些节点按什么顺序运行、每个节点耗时多长，以及数据在节点间如何流动。这对于找出瓶颈和理解具有分支或循环的复杂工作流很有用。
- **vital 2**：节点配置面板的最后运行展示最近输入、输出和时间。
  - 必需组1（组内OR）：
    - [self-host/use-dify/debug/history-and-logs L52–52](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/history-and-logs.mdx#L52-L52) · `self-host/use-dify/debug/history-and-logs#c5` · `self-host/use-dify/debug/history-and-logs#p5`：你也可以检查任何单个节点的最后一次执行。在节点配置面板中点击"最后运行"，查看其最近的输入、输出和时间详情。

## dev075 · single/single_version

云端Sandbox能发布流水线模板吗？换到支持的套餐发布后，在哪找到模板？

参考答案：Sandbox不能发布为可复用流水线模板，该功能限Professional和Team；在允许的套餐中发布为流水线后，模板出现在“自定义模板”中。

失败风险：忽略Sandbox套餐限制，或把自定义模板入口与公共市场混为一谈。

预期行为/路由：answered / SINGLE；小问数：2。

- **vital 1**：云端Sandbox不能将流水线发布为可复用模板。
  - 必需组1（组内OR）：
    - [cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline L54–54](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline.mdx#L54-L54) · `cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline#c1` · `cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline#p0`：Sandbox 账户无法将流水线发布为可复用模板。
- **vital 2**：发布为流水线后，模板出现在自定义模板中。
  - 必需组1（组内OR）：
    - [cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline L49–49](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline.mdx#L49-L49) · `cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline#c1` · `cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline#p0`：你可以点击发布为知识流水线将该流水线保存为可复用的模版，该模版将出现在自定义模版中。

## dev076 · single/single_version

从市场给云端装集成却跳到别处，怎样改回？谁能调整安装权限？

参考答案：清除“安装偏好设置”中保存的URL，即可重新安装到Dify Cloud。工作空间所有者和管理员可以在“集成”页面底部的“权限”中调整谁能安装和调试集成。

失败风险：把自部署填入部署URL的步骤套给Cloud，或把权限设置者误判为普通成员。

预期行为/路由：answered / SINGLE；小问数：2。

- **vital 1**：市场安装目标误指别处时，清除安装偏好设置中保存的URL以恢复安装到Dify Cloud。
  - 必需组1（组内OR）：
    - [cloud/use-dify/workspace/plugins L36–36](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/plugins.mdx#L36-L36) · `cloud/use-dify/workspace/plugins#c2` · `cloud/use-dify/workspace/plugins#p2`：如果从市场安装时打开的是其他 Dify 环境而非你的 Dify Cloud 工作空间，清除 **安装偏好设置** 中保存的 URL 即可重新安装到 Dify Cloud。
- **vital 2**：工作空间所有者和管理员可以在集成页面底部的权限中设置安装权限。
  - 必需组1（组内OR）：
    - [cloud/use-dify/workspace/plugins L46–46](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/plugins.mdx#L46-L46) · `cloud/use-dify/workspace/plugins#c3` · `cloud/use-dify/workspace/plugins#p3`：工作空间所有者和管理员可在 **集成** 页面底部的 **权限** 中，设置谁能安装和调试集成。每项权限都可以设为所有人可用、仅管理员可用或无人可用：

## dev077 · multi/chain

CodeExecutionError通常指什么依赖出了问题？沿该依赖，运行隔离方式和调整超时的配置模板分别是什么？

参考答案：该错误表示沙箱无法执行代码，通常是服务停止。沙箱以独立容器运行，隔离宿主机和其他服务；其行为（含worker超时）通过docker/envs/core-services/sandbox.env.example中的SANDBOX_*变量调整。

失败风险：把沙箱服务无法执行误判成用户代码异常，或误改API输出限制模板而不是沙箱行为模板。

预期行为/路由：answered / MULTI；小问数：2。

- **vital 1**：CodeExecutionError表示沙箱无法执行代码，通常意味着服务停止。
  - 必需组1（组内OR）：
    - [self-host/use-dify/debug/error-type L28–28](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/error-type.mdx#L28-L28) · `self-host/use-dify/debug/error-type#c1` · `self-host/use-dify/debug/error-type#p1`：`CodeExecutionError`
  - 必需组2（组内OR）：
    - [self-host/use-dify/debug/error-type L29–29](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/error-type.mdx#L29-L29) · `self-host/use-dify/debug/error-type#c1` · `self-host/use-dify/debug/error-type#p1`：<Info>沙箱服务无法执行你的代码 - 通常意味着服务已停止</Info>
- **vital 2**：沙箱以独立容器运行，将执行与宿主机及其他服务隔离。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/code L22–22](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/code.mdx#L22-L22) · `self-host/use-dify/nodes/code#c1` · `self-host/use-dify/nodes/code#p1`：沙箱以独立容器运行，将代码执行与宿主机及其他服务隔离。
- **vital 3**：沙箱worker超时等行为通过docker/envs/core-services/sandbox.env.example中的SANDBOX_*变量调整。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/code L22–22](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/code.mdx#L22-L22) · `self-host/use-dify/nodes/code#c1` · `self-host/use-dify/nodes/code#p1`：通过 `docker/envs/core-services/sandbox.env.example` 中的 `SANDBOX_*` 环境变量调整其行为（worker 超时、经由 SSRF 代理的网络访问、端口）

## dev078 · multi/chain

每条消息都要启动处理，该选哪种应用和收尾环节？沿该环节，怎样填入上游值，并在后台仍忙时先发确认？

参考答案：选择Chatflow，每条消息会触发流程；它必需直接回复节点收尾。该节点用{{variable_name}}引用上游值，可用渐进式响应在后台继续处理时先发送确认。

失败风险：直接给Workflow的输出节点，或以为必须等后台处理完成才能发出阶段确认。

预期行为/路由：answered / MULTI；小问数：2。

- **vital 1**：Chatflow中每条用户消息都会触发设计的流程。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/workflow-chatflow L31–31](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/workflow-chatflow.mdx#L31-L31) · `self-host/use-dify/build/workflow-chatflow#c1` · `self-host/use-dify/build/workflow-chatflow#p1`：用户通过聊天界面进行交互，每条消息在生成回复前，都会触发你设计的流程。适用于交互式助手、引导式问答，或任何需要在每次回复背后进行结构化处理的对话场景。
- **vital 2**：Chatflow必需使用直接回复节点作为结束节点。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/workflow-chatflow L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/workflow-chatflow.mdx#L42-L42) · `self-host/use-dify/build/workflow-chatflow#c2` · `self-host/use-dify/build/workflow-chatflow#p1`：| 结束节点 | [输出](/zh/self-host/use-dify/nodes/output)（可选） | [直接回复](/zh/self-host/use-dify/nodes/answer)（必需） |
- **vital 3**：直接回复节点用{{variable_name}}语法引用上游节点变量。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/answer L18–18](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/answer.mdx#L18-L18) · `self-host/use-dify/nodes/answer#c1` · `self-host/use-dify/nodes/answer#p1`：使用 `{{variable_name}}` 语法引用任何先前工作流节点的变量。编辑器支持丰富的内容格式化和变量插入，以创建动态的、上下文相关的响应。
- **vital 4**：直接回复节点的渐进式响应能在后台继续处理时先发送确认。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/answer L46–46](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/answer.mdx#L46-L46) · `self-host/use-dify/nodes/answer#c3` · `self-host/use-dify/nodes/answer#p3`：**渐进式响应** - 在后台处理继续的同时提供即时确认

## dev079 · multi/chain

Dify第9课的固定排版环节放在哪，正文取谁的值？该环节怎样读嵌套姓名并兜底缺失项？

参考答案：在Agent之后、输出节点之前插入模板转换节点，其body变量接Agent的text输出。该环节可用点号或括号读取嵌套对象或数组，例如{{user.name}}；缺失字段可用default过滤器提供默认值，例如{{user.name | default("there")}}。

失败风险：取错Agent正文输出，或把嵌套字段访问与default兜底当作同一语法。

预期行为/路由：answered / MULTI；小问数：2。

- **vital 1**：第9课的模板转换节点放在Agent之后、输出之前。
  - 必需组1（组内OR）：
    - [learn/tutorials/workflow-101/lesson-09 L35–35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/learn/tutorials/workflow-101/lesson-09.mdx#L35-L35) · `learn/tutorials/workflow-101/lesson-09#c2` · `learn/tutorials/workflow-101/lesson-09#p2`：在 Agent 节点之后、输出节点之前插入一个模板转换节点。
- **vital 2**：模板body变量接Agent的text输出。
  - 必需组1（组内OR）：
    - [learn/tutorials/workflow-101/lesson-09 L45–45](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/learn/tutorials/workflow-101/lesson-09.mdx#L45-L45) · `learn/tutorials/workflow-101/lesson-09#c2` · `learn/tutorials/workflow-101/lesson-09#p2`：- `body`：`Agent /{x} text`
- **vital 3**：该环节用点号或括号访问嵌套对象或数组元素。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/template L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/template.mdx#L20-L20) · `self-host/use-dify/nodes/template#c2` · `self-host/use-dify/nodes/template#p2`：使用双花括号引用工作流变量：`{{ variable_name }}`。可使用点号和括号语法访问嵌套对象属性和数组元素。
- **vital 4**：该环节用default过滤器给缺失字段提供默认值。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/template L76–76](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/template.mdx#L76-L76) · `self-host/use-dify/nodes/template#c6` · `self-host/use-dify/nodes/template#p6`：{{ user.email | default('No email provided') }}

## dev080 · multi/parallel_compare

Arize AX与Phoenix Cloud除密钥、项目名外各缺哪个空间字段？后者要哪类密钥？

参考答案：Arize AX还需Space ID；Phoenix Cloud还需空间主机名。Phoenix Cloud应在空间设置中创建“系统密钥”。

失败风险：将Arize的Space ID填入Phoenix空间主机名，或错用个人密钥。

预期行为/路由：answered / MULTI；小问数：2。

- **vital 1**：Arize AX还需Space ID。
  - 必需组1（组内OR）：
    - [self-host/use-dify/monitor/integrations/integrate-arize L37–37](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-arize.mdx#L37-L37) · `self-host/use-dify/monitor/integrations/integrate-arize#c3` · `self-host/use-dify/monitor/integrations/integrate-arize#p3`：点击配置后，将在 Arize 中创建的 **API Key**, **Space ID** 和 **项目名称**粘贴到配置中并保存。
    - [cloud/use-dify/monitor/integrations/integrate-arize L37–37](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-arize.mdx#L37-L37) · `cloud/use-dify/monitor/integrations/integrate-arize#c3` · `cloud/use-dify/monitor/integrations/integrate-arize#p3`：点击配置后，将在 Arize 中创建的 **API Key**, **Space ID** 和 **项目名称**粘贴到配置中并保存。
- **vital 2**：Phoenix Cloud还需空间主机名。
  - 必需组1（组内OR）：
    - [self-host/use-dify/monitor/integrations/integrate-phoenix L87–87](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-phoenix.mdx#L87-L87) · `self-host/use-dify/monitor/integrations/integrate-phoenix#c7` · `self-host/use-dify/monitor/integrations/integrate-phoenix#p7`：点击配置后，粘贴从 Phoenix Cloud 中获取的 API 密钥、项目名称 和 空间主机名 到配置项中并保存。
    - [cloud/use-dify/monitor/integrations/integrate-phoenix L87–87](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-phoenix.mdx#L87-L87) · `cloud/use-dify/monitor/integrations/integrate-phoenix#c7` · `cloud/use-dify/monitor/integrations/integrate-phoenix#p7`：点击配置后，粘贴从 Phoenix Cloud 中获取的 API 密钥、项目名称 和 空间主机名 到配置项中并保存。
- **vital 3**：Phoenix Cloud在空间设置中创建系统密钥。
  - 必需组1（组内OR）：
    - [self-host/use-dify/monitor/integrations/integrate-phoenix L73–73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-phoenix.mdx#L73-L73) · `self-host/use-dify/monitor/integrations/integrate-phoenix#c6` · `self-host/use-dify/monitor/integrations/integrate-phoenix#p6`：启动空间后，你可以在左下角的用户菜单中点击 设置 来创建 Phoenix API 密钥。点击 系统密钥，然后为你的 API 密钥命名：
    - [cloud/use-dify/monitor/integrations/integrate-phoenix L73–73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-phoenix.mdx#L73-L73) · `cloud/use-dify/monitor/integrations/integrate-phoenix#c6` · `cloud/use-dify/monitor/integrations/integrate-phoenix#p6`：启动空间后，你可以在左下角的用户菜单中点击 设置 来创建 Phoenix API 密钥。点击 系统密钥，然后为你的 API 密钥命名：

## dev081 · multi/parallel_compare

Langfuse接入缺地址和公开标识，分别填哪项？LangSmith鉴权选哪类，项目名不匹配会怎样？

参考答案：Langfuse还需Host和Public Key；LangSmith凭据选择Personal Access Token。LangSmith配置的项目名与已有项目不一致时，会自动创建新项目。

失败风险：混淆Langfuse的Public Key和Host，或把LangSmith项目名不匹配误报为鉴权失败。

预期行为/路由：answered / MULTI；小问数：2。

- **vital 1**：Langfuse需要填写Host。
  - 必需组1（组内OR）：
    - [self-host/use-dify/monitor/integrations/integrate-langfuse L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-langfuse.mdx#L42-L42) · `self-host/use-dify/monitor/integrations/integrate-langfuse#c1` · `self-host/use-dify/monitor/integrations/integrate-langfuse#p1`：复制并保存 **Secret Key**、**Public Key** 和 **Host**。
    - [cloud/use-dify/monitor/integrations/integrate-langfuse L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-langfuse.mdx#L42-L42) · `cloud/use-dify/monitor/integrations/integrate-langfuse#c1` · `cloud/use-dify/monitor/integrations/integrate-langfuse#p1`：复制并保存 **Secret Key**、**Public Key** 和 **Host**。
- **vital 2**：Langfuse需要填写Public Key。
  - 必需组1（组内OR）：
    - [self-host/use-dify/monitor/integrations/integrate-langfuse L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-langfuse.mdx#L42-L42) · `self-host/use-dify/monitor/integrations/integrate-langfuse#c1` · `self-host/use-dify/monitor/integrations/integrate-langfuse#p1`：复制并保存 **Secret Key**、**Public Key** 和 **Host**。
    - [cloud/use-dify/monitor/integrations/integrate-langfuse L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-langfuse.mdx#L42-L42) · `cloud/use-dify/monitor/integrations/integrate-langfuse#c1` · `cloud/use-dify/monitor/integrations/integrate-langfuse#p1`：复制并保存 **Secret Key**、**Public Key** 和 **Host**。
- **vital 3**：LangSmith凭据类型选择Personal Access Token。
  - 必需组1（组内OR）：
    - [self-host/use-dify/monitor/integrations/integrate-langsmith L49–49](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-langsmith.mdx#L49-L49) · `self-host/use-dify/monitor/integrations/integrate-langsmith#c2` · `self-host/use-dify/monitor/integrations/integrate-langsmith#p1`：选择 **Personal Access Token** ，用于后续的 API 身份校验。
    - [cloud/use-dify/monitor/integrations/integrate-langsmith L49–49](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-langsmith.mdx#L49-L49) · `cloud/use-dify/monitor/integrations/integrate-langsmith#c2` · `cloud/use-dify/monitor/integrations/integrate-langsmith#p1`：选择 **Personal Access Token** ，用于后续的 API 身份校验。
- **vital 4**：LangSmith配置的项目名不一致会自动创建新项目。
  - 必需组1（组内OR）：
    - [self-host/use-dify/monitor/integrations/integrate-langsmith L76–76](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-langsmith.mdx#L76-L76) · `self-host/use-dify/monitor/integrations/integrate-langsmith#c2` · `self-host/use-dify/monitor/integrations/integrate-langsmith#p1`：配置项目名需要与 LangSmith 内设置的项目一致，若项目名不一致，数据同步时 LangSmith 会自动创建一个新的项目。
    - [cloud/use-dify/monitor/integrations/integrate-langsmith L76–76](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-langsmith.mdx#L76-L76) · `cloud/use-dify/monitor/integrations/integrate-langsmith#c2` · `cloud/use-dify/monitor/integrations/integrate-langsmith#p1`：配置项目名需要与 LangSmith 内设置的项目一致，若项目名不一致，数据同步时 LangSmith 会自动创建一个新的项目。

## dev082 · multi/parallel_compare

无现成插件的接口如何接入，在画布怎样选操作和凭证，默认凭证在哪改？

参考答案：在工作空间的工具中导入OpenAPI（Swagger）规范生成工具接口。画布点击“添加节点 > 工具”，选具体操作；需要认证时选择现有凭证或新建凭证。默认凭证在“集成 > 工具 > 工具插件”修改。

失败风险：只建议HTTP节点而漏掉OpenAPI导入，或混淆画布凭据和工作空间默认凭据位置。

预期行为/路由：answered / MULTI；小问数：3。

- **vital 1**：可通过导入OpenAPI规范生成工具接口。
  - 必需组1（组内OR）：
    - [self-host/use-dify/workspace/tools L28–28](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/tools.mdx#L28-L28) · `self-host/use-dify/workspace/tools#c1` · `self-host/use-dify/workspace/tools#p1`：通过导入标准的 OpenAPI（Swagger）规范，将尚未以工具插件形式提供的服务集成进来。
    - [cloud/use-dify/workspace/tools L28–28](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/tools.mdx#L28-L28) · `cloud/use-dify/workspace/tools#c1` · `cloud/use-dify/workspace/tools#p1`：通过导入标准的 OpenAPI（Swagger）规范，将尚未以工具插件形式提供的服务集成进来。
  - 必需组2（组内OR）：
    - [self-host/use-dify/workspace/tools L30–30](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/tools.mdx#L30-L30) · `self-host/use-dify/workspace/tools#c1` · `self-host/use-dify/workspace/tools#p1`：粘贴规范、从 URL 导入，或从提供的示例开始，Dify 会自动生成工具接口。
    - [cloud/use-dify/workspace/tools L30–30](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/tools.mdx#L30-L30) · `cloud/use-dify/workspace/tools#c1` · `cloud/use-dify/workspace/tools#p1`：粘贴规范、从 URL 导入，或从提供的示例开始，Dify 会自动生成工具接口。
- **vital 2**：画布中通过添加节点>工具选择具体操作。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/tools L15–15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/tools.mdx#L15-L15) · `self-host/use-dify/nodes/tools#c0` · `self-host/use-dify/nodes/tools#p0`：1. 在画布上，点击 **添加节点** > **工具**，然后从可用工具中选择一个操作。
- **vital 3**：需认证的工具可在节点选择现有凭证或创建新凭证。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/tools L17–17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/tools.mdx#L17-L17) · `self-host/use-dify/nodes/tools#c0` · `self-host/use-dify/nodes/tools#p0`：2. 可选：如果工具需要认证，选择已有凭证或创建新凭证。
- **vital 4**：默认凭证在集成>工具>工具插件中修改。
  - 必需组1（组内OR）：
    - [self-host/use-dify/nodes/tools L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/tools.mdx#L20-L20) · `self-host/use-dify/nodes/tools#c0` · `self-host/use-dify/nodes/tools#p0`：要更改默认凭证，前往 **集成** > **工具** > **工具插件**。

## dev083 · multi/parallel_compare

自建拆子域后登录失效，要改哪两个Cookie变量？换域名后401看哪个控制台跨域项，域名共享有何边界？

参考答案：拆分子域后可检查COOKIE_DOMAIN是否为共享顶级域名，并把NEXT_PUBLIC_COOKIE_DOMAIN设为1，然后重启。更换域名后的401可检查控制台CORS变量CONSOLE_CORS_ALLOW_ORIGINS。Cookie不能跨不同可注册域名共享。这些是对应故障的排查方向，不代表唯一病因。

失败风险：混淆Cookie域与控制台CORS，或声称不同可注册域名之间也能共享Cookie。

预期行为/路由：answered / MULTI；小问数：3。

- **vital 1**：COOKIE_DOMAIN应设为前后端共享的顶级域名。
  - 必需组1（组内OR）：
    - [self-host/deploy/quick-start/faqs L75–75](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/quick-start/faqs.mdx#L75-L75) · `self-host/deploy/quick-start/faqs#c5` · `self-host/deploy/quick-start/faqs#p4`：- **`COOKIE_DOMAIN`**：设为前后端共享的顶级域名（例如 `example.com`），前导点可省略。
    - [self-host/deploy/configuration/environments L419–419](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L419-L419) · `self-host/deploy/configuration/environments#c57` · `self-host/deploy/configuration/environments#p27`：| `COOKIE_DOMAIN` | （空） | 当前端和后端运行在不同子域上时，设为共享的顶级域名（例如 `example.com`）。这允许认证 Cookie 在子域间共享。为空时 Cookie 使用最安全的 `__Host-` 前缀，并锁定到单个域。 |
- **vital 2**：NEXT_PUBLIC_COOKIE_DOMAIN应设为1以启用跨子域Cookie。
  - 必需组1（组内OR）：
    - [self-host/deploy/quick-start/faqs L76–76](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/quick-start/faqs.mdx#L76-L76) · `self-host/deploy/quick-start/faqs#c5` · `self-host/deploy/quick-start/faqs#p4`：- **`NEXT_PUBLIC_COOKIE_DOMAIN`**：设为 `1`，启用前端的跨子域名 Cookie。
    - [self-host/deploy/configuration/environments L420–420](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L420-L420) · `self-host/deploy/configuration/environments#c58` · `self-host/deploy/configuration/environments#p27`：| `NEXT_PUBLIC_COOKIE_DOMAIN` | （空） | 跨子域 Cookie 的前端标志。设为 `1`（或任何非空值）启用，后端从 `COOKIE_DOMAIN` 读取实际域名。 |
- **vital 3**：更换域名后401可检查CONSOLE_CORS_ALLOW_ORIGINS。
  - 必需组1（组内OR）：
    - [self-host/deploy/troubleshooting/common-issues L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/common-issues.mdx#L23-L23) · `self-host/deploy/troubleshooting/common-issues#c1` · `self-host/deploy/troubleshooting/common-issues#p1`：这通常发生在更改域名之后。请更新以下环境变量：
    - [self-host/deploy/configuration/environments L418–418](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L418-L418) · `self-host/deploy/configuration/environments#c57` · `self-host/deploy/configuration/environments#p27`：| `CONSOLE_CORS_ALLOW_ORIGINS` | `*` | 控制台 API 跨域请求的允许来源。如果未设置，回退到 `CONSOLE_WEB_URL`。 |
  - 必需组2（组内OR）：
    - [self-host/deploy/troubleshooting/common-issues L25–25](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/common-issues.mdx#L25-L25) · `self-host/deploy/troubleshooting/common-issues#c1` · `self-host/deploy/troubleshooting/common-issues#p1`：- `CONSOLE_CORS_ALLOW_ORIGINS` - 控制台 CORS 策略
- **vital 4**：Cookie不能跨不同可注册域名共享。
  - 必需组1（组内OR）：
    - [self-host/deploy/quick-start/faqs L83–83](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/quick-start/faqs.mdx#L83-L83) · `self-host/deploy/quick-start/faqs#c6` · `self-host/deploy/quick-start/faqs#p4`：Cookie 无法跨顶级域名共享，因此前端和后端必须位于同一可注册域名下。

## dev084 · multi/scattered_ordered

Weaviate迁移：服务端最低版本、gRPC地址格式、Dify1.11后Worker脚本选项分别是什么？

参考答案：服务端至少1.27.0；WEAVIATE_GRPC_ENDPOINT填写hostname:port，不加协议前缀。Dify1.11.0及之后在Worker执行迁移脚本使用uv run --no-cache。

失败风险：把gRPC端点加上http/grpc协议头，或漏掉新版Worker的无缓存选项。

预期行为/路由：answered / MULTI；小问数：3。

- **vital 1**：Weaviate v4客户端需要服务端1.27.0或更高版本。
  - 必需组1（组内OR）：
    - [self-host/deploy/troubleshooting/weaviate-v4-migration L15–15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L15-L15) · `self-host/deploy/troubleshooting/weaviate-v4-migration#c1` · `self-host/deploy/troubleshooting/weaviate-v4-migration#p1`：从 **Dify v1.9.2** 开始，weaviate-client 已从 v3 升级到 v4.17.0。此升级带来了显著的性能改进和更好的稳定性，但需要 **Weaviate 服务器版本 1.27.0 或更高版本**。
    - [self-host/deploy/troubleshooting/weaviate-v4-migration L18–18](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L18-L18) · `self-host/deploy/troubleshooting/weaviate-v4-migration#c1` · `self-host/deploy/troubleshooting/weaviate-v4-migration#p1`：**破坏性变更**：新的 weaviate-client v4 与 1.27.0 以下的 Weaviate 服务器版本不向后兼容。如果你正在运行 1.19.0 或更旧版本的自部署 Weaviate 实例，则必须在升级 Dify 之前升级 Weaviate 服务器。
    - [self-host/deploy/troubleshooting/weaviate-v4-migration L25–25](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L25-L25) · `self-host/deploy/troubleshooting/weaviate-v4-migration#c2` · `self-host/deploy/troubleshooting/weaviate-v4-migration#p2`：- 运行低于 1.27.0 版本的自部署 Weaviate 实例的自部署 Dify 用户
    - [self-host/deploy/troubleshooting/weaviate-v4-migration L39–39](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L39-L39) · `self-host/deploy/troubleshooting/weaviate-v4-migration#c3` · `self-host/deploy/troubleshooting/weaviate-v4-migration#p3`：1. **最低服务器版本**：需要 Weaviate 服务器 1.27.0 或更高版本
- **vital 2**：WEAVIATE_GRPC_ENDPOINT采用hostname:port格式，不含协议前缀。
  - 必需组1（组内OR）：
    - [self-host/deploy/troubleshooting/weaviate-v4-migration L503–503](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L503-L503) · `self-host/deploy/troubleshooting/weaviate-v4-migration#c35` · `self-host/deploy/troubleshooting/weaviate-v4-migration#p15`：**格式**：`hostname:port`（无协议前缀）
- **vital 3**：Dify1.11.0及之后在Worker运行迁移脚本使用uv run --no-cache。
  - 必需组1（组内OR）：
    - [self-host/deploy/troubleshooting/weaviate-v4-migration L300–300](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L300-L300) · `self-host/deploy/troubleshooting/weaviate-v4-migration#c22` · `self-host/deploy/troubleshooting/weaviate-v4-migration#p10`：# 运行迁移脚本（Dify 1.11.0+ 请使用 --no-cache）
    - [self-host/deploy/troubleshooting/weaviate-v4-migration L301–301](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L301-L301) · `self-host/deploy/troubleshooting/weaviate-v4-migration#c22` · `self-host/deploy/troubleshooting/weaviate-v4-migration#p10`：uv run --no-cache /app/api/storage/migrate_weaviate_collections.py
    - [self-host/deploy/troubleshooting/weaviate-v4-migration L809–809](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L809-L809) · `self-host/deploy/troubleshooting/weaviate-v4-migration#c53` · `self-host/deploy/troubleshooting/weaviate-v4-migration#p31`：uv run --no-cache migrate_weaviate_collections.py

## dev085 · multi/scattered_ordered

Agent构建时放弃、运行时新增文件、重开对话和恢复旧版，分别怎样影响文件或构建笔记？

参考答案：放弃构建会丢弃本次对长期文件的改动；发布后的运行中新增内容均为临时，不会改变Agent本身。每次新对话会重新读取构建笔记；恢复旧版时，沙箱长期文件也恢复到该版本。

失败风险：把构建阶段永久状态与发布后运行临时状态混淆。

预期行为/路由：answered / MULTI；小问数：4。

- **vital 1**：放弃构建会丢弃本轮对长期文件的改动。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/new-agent/build L137–137](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/build.mdx#L137-L137) · `self-host/use-dify/build/new-agent/build#c11` · `self-host/use-dify/build/new-agent/build#p9`：**放弃** 会丢弃本次构建对话中的一切：对配置以及 [**文件系统**](#文件系统) 中长期文件的所有更改。
- **vital 2**：发布后的运行中新添加内容都是临时的。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/new-agent/build L150–150](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/build.mdx#L150-L150) · `self-host/use-dify/build/new-agent/build#c14` · `self-host/use-dify/build/new-agent/build#p10`：在发布后的运行中，Agent 添加的任何内容都是临时的，因此运行中发生的一切都不会改变 Agent 本身。
- **vital 3**：每次新对话开始时Agent都会重新读取构建笔记。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/new-agent/build L156–156](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/build.mdx#L156-L156) · `self-host/use-dify/build/new-agent/build#c15` · `self-host/use-dify/build/new-agent/build#p11`：这份笔记会随 Agent 的配置一起保存。每次新对话开始时，Agent 都会重新读取笔记，将它与你的 **提示词** 组合成自己的指令。
- **vital 4**：恢复Agent版本时，沙箱长期文件也恢复到该版本。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/new-agent/build L179–179](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/build.mdx#L179-L179) · `self-host/use-dify/build/new-agent/build#c17` · `self-host/use-dify/build/new-agent/build#p12`：恢复版本时，Agent 沙箱中的长期文件也会一并恢复到该版本。

## dev086 · refuse_correct/out_of_database

社区集成报漏洞后，官方承诺多久响应、多久发补丁？

参考答案：冻结资料没有给出第三方社区集成漏洞的官方首次响应时限或补丁交付期限，无法据此报时长。这不等于官方或维护方不会处理漏洞，应查具体维护方的安全政策或支持约定。

失败风险：把社区插件维护承诺当作Dify官方SLA，编造首次响应或补丁期限。

预期行为/路由：refused / None；小问数：2。

- 边界反证、可接受行为与不同解释见evidence.json该题。

## dev087 · refuse_correct/false_premise

教我保留事件触发器，把同一流程直接发布成MCP服务。

参考答案：不能按这个前提操作。只有以用户输入启动的工作流才能发布为MCP；用户输入和触发器在同一画布互斥。若要改成这种发布方式，需切换开始节点，不能保留原触发器与用户输入并存。

失败风险：直接给出发布步骤，漏掉启动方式限制。

预期行为/路由：corrects_premise / None；小问数：1。

- 边界反证、可接受行为与不同解释见evidence.json该题。

## dev088 · refuse_correct/unrelated

我用LangGraph搭RAG，给它的PostgreSQL业务库写一套Patroni跨机房故障转移配置。

参考答案：这属于LangGraph RAG服务的PostgreSQL/Patroni高可用运维，超出冻结Dify文档范围；不能据库内资料提供完整配置，应说明范围并建议查相应系统的部署资料。

失败风险：看到RAG与PostgreSQL就误认为库内有对应运维方案，编造Patroni完整配置。

预期行为/路由：refused / REFUSE；小问数：1。

- 边界反证、可接受行为与不同解释见evidence.json该题。

## dev089 · clarify/version_unspecified

别人导出的DSL，导入就一定兼容吗？

参考答案：需要确认导入目标是Dify Cloud还是社区自部署。冻结Cloud资料说明平台始终使用最新DSL版本，导入文件兼容；自部署导入由较新Dify导出的DSL前可能需要升级。可先澄清目标部署和相对版本，也可给上述条件答案。

失败风险：把平台持续更新与某个旧的社区实例当作相同前提。

预期行为/路由：clarified_or_conditional_answer / CLARIFY；小问数：1。

- 边界反证、可接受行为与不同解释见evidence.json该题。

## dev090 · clarify/missing_slot

想把外部系统的资料接进来，怎么配？

参考答案：先确认外部系统是已有知识检索服务，还是按当前输入返回资料的业务API。前者连接外部知识库API，数据和检索逻辑仍由外部维护，Dify只有检索权限；后者用外部数据工具，把应用变量或对话输入交给API，返回字符串补进提示词。

失败风险：未确认资料接入形态就一律走外部知识库，漏掉业务API返回字符串补入提示词的路径。

预期行为/路由：clarified_or_conditional_answer / CLARIFY；小问数：1。

- 边界反证、可接受行为与不同解释见evidence.json该题。
