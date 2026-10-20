# batch-03 当前审阅稿

2026-10-20复审修订稿；逐项原因见repair-2026-10-20.json及revision-log.md。所有原样检索和数据库记录为修订前历史证据，本版本未复跑。

## dev045 · single/synonym

怎样把调好的步骤打包并接上未选部分的取值？原组合再改会同步吗？

参考答案：选中调好的节点，右键创建Snippet。外部变量引用会成为它的输入；插入后要为各输入映射当前流程里的变量。插入的是副本，原组合后续改动不会同步到已使用的流程。

失败风险：把复用副本误作实时链接，或漏掉插入后的变量映射。

预期行为/路由：answered / SINGLE；小问数：4。

- **vital 1**：选中要复用的节点，右键选择创建Snippet。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/snippet L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/snippet.mdx#L20-L20) · `self-host/use-dify/build/snippet#c1` · `self-host/use-dify/build/snippet#p1`：    选中想要复用的节点，右键点击并选择 **创建 Snippet**。
- **vital 2**：未选中节点的输出等外部变量引用会成为Snippet输入变量。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/snippet L22–22](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/snippet.mdx#L22-L22) · `self-host/use-dify/build/snippet#c1` · `self-host/use-dify/build/snippet#p1`：    这些节点的配置会一并保存到 Snippet 中。它们引用的外部变量（未选中节点的输出、环境变量等）会成为该 Snippet 的 [输入变量](#编辑-snippet)。
- **vital 3**：插入后应为各输入变量映射当前流程的实际变量。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/snippet L56–56](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/snippet.mdx#L56-L56) · `self-host/use-dify/build/snippet#c5` · `self-host/use-dify/build/snippet#p4`：Snippet 会以副本形式添加到画布上。在插入的节点中，为每个输入变量指定工作流里对应的变量，让它们获取所需的数据。
- **vital 4**：原始Snippet之后的修改不影响已插入它的流程。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/snippet L58–58](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/snippet.mdx#L58-L58) · `self-host/use-dify/build/snippet#c5` · `self-host/use-dify/build/snippet#p4`：之后修改原始 Snippet 不会影响已经使用它的工作流，反之亦然。

## dev046 · single/synonym

只找眼前画布里的步骤，键盘怎么用？组合键失灵还有何入口？

参考答案：macOS按⌘+K，Windows/Linux按Ctrl+K，再用@node只查当前打开画布里的节点。组合键失效可点侧边栏顶部搜索按钮。

失败风险：搜到其他画布的同名步骤，或把组合键冲突误判为不可使用。

预期行为/路由：answered / SINGLE；小问数：3。

- **vital 1**：macOS用⌘+K，Windows/Linux用Ctrl+K打开入口。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/goto-anything L12–12](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/goto-anything.mdx#L12-L12) · `self-host/use-dify/build/goto-anything#c1` · `self-host/use-dify/build/goto-anything#p1`：在 macOS 上按 `⌘ + K`，在 Windows/Linux 上按 `Ctrl + K`，或点击侧边栏顶部的搜索按钮。
- **vital 2**：使用@node仅查当前打开画布的节点。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/goto-anything L27–27](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/goto-anything.mdx#L27-L27) · `self-host/use-dify/build/goto-anything#c2` · `self-host/use-dify/build/goto-anything#p2`：- `@node`：在当前打开的画布中搜索节点（工作流和知识流水线中可用）
- **vital 3**：组合键失效时可点击侧边栏顶部按钮。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/goto-anything L12–12](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/goto-anything.mdx#L12-L12) · `self-host/use-dify/build/goto-anything#c1` · `self-host/use-dify/build/goto-anything#p1`：在 macOS 上按 `⌘ + K`，在 Windows/Linux 上按 `Ctrl + K`，或点击侧边栏顶部的搜索按钮。
  - 必需组2（组内OR）：
    - [self-host/use-dify/build/goto-anything L15–15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/goto-anything.mdx#L15-L15) · `self-host/use-dify/build/goto-anything#c1` · `self-host/use-dify/build/goto-anything#p1`：如果快捷键没有反应，可能是其他应用或浏览器扩展占用了它。侧边栏按钮始终可用。

## dev047 · single/synonym

两人改同一元素谁的会留下？讨论留言会随修订消失吗？

参考答案：同一元素的冲突以最后一次编辑为准；画布评论跨流程版本保留。

失败风险：假称锁定先编辑者，或说新版本会删评论。

预期行为/路由：answered / SINGLE；小问数：2。

- **vital 1**：同一元素发生编辑冲突时，以最后一次编辑为准。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/workflow-collaboration L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/workflow-collaboration.mdx#L23-L23) · `self-host/use-dify/build/workflow-collaboration#c1` · `self-host/use-dify/build/workflow-collaboration#p1`：拥有编辑权限及以上的工作空间成员可同时编辑同一个工作流。当两位成员同时修改同一个元素时，以最后一次编辑为准。
- **vital 2**：画布评论跨流程版本保留。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/workflow-collaboration L27–27](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/workflow-collaboration.mdx#L27-L27) · `self-host/use-dify/build/workflow-collaboration#c2` · `self-host/use-dify/build/workflow-collaboration#p2`：右键点击画布的空白区域并选择 **添加评论** 留下一条评论。要连续添加多条评论，按 `C` 键进入评论模式。评论会跨工作流版本保留。

## dev048 · single/numeric_table

回复后的建议提示词和同输入生成的结果变体，各有什么数量限制？

参考答案：下一步问题建议的自定义提示词最多1000字符；生成更多类似内容时，每条原结果最多生成2个变体，每个变体额外消耗token。

失败风险：把文件上传大小限额错套给建议提示词字符数，或把变体数说成可无限生成。

预期行为/路由：answered / SINGLE；小问数：1。

- **vital 1**：下一步问题建议的自定义提示词最多1000字符。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/additional-features L50–50](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/additional-features.mdx#L50-L50) · `self-host/use-dify/build/additional-features#c2` · `self-host/use-dify/build/additional-features#p2`：点击 **设置** 可选择用于生成问题的模型，或编写自定义提示词（最多 1,000 字符）来调整问题的数量、措辞或长度。
- **vital 2**：生成更多类似内容时，每条结果最多生成2个变体。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/additional-features L135–135](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/additional-features.mdx#L135-L135) · `self-host/use-dify/build/additional-features#c9` · `self-host/use-dify/build/additional-features#p9`：每条结果最多可生成 2 个变体，每个变体都会消耗额外的 token。

## dev049 · single/numeric_table

云端扩员前，免费档和两个付费档各能容纳多少成员？

参考答案：Sandbox最多1名成员，Professional最多3名，Team最多50名。

失败风险：把团队人数与知识库请求频率或单次上传数量混淆，误认为两个付费档上限相同。

预期行为/路由：answered / SINGLE；小问数：1。

- **vital 1**：Sandbox工作空间最多1名成员。
  - 必需组1（组内OR）：
    - [cloud/use-dify/workspace/team-members-management L14–14](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/team-members-management.mdx#L14-L14) · `cloud/use-dify/workspace/team-members-management#c1` · `cloud/use-dify/workspace/team-members-management#p1`：- **Sandbox**：1 个成员
- **vital 2**：Professional工作空间最多3名成员。
  - 必需组1（组内OR）：
    - [cloud/use-dify/workspace/team-members-management L15–15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/team-members-management.mdx#L15-L15) · `cloud/use-dify/workspace/team-members-management#c1` · `cloud/use-dify/workspace/team-members-management#p1`：- **Professional**：3 个成员
- **vital 3**：Team工作空间最多50名成员。
  - 必需组1（组内OR）：
    - [cloud/use-dify/workspace/team-members-management L16–16](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/team-members-management.mdx#L16-L16) · `cloud/use-dify/workspace/team-members-management#c1` · `cloud/use-dify/workspace/team-members-management#p1`：- **Team**：50 个成员

## dev050 · single/neighbor

需要可装程序改文件的沙箱助理，选哪类应用？固定能力和每次任务如何区分？

参考答案：用新的Agent，它能在自己的沙箱运行命令、安装程序、读写文件。能力是预先配置的角色、模型、Skill、工具和文件等；任务是一次消息，或工作流给节点的指令。

失败风险：把仅调用已配工具的旧Agent当作独立沙箱，混淆能力与任务。

预期行为/路由：answered / SINGLE；小问数：3。

- **vital 1**：应使用在自有沙箱运行命令、安装程序和读写文件的新Agent。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/new-agent/overview L25–25](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/overview.mdx#L25-L25) · `self-host/use-dify/build/new-agent/overview#c1` · `self-host/use-dify/build/new-agent/overview#p0`：- 它在 **自己的沙箱** 中工作：可运行命令、安装程序、读写文件，因此能承担开放式的工作，而不只是调用你配置好的工具。
- **vital 2**：能力是预先塑造的角色、模型、Skill、工具和文件等配置。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/new-agent/overview L35–35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/overview.mdx#L35-L35) · `self-host/use-dify/build/new-agent/overview#c2` · `self-host/use-dify/build/new-agent/overview#p1`：- **能力（可视为 Agent 的灵魂）决定了 Agent 是谁。**
  - 必需组2（组内OR）：
    - [self-host/use-dify/build/new-agent/overview L37–37](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/overview.mdx#L37-L37) · `self-host/use-dify/build/new-agent/overview#c2` · `self-host/use-dify/build/new-agent/overview#p1`：  包括你编写的角色和提示词、它运行的模型，以及你提供的 Skill、Dify 工具和文件。塑造一次后，可随着你逐渐摸清 Agent 需要什么而不断打磨。
- **vital 3**：任务是单次运行的消息，或流程中给节点的指令。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/new-agent/overview L39–39](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/overview.mdx#L39-L39) · `self-host/use-dify/build/new-agent/overview#c2` · `self-host/use-dify/build/new-agent/overview#p1`：- **任务是你在一次运行中要它做的事。**
  - 必需组2（组内OR）：
    - [self-host/use-dify/build/new-agent/overview L41–41](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/overview.mdx#L41-L41) · `self-host/use-dify/build/new-agent/overview#c2` · `self-host/use-dify/build/new-agent/overview#p1`：  Agent 独立工作时，任务是你发给它的消息；在工作流中时，任务是你给节点的指令。

## dev051 · single/neighbor

旧版工具助理为什么漏选资料，怎样改进选库判断？

参考答案：旧版Agent会评估每条用户查询与知识库描述的相关性，再决定是否检索；把知识库描述写详细，可以改善相关性判断。

失败风险：误套聊天助手每条消息都检索的机制，未说明知识库描述对相关性决策的作用。

预期行为/路由：answered / SINGLE；小问数：2。

- **vital 1**：旧版Agent按每条查询与知识库描述的相关性决定是否检索。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/agent L130–130](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/agent.mdx#L130-L130) · `self-host/use-dify/build/agent#c7` · `self-host/use-dify/build/agent#p3`：模型会评估每条用户查询与知识库描述的相关性，并决定是否需要检索。你无需在提示词中提及知识库。
- **vital 2**：写更详细的知识库描述能改善相关性判断。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/agent L132–132](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/agent.mdx#L132-L132) · `self-host/use-dify/build/agent#c7` · `self-host/use-dify/build/agent#p3`：**知识库描述越详细，模型判断相关性就越准确**，从而实现更精准的检索。

## dev052 · single/short

恢复旧版后草稿怎样变化，如何更新线上？

参考答案：旧版重新载入草稿并完全替换当前草稿；要上线还需点发布→发布更新。

失败风险：将恢复草稿等同于自动上线。

预期行为/路由：answered / SINGLE；小问数：2。

- **vital 1**：恢复旧版会把它载入草稿，完全替换当前草稿。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/version-control L88–88](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/version-control.mdx#L88-L88) · `self-host/use-dify/build/version-control#c4` · `self-host/use-dify/build/version-control#p4`：**恢复版本**：将旧版本重新加载到你的草稿中
  - 必需组2（组内OR）：
    - [self-host/use-dify/build/version-control L95–95](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/version-control.mdx#L95-L95) · `self-host/use-dify/build/version-control#c4` · `self-host/use-dify/build/version-control#p4`：  这将完全替换你当前的草稿。确保你没有未保存的工作。
- **vital 2**：需点击发布→发布更新才使草稿上线。
  - 必需组1（组内OR）：
    - [self-host/use-dify/build/version-control L36–36](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/version-control.mdx#L36-L36) · `self-host/use-dify/build/version-control#c2` · `self-host/use-dify/build/version-control#p2`：点击 **发布** → **发布更新** 以使你的草稿上线。

## dev053 · single/short

单独跑前端时，两类域名不同用什么配置？

参考答案：控制台域用CONSOLE_URL，Web应用域用APP_URL，可分别设置。前端可直接用Docker镜像运行。

失败风险：混淆CONSOLE_URL/APP_URL与后端API地址变量。

预期行为/路由：answered / SINGLE；小问数：2。

- **vital 1**：控制台域与Web应用域分别由CONSOLE_URL和APP_URL设置。
  - 必需组1（组内OR）：
    - [self-host/deploy/advanced-deployments/start-the-frontend-docker-container L29–29](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/start-the-frontend-docker-container.mdx#L29-L29) · `self-host/deploy/advanced-deployments/start-the-frontend-docker-container#c1` · `self-host/deploy/advanced-deployments/start-the-frontend-docker-container#p0`：3. 当控制台域和 Web 应用域不同时，可以分别设置 CONSOLE_URL 和 APP_URL
- **okay 2**：可直接拉取Docker镜像运行前端服务。
  - 必需组1（组内OR）：
    - [self-host/deploy/advanced-deployments/start-the-frontend-docker-container L7–7](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/start-the-frontend-docker-container.mdx#L7-L7) · `self-host/deploy/advanced-deployments/start-the-frontend-docker-container#c0` · `self-host/deploy/advanced-deployments/start-the-frontend-docker-container#p0`：在单独开发后端时，你可能只需要从源代码启动后端服务，而无需在本地构建和启动前端。在这种情况下，你可以通过拉取 Docker 镜像并运行容器来直接启动前端服务。以下是具体步骤：

## dev054 · single/single_version

社区部署的空间何时创建，初始管理员凭据从哪来？

参考答案：安装时创建工作空间；用初始化阶段设置的管理员邮箱和密码登录。

失败风险：套用Cloud首次登录创建规则。

预期行为/路由：answered / SINGLE；小问数：2。

- **vital 1**：社区部署在安装时创建工作空间。
  - 必需组1（组内OR）：
    - [self-host/use-dify/workspace/readme L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/readme.mdx#L20-L20) · `self-host/use-dify/workspace/readme#c2` · `self-host/use-dify/workspace/readme#p2`：安装时会创建一个工作空间，使用你在初始化阶段设置的管理员邮箱和密码。
- **vital 2**：使用初始化阶段设置的管理员邮箱和密码。
  - 必需组1（组内OR）：
    - [self-host/use-dify/workspace/readme L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/readme.mdx#L20-L20) · `self-host/use-dify/workspace/readme#c2` · `self-host/use-dify/workspace/readme#p2`：安装时会创建一个工作空间，使用你在初始化阶段设置的管理员邮箱和密码。

## dev055 · multi/chain

云端报provider_not_initialize，原因和修复入口是什么？沿这个入口，谁能维护，手动添入列表的条目删掉最后一把密钥会怎样？

参考答案：该错误表示应用模型没有有效凭据，需修复Dify中的应用模型配置。该处由工作空间所有者或管理员管理；若删掉某自定义模型唯一的密钥，该模型也会一并删除。

失败风险：反复原样重试，或忽略管理权限和唯一凭据删除后的模型生命周期。

预期行为/路由：answered / MULTI；小问数：4。

- **vital 1**：provider_not_initialize表示应用模型没有有效凭据。
  - 必需组1（组内OR）：
    - [api-reference/guides/errors L37–37](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/errors.mdx#L37-L37) · `api-reference/guides/errors#c2` · `api-reference/guides/errors#p2`：- `provider_not_initialize`：没有有效的模型凭据
- **vital 2**：应在Dify中修复应用的模型配置。
  - 必需组1（组内OR）：
    - [api-reference/guides/errors L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/errors.mdx#L42-L42) · `api-reference/guides/errors#c2` · `api-reference/guides/errors#p2`：这些错误重试无济于事，需在 Dify 中修复应用的模型配置。
- **vital 3**：只有工作空间所有者和管理员可以管理供应商。
  - 必需组1（组内OR）：
    - [cloud/use-dify/workspace/model-providers L13–13](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/model-providers.mdx#L13-L13) · `cloud/use-dify/workspace/model-providers#c0` · `cloud/use-dify/workspace/model-providers#p0`：只有工作空间所有者和管理员可以管理供应商。你添加的任何密钥都在整个工作空间内生效，并通过你自己的供应商账户计费。
    - [self-host/use-dify/workspace/model-providers L11–11](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/model-providers.mdx#L11-L11) · `self-host/use-dify/workspace/model-providers#c0` · `self-host/use-dify/workspace/model-providers#p0`：API 密钥授予工作空间范围的模型访问权限，并会通过各供应商的账户直接计费。只有工作空间所有者和管理员可以管理供应商。
- **vital 4**：删除自定义模型唯一的密钥时，该模型也会被删除。
  - 必需组1（组内OR）：
    - [cloud/use-dify/workspace/model-providers L73–73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/model-providers.mdx#L73-L73) · `cloud/use-dify/workspace/model-providers#c5` · `cloud/use-dify/workspace/model-providers#p5`：    自定义模型依赖于自己的密钥。删除它唯一的密钥时，该模型也会一并删除。
    - [self-host/use-dify/workspace/model-providers L54–54](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/model-providers.mdx#L54-L54) · `self-host/use-dify/workspace/model-providers#c3` · `self-host/use-dify/workspace/model-providers#p3`：    你添加的模型依赖于自己的凭据。删除它唯一的凭据时，该模型也会一并删除。

## dev056 · multi/chain

自建库要模型生成结构化问答，用哪个内置方案？其材料产出顺序和适合文体呢？

参考答案：选LLM生成问答模板，产出问答模式。其处理先将上传文本分段，总结内容后为每段生成Q&A匹配对；具有完整语法结构的自然语言常见问题文档更适合该方法。

失败风险：选Simple Q&A而非LLM生成问答，或只解释QtoQ不回答处理顺序与文体。

预期行为/路由：answered / MULTI；小问数：3。

- **vital 1**：选择LLM生成问答模板，其分段结构为问答模式。
  - 必需组1（组内OR）：
    - [self-host/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline L44–44](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline.mdx#L44-L44) · `self-host/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline#c5` · `self-host/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline#p2`：| LLM 生成问答（LLM Generated Q&A) | 问答模式 | 高质量 | 向量搜索 - 加权评分 | 使用大型语言模型自动生成结构化的问答对，通过问题匹配机制找到相关的答案信息。 |
    - [cloud/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline L44–44](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline.mdx#L44-L44) · `cloud/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline#c5` · `cloud/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline#p2`：| LLM 生成问答（LLM Generated Q&A) | 问答模式 | 高质量 | 向量搜索 - 加权评分 | 使用大型语言模型自动生成结构化的问答对，通过问题匹配机制找到相关的答案信息。 |
- **vital 2**：该模式先将上传文本分段，总结内容后为每段生成Q&A匹配对。
  - 必需组1（组内OR）：
    - [self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods.mdx#L42-L42) · `self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#c3` · `self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#p2`：    开启该模式后，系统将对已上传的文本进行分段。总结内容后为每个分段自动生成 Q&A 匹配对。
- **vital 3**：具备完整语法结构的自然语言常见问题文档更适合该方法。
  - 必需组1（组内OR）：
    - [self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods L44–44](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods.mdx#L44-L44) · `self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#c3` · `self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#p2`：    与常见的 「Q to P」（用户问题匹配文本段落）策略不同，Q&A 模式采用 「Q to Q」（问题匹配问题）策略。
  - 必需组2（组内OR）：
    - [self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods L46–46](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods.mdx#L46-L46) · `self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#c3` · `self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#p2`：    这种方法特别有效，因为常见问题文档中的文本 **通常是具备完整语法结构的自然语言**。

## dev057 · multi/chain

本地HTTP接笔记型数据源，该选哪种授权、模式配置填什么？沿该方式怎样取密钥并加载？

参考答案：这里对应Notion。本地HTTP用内部集成（NOTION_INTEGRATION_TYPE=internal）；在Capabilities按需配置后，到Secrets选项卡点击Show复制密钥，改好环境变量后重启Dify加载。公开方式的Keys不适用于这里选择的分支。

失败风险：误用公开OAuth，混淆Notion所有者与Dify管理员。

预期行为/路由：answered / MULTI；小问数：2。

- **vital 1**：本地HTTP使用内部集成，NOTION_INTEGRATION_TYPE取internal。
  - 必需组1（组内OR）：
    - [self-host/deploy/troubleshooting/integrations L9–9](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/integrations.mdx#L9-L9) · `self-host/deploy/troubleshooting/integrations#c0` · `self-host/deploy/troubleshooting/integrations#p0`：Notion OAuth 仅支持 HTTPS，因此本地部署必须使用内部集成。
    - [self-host/deploy/configuration/environments L1120–1120](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L1120-L1120) · `self-host/deploy/configuration/environments#c137` · `self-host/deploy/configuration/environments#p41`：| `NOTION_INTEGRATION_TYPE` | `public` | `public` 使用标准 OAuth 2.0（需要 HTTPS 重定向 URL，需要 CLIENT_ID + CLIENT_SECRET）。`internal` 使用直接集成令牌（支持 HTTP）。本地部署建议使用 `internal`。 |
  - 必需组2（组内OR）：
    - [self-host/deploy/troubleshooting/integrations L16–16](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/integrations.mdx#L16-L16) · `self-host/deploy/troubleshooting/integrations#c1` · `self-host/deploy/troubleshooting/integrations#p1`：NOTION_INTEGRATION_TYPE=internal
    - [self-host/deploy/configuration/environments L1120–1120](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L1120-L1120) · `self-host/deploy/configuration/environments#c137` · `self-host/deploy/configuration/environments#p41`：| `NOTION_INTEGRATION_TYPE` | `public` | `public` 使用标准 OAuth 2.0（需要 HTTPS 重定向 URL，需要 CLIENT_ID + CLIENT_SECRET）。`internal` 使用直接集成令牌（支持 HTTP）。本地部署建议使用 `internal`。 |
- **vital 2**：内部集成从Secrets选项卡点击Show复制密钥。
  - 必需组1（组内OR）：
    - [self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion L64–64](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion.mdx#L64-L64) · `self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#c6` · `self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#p5`：在 **Capabilities** 选项卡下按需更新集成设置，然后在 **Secrets** 下点击 **Show** 复制密钥。
- **vital 3**：更改环境变量后需重启Dify加载新配置。
  - 必需组1（组内OR）：
    - [self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion L99–99](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion.mdx#L99-L99) · `self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#c7` · `self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#p5`：重启 Dify 以加载新的环境变量。之后即可按上述步骤授权 Notion 并导入数据。

## dev058 · multi/chain

云端取消付费何时转免费档？此后知识库容量和超额旧资料的去留与检索呢？

参考答案：已付费周期结束后才恢复Sandbox；其知识库存储容量为50 MB。已有资料即使超额也不会被删除，应用仍可检索。

失败风险：把取消视为立即降级，或把50 MB当单文件上限并误称旧数据被删。

预期行为/路由：answered / MULTI；小问数：4。

- **vital 1**：取消后保留当前计划直到已付费周期结束，随后恢复Sandbox。
  - 必需组1（组内OR）：
    - [cloud/use-dify/workspace/subscription-management L22–22](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/subscription-management.mdx#L22-L22) · `cloud/use-dify/workspace/subscription-management#c1` · `cloud/use-dify/workspace/subscription-management#p1`：- **取消或更新付款方式**：点击 **管理**（Manage）打开 Stripe 计费门户，在其中取消订阅或更改付款方式。取消后，工作空间会保留当前计划直到已付费周期结束，随后恢复为免费的 Sandbox 计划。
- **vital 2**：Sandbox的知识库存储容量为50 MB。
  - 必需组1（组内OR）：
    - [cloud/use-dify/knowledge/knowledge-storage-limit L15–15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L15-L15) · `cloud/use-dify/knowledge/knowledge-storage-limit#c0` · `cloud/use-dify/knowledge/knowledge-storage-limit#p0`：| Sandbox | 50 MB |
- **vital 3**：降级造成已有数据超过新限额时，数据不会被删除。
  - 必需组1（组内OR）：
    - [cloud/use-dify/knowledge/knowledge-storage-limit L53–53](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L53-L53) · `cloud/use-dify/knowledge/knowledge-storage-limit#c3` · `cloud/use-dify/knowledge/knowledge-storage-limit#p3`：如果套餐降级或订阅到期导致现有数据超出新套餐的上限，数据不会被删除：应用仍可正常检索这些知识库，但在用量降到限额以内或重新升级前，无法再新增内容。
- **vital 4**：降级造成已有数据超额时，应用仍能正常检索。
  - 必需组1（组内OR）：
    - [cloud/use-dify/knowledge/knowledge-storage-limit L53–53](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L53-L53) · `cloud/use-dify/knowledge/knowledge-storage-limit#c3` · `cloud/use-dify/knowledge/knowledge-storage-limit#p3`：如果套餐降级或订阅到期导致现有数据超出新套餐的上限，数据不会被删除：应用仍可正常检索这些知识库，但在用量降到限额以内或重新升级前，无法再新增内容。

## dev059 · multi/parallel_compare

旧版Agent和文本生成API的返回方式有何差别？两者流式正文各用什么事件？

参考答案：旧版Agent仅支持流式，回复正文由agent_message事件承载（另有agent_thought思考事件）；文本生成可阻塞也可流式，流式正文使用message事件。只要求比较返回方式与正文事件，不考会话记忆。

失败风险：混用Agent的agent_message与普通message事件，或错误承诺旧版Agent支持阻塞返回。

预期行为/路由：answered / MULTI；小问数：2。

- **vital 1**：旧版Agent应用仅支持流式返回。
  - 必需组1（组内OR）：
    - [api-reference/guides/chat L17–17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/chat.mdx#L17-L17) · `api-reference/guides/chat#c1` · `api-reference/guides/chat#p1`：旧版 Agent 应用仅支持流式返回。
    - [api-reference/guides/streaming L18–18](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx#L18-L18) · `api-reference/guides/streaming#c1` · `api-reference/guides/streaming#p1`：旧版 Agent 和 Agent 应用仅支持流式返回。
- **vital 2**：文本生成API支持阻塞式返回，也支持流式返回。
  - 必需组1（组内OR）：
    - [api-reference/guides/completion L17–17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/completion.mdx#L17-L17) · `api-reference/guides/completion#c1` · `api-reference/guides/completion#p1`：阻塞式返回在生成完成后一次性返回全部内容；流式返回持续输出 `message` 事件，直至 `message_end`（应用开启文字转语音自动播放时还会收到 `tts_message` 事件）。
- **vital 3**：旧版Agent流式正文使用agent_message事件。
  - 必需组1（组内OR）：
    - [api-reference/guides/chat L9–9](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/chat.mdx#L9-L9) · `api-reference/guides/chat#c0` · `api-reference/guides/chat#p0`：聊天助手应用以 `message` 事件流式返回回复，旧版 Agent 应用则返回 `agent_thought` 和 `agent_message` 事件。
    - [api-reference/guides/streaming L71–71](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx#L71-L71) · `api-reference/guides/streaming#c5` · `api-reference/guides/streaming#p3`：- 旧版 Agent 和 Agent 应用为 `agent_message` 事件
- **vital 4**：文本生成API流式正文使用message事件。
  - 必需组1（组内OR）：
    - [api-reference/guides/completion L17–17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/completion.mdx#L17-L17) · `api-reference/guides/completion#c1` · `api-reference/guides/completion#p1`：流式返回持续输出 `message` 事件，直至 `message_end`（应用开启文字转语音自动播放时还会收到 `tts_message` 事件）。

## dev060 · multi/parallel_compare

聊天页如何隔开多主题记忆？任务页适合什么任务，跑CSV每行含义与编码呢？

参考答案：聊天网页按各对话线程分别维护记忆和上下文。Workflow任务页适合产出特定结果的离散任务；批处理CSV每一行执行一次，文件须用Unicode UTF-8编码。

失败风险：将CSV整批当一次执行，或把聊天线程的记忆套给离散任务。

预期行为/路由：answered / MULTI；小问数：4。

- **vital 1**：聊天Web应用各对话线程维护各自记忆和上下文。
  - 必需组1（组内OR）：
    - [self-host/use-dify/publish/webapp/chatflow-webapp L103–103](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/webapp/chatflow-webapp.mdx#L103-L103) · `self-host/use-dify/publish/webapp/chatflow-webapp#c5` · `self-host/use-dify/publish/webapp/chatflow-webapp#p5`：每个对话线程都维护自己的记忆和上下文。用户可以在不同主题或项目间无缝切换。
- **vital 2**：Workflow网页用于产生特定输出的离散任务。
  - 必需组1（组内OR）：
    - [self-host/use-dify/publish/webapp/workflow-webapp L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/webapp/workflow-webapp.mdx#L20-L20) · `self-host/use-dify/publish/webapp/workflow-webapp#c1` · `self-host/use-dify/publish/webapp/workflow-webapp#p1`：与维护对话上下文的聊天应用不同，Workflow 应用设计用于产生特定输出的离散任务。
- **vital 3**：批处理CSV的每一行都是一次Workflow执行。
  - 必需组1（组内OR）：
    - [self-host/use-dify/publish/webapp/workflow-webapp L88–88](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/webapp/workflow-webapp.mdx#L88-L88) · `self-host/use-dify/publish/webapp/workflow-webapp#c4` · `self-host/use-dify/publish/webapp/workflow-webapp#p4`：    在模板中填入你的输入数据。每一行都会成为一次工作流执行。
- **vital 4**：从Excel导出导入用CSV时应选Unicode UTF-8编码。
  - 必需组1（组内OR）：
    - [self-host/use-dify/publish/webapp/workflow-webapp L108–108](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/webapp/workflow-webapp.mdx#L108-L108) · `self-host/use-dify/publish/webapp/workflow-webapp#c5` · `self-host/use-dify/publish/webapp/workflow-webapp#p5`：CSV 文件必须使用 Unicode 编码以防止导入失败。从 Excel 或类似工具保存时，请明确选择「Unicode (UTF-8)」编码。

## dev061 · multi/scattered_ordered

Windows源码调试：API前起哪些依赖，消费者需哪些兼容选项，定时服务怎么起？

参考答案：先用middleware配置启动数据库、沙箱和插件守护进程，可执行docker compose --env-file middleware.env -f docker-compose.middleware.yaml -p dify up -d。Windows的Celery Worker需-P solo --without-gossip --without-mingle兼容选项；定时服务另开终端运行uv run celery -A app.celery beat。文档完整Worker命令中的队列清单不是本题必答项。

失败风险：Windows误用默认进程池，或遗漏定时任务独立beat服务。

预期行为/路由：answered / MULTI；小问数：3。

- **vital 1**：启动API前，用middleware配置启动数据库、沙箱和插件守护进程。
  - 必需组1（组内OR）：
    - [self-host/deploy/advanced-deployments/local-source-code L33–33](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L33-L33) · `self-host/deploy/advanced-deployments/local-source-code#c5` · `self-host/deploy/advanced-deployments/local-source-code#p2`：启动后端前，先用 Docker Compose 启动数据库、[沙箱](https://github.com/langgenius/dify-sandbox)和[插件守护进程](https://github.com/langgenius/dify-plugin-daemon)。
  - 必需组2（组内OR）：
    - [self-host/deploy/advanced-deployments/local-source-code L41–41](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L41-L41) · `self-host/deploy/advanced-deployments/local-source-code#c5` · `self-host/deploy/advanced-deployments/local-source-code#p2`：docker compose --env-file middleware.env -f docker-compose.middleware.yaml -p dify up -d
- **vital 2**：Windows的Celery Worker命令使用-P solo --without-gossip --without-mingle。
  - 必需组1（组内OR）：
    - [self-host/deploy/advanced-deployments/local-source-code L124–124](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L124-L124) · `self-host/deploy/advanced-deployments/local-source-code#c10` · `self-host/deploy/advanced-deployments/local-source-code#p5`：    如果你使用 Windows 系统启动 Worker 服务，请使用以下命令：
  - 必需组2（组内OR）：
    - [self-host/deploy/advanced-deployments/local-source-code L128–128](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L128-L128) · `self-host/deploy/advanced-deployments/local-source-code#c11` · `self-host/deploy/advanced-deployments/local-source-code#p5`：    uv run celery -A app.celery worker -P solo --without-gossip --without-mingle --loglevel INFO -Q dataset,dataset_summary,priority_dataset,priority_pipeline,pipeline,mail,ops_trace,app_deletion,plugin,workflow_storage,conversation,workflow,schedule_poller,schedule_executor,triggered_workflow_dispatcher,trigger_refresh_executor,retention,workflow_based_app_execution
- **vital 3**：定时任务需另起uv run celery -A app.celery beat服务。
  - 必需组1（组内OR）：
    - [self-host/deploy/advanced-deployments/local-source-code L201–201](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L201-L201) · `self-host/deploy/advanced-deployments/local-source-code#c16` · `self-host/deploy/advanced-deployments/local-source-code#p7`：如需调试 celery 定时任务或运行定时触发器节点，可以在另一个终端中运行以下命令启动 beat 服务：
  - 必需组2（组内OR）：
    - [self-host/deploy/advanced-deployments/local-source-code L204–204](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L204-L204) · `self-host/deploy/advanced-deployments/local-source-code#c16` · `self-host/deploy/advanced-deployments/local-source-code#p7`：uv run celery -A app.celery beat

## dev062 · multi/scattered_ordered

自建流程外链预览、容器取文件及旧链接过期，分别查何配置，地址留空会怎样？

参考答案：外链预览/下载用FILES_URL，留空回退CONSOLE_API_URL；两者都空则无法预览。容器内取文件用INTERNAL_FILES_URL，留空用FILES_URL，内部无法访问外部地址时应单独配置。签名链接时效由FILES_ACCESS_TIMEOUT按秒控制，过期需重新请求。

失败风险：只设置公网地址，或将签名过期误作文件已被删除。

预期行为/路由：answered / MULTI；小问数：4。

- **vital 1**：FILES_URL是预览和下载基础URL，留空回退CONSOLE_API_URL。
  - 必需组1（组内OR）：
    - [self-host/deploy/configuration/environments L89–89](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L89-L89) · `self-host/deploy/configuration/environments#c10` · `self-host/deploy/configuration/environments#p9`：默认值：（空；回退到 `CONSOLE_API_URL`）
  - 必需组2（组内OR）：
    - [self-host/deploy/configuration/environments L91–91](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L91-L91) · `self-host/deploy/configuration/environments#c10` · `self-host/deploy/configuration/environments#p9`：文件预览和下载链接的基础 URL。Dify 为所有文件（上传的文档、工具输出、工作空间 Logo）生成签名的限时 URL，并提供给前端和多模态模型使用。
- **vital 2**：FILES_URL与CONSOLE_API_URL都为空时，文件预览无法工作。
  - 必需组1（组内OR）：
    - [self-host/deploy/configuration/environments L93–93](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L93-L93) · `self-host/deploy/configuration/environments#c10` · `self-host/deploy/configuration/environments#p9`：如果你使用文件处理插件，或希望文件 URL 使用专用域名，请设置此变量。如果 `FILES_URL` 和 `CONSOLE_API_URL` 都为空，文件预览将无法工作。
- **vital 3**：容器内部取文件用INTERNAL_FILES_URL，留空回退FILES_URL。
  - 必需组1（组内OR）：
    - [self-host/deploy/configuration/environments L99–99](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L99-L99) · `self-host/deploy/configuration/environments#c11` · `self-host/deploy/configuration/environments#p10`：默认值：（空；回退到 `FILES_URL`）
  - 必需组2（组内OR）：
    - [self-host/deploy/configuration/environments L101–101](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L101-L101) · `self-host/deploy/configuration/environments#c11` · `self-host/deploy/configuration/environments#p10`：Docker 网络内部服务间通信使用的文件访问 URL（例如插件守护进程、PDF/Word 提取器）。这些内部服务可能无法通过 Nginx 或公共域名访问外部的 `FILES_URL`。
  - 必需组3（组内OR）：
    - [self-host/deploy/configuration/environments L103–103](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L103-L103) · `self-host/deploy/configuration/environments#c11` · `self-host/deploy/configuration/environments#p10`：如果为空，内部服务使用 `FILES_URL`。当内部服务无法访问外部 URL 时，请设置此变量。
- **vital 4**：FILES_ACCESS_TIMEOUT规定签名链接的秒级有效期，过期需重新请求。
  - 必需组1（组内OR）：
    - [self-host/deploy/configuration/environments L111–111](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L111-L111) · `self-host/deploy/configuration/environments#c12` · `self-host/deploy/configuration/environments#p11`：签名文件 URL 的有效时长（秒）。超过此时间后 URL 将被拒绝，文件需要重新请求。对于长时间运行的流程可以增大此值；对于更严格的安全要求可以减小此值。

## dev063 · refuse_correct/out_of_database

官方对自部署跨机房灾备承诺的恢复点、恢复时间和切换期限各是多少？

参考答案：冻结资料没有给出自部署跨机房灾备的恢复点、恢复时间或故障切换期限承诺，不能报出具体数值；备份与迁移操作说明不等于这些保证。

失败风险：把备份操作建议编造成RPO/RTO或灾备SLA。

预期行为/路由：acknowledge_missing_evidence / None；小问数：1。

- 边界反证、可接受行为与不同解释见evidence.json该题。

## dev064 · refuse_correct/out_of_database

云版日本企业付款后，税务发票注册号与申请和开票期限怎样规定？

参考答案：资料只提到可查看账单、下载发票，没有日本税务发票注册号或申请、开票期限规定，无法给出这些参数；不能由资料不足推出不提供发票。

失败风险：从下载发票泛化出日本税号或税务期限。

预期行为/路由：acknowledge_missing_evidence / None；小问数：1。

- 边界反证、可接受行为与不同解释见evidence.json该题。

## dev065 · refuse_correct/false_premise

把含用户输入的全部节点复制到另一实例，让原空间资源原样继承，怎么做？

参考答案：不能按该前提操作。跨画布或实例复制不包含用户输入节点。粘贴会迁移节点配置，但变量等工作流资源、集成和知识库等工作空间资源会在目标重新评估，不能保证原样继承。

失败风险：顺着错误前提给迁移步骤，遗漏用户输入例外与资源重评估。

预期行为/路由：corrects_premise / None；小问数：1。

- 边界反证、可接受行为与不同解释见evidence.json该题。

## dev066 · clarify/version_unspecified

知识流水线的本地文件源一批能传多少份？

参考答案：需先确认部署方式及套餐：知识流水线文件源在Cloud的Sandbox为每批1个，Professional/Team最多50个；社区自部署默认每批20个。可据此条件回答，也可先询问。

失败风险：混用即用型上传的5个默认值，或未区分流水线两版的20与1/50。

预期行为/路由：clarify_or_conditional_answer / CLARIFY；小问数：1。

- 边界反证、可接受行为与不同解释见evidence.json该题。

## dev067 · clarify/missing_slot

想改应用显示给用户的那段文字，在哪里设置？

参考答案：你指应用着陆页/搜索结果里的介绍，还是聊天输入框的占位提示？前者改应用描述，后者改输入框提示语；输入框提示语适用于Chatbot、Agent与Chatflow，留空使用默认。

失败风险：未确认是应用介绍还是聊天框占位提示，就把两个文字入口混为同一配置。

预期行为/路由：clarify_or_conditional_answer / CLARIFY；小问数：1。

- 边界反证、可接受行为与不同解释见evidence.json该题。
