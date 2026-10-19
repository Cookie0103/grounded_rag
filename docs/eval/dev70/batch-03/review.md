# batch-03审阅稿

固定语料：langgenius/dify-docs @ c80a31868611b673bd77725a6310c685068a585e（CC BY 4.0）。新70为dev021～090，旧20独立回归。题目为交审草案，未运行完整系统、无检索基线或付费评分。原样单次检索的实际状态见validation.json和retrieval-selftest.jsonl。

等价来源组内OR、必要来源组间AND；现有正式评分加载器尚不保留gold_doc_groups。静态符合条件和候选召回不等于难度、答案效果或人工审核通过。

| ID | 行为 / 子类 | vital数 | 预期路由 | 题目 |
|---|---|---:|---|---|
| dev045 | 单跳 / 同义改写 | 4 | SINGLE | 怎样把调好的步骤打包并接上未选部分的取值？原组合再改会同步吗？ |
| dev046 | 单跳 / 同义改写 | 3 | SINGLE | 只找眼前画布里的步骤，键盘怎么用？组合键失灵还有何入口？ |
| dev047 | 单跳 / 同义改写 | 2 | SINGLE | 两人改同一元素谁的会留下？讨论留言会随修订消失吗？ |
| dev048 | 单跳 / 数值/表格 | 2 | SINGLE | 自建聊天接收录音，单个默认多大，调整上限用哪项配置？ |
| dev049 | 单跳 / 数值/表格 | 2 | SINGLE | 交接团队负责人时，验证码寄给谁，原负责人之后是什么角色？ |
| dev050 | 单跳 / 易混 | 3 | SINGLE | 需要可装程序改文件的沙箱助理，选哪类应用？固定能力和每次任务如何区分？ |
| dev051 | 单跳 / 易混 | 2 | SINGLE | 旧版工具助理为什么漏选资料，怎样改进选库判断？ |
| dev052 | 单跳 / 短问 | 2 | SINGLE | 恢复旧版后草稿怎样变化，如何更新线上？ |
| dev053 | 单跳 / 短问 | 1 | SINGLE | 单独跑前端时，两类域名不同用什么配置？ |
| dev054 | 单跳 / 单问版本 | 2 | SINGLE | 社区部署的空间何时创建，初始管理员凭据从哪来？ |
| dev055 | 多跳 / 链式 | 4 | MULTI | 云端报provider_not_initialize，原因与修复处是什么？谁能维护，移除唯一凭据后呢？ |
| dev056 | 多跳 / 链式 | 3 | MULTI | 自建库要模型生成结构化问答，用哪个内置方案？其材料产出顺序和适合文体呢？ |
| dev057 | 多跳 / 链式 | 4 | MULTI | 本地HTTP接Notion用哪种授权？该方式谁能建，凭据怎么配才生效？ |
| dev058 | 多跳 / 链式 | 4 | MULTI | 云端取消付费何时转免费档？此后知识库容量和超额旧资料的去留与检索呢？ |
| dev059 | 多跳 / 并列/比较 | 4 | MULTI | 旧版Agent和文本生成API的返回方式有何差别？两者流式正文各用什么事件？ |
| dev060 | 多跳 / 并列/比较 | 4 | MULTI | 聊天页如何隔开多主题记忆？任务页适合什么任务，跑CSV每行含义与编码呢？ |
| dev061 | 多跳 / 分散/有序 | 3 | MULTI | Windows源码调试：API前起哪些依赖，消费者需哪些兼容选项，定时服务怎么起？ |
| dev062 | 多跳 / 分散/有序 | 4 | MULTI | 自建流程外链预览、容器取文件及旧链接过期，分别查何配置，地址留空会怎样？ |
| dev063 | 拒答与纠正 / 库内缺依据 | 0 | null | 官方对自部署跨机房灾备承诺的恢复点、恢复时间和切换期限各是多少？ |
| dev064 | 拒答与纠正 / 库内缺依据 | 0 | null | 云版日本企业付款后，税务发票注册号与申请和开票期限怎样规定？ |
| dev065 | 拒答与纠正 / 错误前提 | 0 | null | 把含用户输入的全部节点复制到另一实例，让原空间资源原样继承，怎么做？ |
| dev066 | 模糊 / 版本不明 | 0 | CLARIFY | 知识流水线的本地文件源一批能传多少份？ |
| dev067 | 模糊 / 缺关键信息 | 0 | CLARIFY | 想让应用支持文件，在哪儿配置？ |

## dev045：怎样把调好的步骤打包并接上未选部分的取值？原组合再改会同步吗？

参考答案：选中调好的节点，右键创建Snippet。外部变量引用会成为它的输入；插入后要为各输入映射当前流程里的变量。插入的是副本，原组合后续改动不会同步到已使用的流程。

版本：未限定；预期行为：answered；最可能失败：把复用副本误作实时链接，或漏掉插入后的变量映射。。

1. **vital**：选中要复用的节点，右键选择创建Snippet。
   - [self-host/use-dify/build/snippet L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/snippet.mdx#L20-L20)；`self-host/use-dify/build/snippet#c1` / `self-host/use-dify/build/snippet#p1`。

     >     选中想要复用的节点，右键点击并选择 **创建 Snippet**。

2. **vital**：未选中节点的输出等外部变量引用会成为Snippet输入变量。
   - [self-host/use-dify/build/snippet L22–22](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/snippet.mdx#L22-L22)；`self-host/use-dify/build/snippet#c1` / `self-host/use-dify/build/snippet#p1`。

     >     这些节点的配置会一并保存到 Snippet 中。它们引用的外部变量（未选中节点的输出、环境变量等）会成为该 Snippet 的 [输入变量](#编辑-snippet)。

3. **vital**：插入后应为各输入变量映射当前流程的实际变量。
   - [self-host/use-dify/build/snippet L56–56](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/snippet.mdx#L56-L56)；`self-host/use-dify/build/snippet#c5` / `self-host/use-dify/build/snippet#p4`。

     > Snippet 会以副本形式添加到画布上。在插入的节点中，为每个输入变量指定工作流里对应的变量，让它们获取所需的数据。

4. **vital**：原始Snippet之后的修改不影响已插入它的流程。
   - [self-host/use-dify/build/snippet L58–58](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/snippet.mdx#L58-L58)；`self-host/use-dify/build/snippet#c5` / `self-host/use-dify/build/snippet#p4`。

     > 之后修改原始 Snippet 不会影响已经使用它的工作流，反之亦然。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 31,
    "vital_count": 4
  }
}
```

</details>


## dev046：只找眼前画布里的步骤，键盘怎么用？组合键失灵还有何入口？

参考答案：macOS按⌘+K，Windows/Linux按Ctrl+K，再用@node只查当前打开画布里的节点。组合键失效可点侧边栏顶部搜索按钮。

版本：未限定；预期行为：answered；最可能失败：搜到其他画布的同名步骤，或把组合键冲突误判为不可使用。。

1. **vital**：macOS用⌘+K，Windows/Linux用Ctrl+K打开入口。
   - [self-host/use-dify/build/goto-anything L12–12](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/goto-anything.mdx#L12-L12)；`self-host/use-dify/build/goto-anything#c1` / `self-host/use-dify/build/goto-anything#p1`。

     > 在 macOS 上按 `⌘ + K`，在 Windows/Linux 上按 `Ctrl + K`，或点击侧边栏顶部的搜索按钮。

2. **vital**：使用@node仅查当前打开画布的节点。
   - [self-host/use-dify/build/goto-anything L27–27](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/goto-anything.mdx#L27-L27)；`self-host/use-dify/build/goto-anything#c2` / `self-host/use-dify/build/goto-anything#p2`。

     > - `@node`：在当前打开的画布中搜索节点（工作流和知识流水线中可用）

3. **vital**：组合键失效时可点击侧边栏顶部按钮。
   - [self-host/use-dify/build/goto-anything L12–12](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/goto-anything.mdx#L12-L12)；`self-host/use-dify/build/goto-anything#c1` / `self-host/use-dify/build/goto-anything#p1`。

     > 在 macOS 上按 `⌘ + K`，在 Windows/Linux 上按 `Ctrl + K`，或点击侧边栏顶部的搜索按钮。

   - [self-host/use-dify/build/goto-anything L15–15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/goto-anything.mdx#L15-L15)；`self-host/use-dify/build/goto-anything#c1` / `self-host/use-dify/build/goto-anything#p1`。

     > 如果快捷键没有反应，可能是其他应用或浏览器扩展占用了它。侧边栏按钮始终可用。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 28,
    "vital_count": 3
  }
}
```

</details>


## dev047：两人改同一元素谁的会留下？讨论留言会随修订消失吗？

参考答案：同一元素的冲突以最后一次编辑为准；画布评论跨流程版本保留。

版本：未限定；预期行为：answered；最可能失败：假称锁定先编辑者，或说新版本会删评论。。

1. **vital**：同一元素发生编辑冲突时，以最后一次编辑为准。
   - [self-host/use-dify/build/workflow-collaboration L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/workflow-collaboration.mdx#L23-L23)；`self-host/use-dify/build/workflow-collaboration#c1` / `self-host/use-dify/build/workflow-collaboration#p1`。

     > 拥有编辑权限及以上的工作空间成员可同时编辑同一个工作流。当两位成员同时修改同一个元素时，以最后一次编辑为准。

2. **vital**：画布评论跨流程版本保留。
   - [self-host/use-dify/build/workflow-collaboration L27–27](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/workflow-collaboration.mdx#L27-L27)；`self-host/use-dify/build/workflow-collaboration#c2` / `self-host/use-dify/build/workflow-collaboration#p2`。

     > 右键点击画布的空白区域并选择 **添加评论** 留下一条评论。要连续添加多条评论，按 `C` 键进入评论模式。评论会跨工作流版本保留。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 25,
    "vital_count": 2
  }
}
```

</details>


## dev048：自建聊天接收录音，单个默认多大，调整上限用哪项配置？

参考答案：单个录音默认最多50 MB，配置项是UPLOAD_AUDIO_FILE_SIZE_LIMIT。

版本：self_host；预期行为：answered；最可能失败：把图片、普通文件或视频的大小限额套给音频。。

1. **vital**：单个音频文件上传默认上限为50 MB。
   - [self-host/use-dify/build/additional-features L80–80](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/additional-features.mdx#L80-L80)；`self-host/use-dify/build/additional-features#c5` / `self-host/use-dify/build/additional-features#p5`。

     > - `UPLOAD_AUDIO_FILE_SIZE_LIMIT`（默认值：50 MB）

2. **vital**：调整音频大小上限使用UPLOAD_AUDIO_FILE_SIZE_LIMIT。
   - [self-host/use-dify/build/additional-features L80–80](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/additional-features.mdx#L80-L80)；`self-host/use-dify/build/additional-features#c5` / `self-host/use-dify/build/additional-features#p5`。

     > - `UPLOAD_AUDIO_FILE_SIZE_LIMIT`（默认值：50 MB）

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 26,
    "vital_count": 2,
    "kind": "真实音频大小数值与配置查读"
  }
}
```

</details>


## dev049：交接团队负责人时，验证码寄给谁，原负责人之后是什么角色？

参考答案：验证码发到当前所有者的邮箱；交接完成后原所有者变为普通成员。

版本：未限定；预期行为：answered；最可能失败：把验证码发给接收者，或将原负责人保留为管理员。。

1. **vital**：转移所有权的验证码发送到当前所有者邮箱。
   等价来源（任一成立）：
   - [cloud/use-dify/workspace/team-members-management L47–47](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/team-members-management.mdx#L47-L47)；`cloud/use-dify/workspace/team-members-management#c4` / `cloud/use-dify/workspace/team-members-management#p4`。

     > **转移所有权**：只有所有者才能转移所有权。转移需通过发送至所有者邮箱的验证码确认。确认后，所选成员成为新的所有者，原所有者变更为普通成员。

   - [self-host/use-dify/workspace/team-members-management L50–50](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/team-members-management.mdx#L50-L50)；`self-host/use-dify/workspace/team-members-management#c3` / `self-host/use-dify/workspace/team-members-management#p3`。

     > **转移所有权**：只有所有者才能转移所有权。转移需通过发送至所有者邮箱的验证码确认。确认后，所选成员成为新的所有者，原所有者变更为普通成员。

2. **vital**：转移完成后，原所有者变为普通成员。
   等价来源（任一成立）：
   - [cloud/use-dify/workspace/team-members-management L47–47](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/team-members-management.mdx#L47-L47)；`cloud/use-dify/workspace/team-members-management#c4` / `cloud/use-dify/workspace/team-members-management#p4`。

     > **转移所有权**：只有所有者才能转移所有权。转移需通过发送至所有者邮箱的验证码确认。确认后，所选成员成为新的所有者，原所有者变更为普通成员。

   - [self-host/use-dify/workspace/team-members-management L50–50](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/team-members-management.mdx#L50-L50)；`self-host/use-dify/workspace/team-members-management#c3` / `self-host/use-dify/workspace/team-members-management#p3`。

     > **转移所有权**：只有所有者才能转移所有权。转移需通过发送至所有者邮箱的验证码确认。确认后，所选成员成为新的所有者，原所有者变更为普通成员。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "counterpart_docs": [
    "self-host/use-dify/workspace/team-members-management"
  ],
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 28,
    "vital_count": 2,
    "kind": "角色枚举/转移配置查读，没有答案数值，不冒称数值运算"
  }
}
```

</details>

备注：最终独立审题后主agent按冻结原文修正；具体发现、原版hash和闭环见semantic-review.json及blueprint-amendments.json。


## dev050：需要可装程序改文件的沙箱助理，选哪类应用？固定能力和每次任务如何区分？

参考答案：用新的Agent，它能在自己的沙箱运行命令、安装程序、读写文件。能力是预先配置的角色、模型、Skill、工具和文件等；任务是一次消息，或工作流给节点的指令。

版本：未限定；预期行为：answered；最可能失败：把仅调用已配工具的旧Agent当作独立沙箱，混淆能力与任务。。

1. **vital**：应使用在自有沙箱运行命令、安装程序和读写文件的新Agent。
   - [self-host/use-dify/build/new-agent/overview L25–25](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/overview.mdx#L25-L25)；`self-host/use-dify/build/new-agent/overview#c1` / `self-host/use-dify/build/new-agent/overview#p0`。

     > - 它在 **自己的沙箱** 中工作：可运行命令、安装程序、读写文件，因此能承担开放式的工作，而不只是调用你配置好的工具。

2. **vital**：能力是预先塑造的角色、模型、Skill、工具和文件等配置。
   - [self-host/use-dify/build/new-agent/overview L35–35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/overview.mdx#L35-L35)；`self-host/use-dify/build/new-agent/overview#c2` / `self-host/use-dify/build/new-agent/overview#p1`。

     > - **能力（可视为 Agent 的灵魂）决定了 Agent 是谁。**

   - [self-host/use-dify/build/new-agent/overview L37–37](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/overview.mdx#L37-L37)；`self-host/use-dify/build/new-agent/overview#c2` / `self-host/use-dify/build/new-agent/overview#p1`。

     >   包括你编写的角色和提示词、它运行的模型，以及你提供的 Skill、Dify 工具和文件。塑造一次后，可随着你逐渐摸清 Agent 需要什么而不断打磨。

3. **vital**：任务是单次运行的消息，或流程中给节点的指令。
   - [self-host/use-dify/build/new-agent/overview L39–39](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/overview.mdx#L39-L39)；`self-host/use-dify/build/new-agent/overview#c2` / `self-host/use-dify/build/new-agent/overview#p1`。

     > - **任务是你在一次运行中要它做的事。**

   - [self-host/use-dify/build/new-agent/overview L41–41](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/overview.mdx#L41-L41)；`self-host/use-dify/build/new-agent/overview#c2` / `self-host/use-dify/build/new-agent/overview#p1`。

     >   Agent 独立工作时，任务是你发给它的消息；在工作流中时，任务是你给节点的指令。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "distractor_docs": [
    "self-host/use-dify/build/agent"
  ],
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 35,
    "vital_count": 3
  }
}
```

</details>


## dev051：旧版工具助理为什么漏选资料，怎样改进选库判断？

参考答案：旧版Agent会评估每条用户查询与知识库描述的相关性，再决定是否检索；把知识库描述写详细，可以改善相关性判断。

版本：未限定；预期行为：answered；最可能失败：误套聊天助手每条消息都检索的机制，未说明知识库描述对相关性决策的作用。。

1. **vital**：旧版Agent按每条查询与知识库描述的相关性决定是否检索。
   - [self-host/use-dify/build/agent L130–130](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/agent.mdx#L130-L130)；`self-host/use-dify/build/agent#c7` / `self-host/use-dify/build/agent#p3`。

     > 模型会评估每条用户查询与知识库描述的相关性，并决定是否需要检索。你无需在提示词中提及知识库。

2. **vital**：写更详细的知识库描述能改善相关性判断。
   - [self-host/use-dify/build/agent L132–132](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/agent.mdx#L132-L132)；`self-host/use-dify/build/agent#c7` / `self-host/use-dify/build/agent#p3`。

     > **知识库描述越详细，模型判断相关性就越准确**，从而实现更精准的检索。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "distractor_docs": [
    "self-host/use-dify/build/chatbot"
  ],
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 23,
    "vital_count": 2
  }
}
```

</details>

备注：最终独立审题后主agent按冻结原文修正；具体发现、原版hash和闭环见semantic-review.json及blueprint-amendments.json。


## dev052：恢复旧版后草稿怎样变化，如何更新线上？

参考答案：旧版重新载入草稿并完全替换当前草稿；要上线还需点发布→发布更新。

版本：未限定；预期行为：answered；最可能失败：将恢复草稿等同于自动上线。。

1. **vital**：恢复旧版会把它载入草稿，完全替换当前草稿。
   - [self-host/use-dify/build/version-control L88–88](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/version-control.mdx#L88-L88)；`self-host/use-dify/build/version-control#c4` / `self-host/use-dify/build/version-control#p4`。

     > **恢复版本**：将旧版本重新加载到你的草稿中

   - [self-host/use-dify/build/version-control L95–95](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/version-control.mdx#L95-L95)；`self-host/use-dify/build/version-control#c4` / `self-host/use-dify/build/version-control#p4`。

     >   这将完全替换你当前的草稿。确保你没有未保存的工作。

2. **vital**：需点击发布→发布更新才使草稿上线。
   - [self-host/use-dify/build/version-control L36–36](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/version-control.mdx#L36-L36)；`self-host/use-dify/build/version-control#c2` / `self-host/use-dify/build/version-control#p2`。

     > 点击 **发布** → **发布更新** 以使你的草稿上线。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 19,
    "vital_count": 2
  }
}
```

</details>


## dev053：单独跑前端时，两类域名不同用什么配置？

参考答案：控制台域用CONSOLE_URL，Web应用域用APP_URL，可分别设置。前端可直接用Docker镜像运行。

版本：未限定；预期行为：answered；最可能失败：混淆CONSOLE_URL/APP_URL与后端API地址变量。。

1. **vital**：控制台域与Web应用域分别由CONSOLE_URL和APP_URL设置。
   - [self-host/deploy/advanced-deployments/start-the-frontend-docker-container L29–29](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/start-the-frontend-docker-container.mdx#L29-L29)；`self-host/deploy/advanced-deployments/start-the-frontend-docker-container#c1` / `self-host/deploy/advanced-deployments/start-the-frontend-docker-container#p0`。

     > 3. 当控制台域和 Web 应用域不同时，可以分别设置 CONSOLE_URL 和 APP_URL

2. **okay**：可直接拉取Docker镜像运行前端服务。
   - [self-host/deploy/advanced-deployments/start-the-frontend-docker-container L7–7](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/start-the-frontend-docker-container.mdx#L7-L7)；`self-host/deploy/advanced-deployments/start-the-frontend-docker-container#c0` / `self-host/deploy/advanced-deployments/start-the-frontend-docker-container#p0`。

     > 在单独开发后端时，你可能只需要从源代码启动后端服务，而无需在本地构建和启动前端。在这种情况下，你可以通过拉取 Docker 镜像并运行容器来直接启动前端服务。以下是具体步骤：

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 19,
    "vital_count": 1
  }
}
```

</details>


## dev054：社区部署的空间何时创建，初始管理员凭据从哪来？

参考答案：安装时创建工作空间；用初始化阶段设置的管理员邮箱和密码登录。

版本：self_host；预期行为：answered；最可能失败：套用Cloud首次登录创建规则。。

1. **vital**：社区部署在安装时创建工作空间。
   - [self-host/use-dify/workspace/readme L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/readme.mdx#L20-L20)；`self-host/use-dify/workspace/readme#c2` / `self-host/use-dify/workspace/readme#p2`。

     > 安装时会创建一个工作空间，使用你在初始化阶段设置的管理员邮箱和密码。

2. **vital**：使用初始化阶段设置的管理员邮箱和密码。
   - [self-host/use-dify/workspace/readme L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/readme.mdx#L20-L20)；`self-host/use-dify/workspace/readme#c2` / `self-host/use-dify/workspace/readme#p2`。

     > 安装时会创建一个工作空间，使用你在初始化阶段设置的管理员邮箱和密码。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "counterpart_docs": [
    "cloud/use-dify/workspace/readme"
  ],
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 23,
    "vital_count": 2
  }
}
```

</details>


## dev055：云端报provider_not_initialize，原因与修复处是什么？谁能维护，移除唯一凭据后呢？

参考答案：该错误表示应用模型没有有效凭据，需修复Dify中的应用模型配置。该处由工作空间所有者或管理员管理；若删掉某自定义模型唯一的密钥，该模型也会一并删除。

版本：cloud；预期行为：answered；最可能失败：反复原样重试，或忽略管理权限和唯一凭据删除后的模型生命周期。。

1. **vital**：provider_not_initialize表示应用模型没有有效凭据。
   - [api-reference/guides/errors L37–37](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/errors.mdx#L37-L37)；`api-reference/guides/errors#c2` / `api-reference/guides/errors#p2`。

     > - `provider_not_initialize`：没有有效的模型凭据

2. **vital**：应在Dify中修复应用的模型配置。
   - [api-reference/guides/errors L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/errors.mdx#L42-L42)；`api-reference/guides/errors#c2` / `api-reference/guides/errors#p2`。

     > 这些错误重试无济于事，需在 Dify 中修复应用的模型配置。

3. **vital**：只有工作空间所有者和管理员可以管理供应商。
   等价来源（任一成立）：
   - [cloud/use-dify/workspace/model-providers L13–13](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/model-providers.mdx#L13-L13)；`cloud/use-dify/workspace/model-providers#c0` / `cloud/use-dify/workspace/model-providers#p0`。

     > 只有工作空间所有者和管理员可以管理供应商。你添加的任何密钥都在整个工作空间内生效，并通过你自己的供应商账户计费。

   - [self-host/use-dify/workspace/model-providers L11–11](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/model-providers.mdx#L11-L11)；`self-host/use-dify/workspace/model-providers#c0` / `self-host/use-dify/workspace/model-providers#p0`。

     > API 密钥授予工作空间范围的模型访问权限，并会通过各供应商的账户直接计费。只有工作空间所有者和管理员可以管理供应商。

4. **vital**：删除自定义模型唯一的密钥时，该模型也会被删除。
   等价来源（任一成立）：
   - [cloud/use-dify/workspace/model-providers L73–73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/model-providers.mdx#L73-L73)；`cloud/use-dify/workspace/model-providers#c5` / `cloud/use-dify/workspace/model-providers#p5`。

     >     自定义模型依赖于自己的密钥。删除它唯一的密钥时，该模型也会一并删除。

   - [self-host/use-dify/workspace/model-providers L54–54](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/model-providers.mdx#L54-L54)；`self-host/use-dify/workspace/model-providers#c3` / `self-host/use-dify/workspace/model-providers#p3`。

     >     你添加的模型依赖于自己的凭据。删除它唯一的凭据时，该模型也会一并删除。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 51,
    "vital_count": 4
  },
  "chain": {
    "bridge_type": "诊断标识→配置修复→凭据生命周期",
    "bridge_explanation": "第一篇从400中的稳定code定位为应用模型配置，排除原样重试；第二问用“该处/该条目”指代第一步定位出的模型供应商，不直接给模型供应商标题。",
    "second_document_answer_keywords": [
      "所有者",
      "管理员",
      "工作空间",
      "API 密钥",
      "自定义模型",
      "删除"
    ],
    "generic_distractor_documents": [
      "self-host/use-dify/workspace/plugins",
      "self-host/use-dify/workspace/tools"
    ],
    "semantic_status": "blueprint_independent_review_accepted_formal_question_pending_review",
    "first_document": "api-reference/guides/errors",
    "second_document": "cloud/use-dify/workspace/model-providers",
    "dependency": "第一篇从400中的稳定code定位为应用模型配置，排除原样重试；第二问用“该处/该条目”指代第一步定位出的模型供应商，不直接给模型供应商标题。",
    "generic_distractor_proof": [
      {
        "source": {
          "document_id": "self-host/use-dify/workspace/plugins",
          "heading_path": "集成 > 权限与更新",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/plugins.mdx#L52-L52",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/plugins.mdx",
          "raw_line_start": 52,
          "raw_line_end": 52,
          "original_excerpt": "工作空间所有者和管理员可在 **集成** 页面底部的 **权限** 中，设置谁能安装和调试集成。每项权限都可以设为所有人可用、仅管理员可用或无人可用：",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/workspace/plugins#c3",
            "excerpt": "工作空间所有者和管理员可在 **集成** 页面底部的 **权限** 中，设置谁能安装和调试集成。每项权限都可以设为所有人可用、仅管理员可用或无人可用：",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/workspace/plugins#p3",
            "heading_path": "集成 > 权限与更新",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 847,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "073d4635e172c995380f0c3646ef2c8baee30269bfafbc146c95b5a6f6a7f8f8",
          "reconstruct_verified": true
        },
        "why_not_sufficient": "同样讲所有者、管理员、权限和调试密钥，但不回答自定义模型删除唯一凭据的生命周期。"
      },
      {
        "source": {
          "document_id": "self-host/use-dify/workspace/tools",
          "heading_path": "Dify 工具 > 工具类型",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/tools.mdx#L25-L25",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/tools.mdx",
          "raw_line_start": 25,
          "raw_line_end": 25,
          "original_excerpt": "        部分工具插件（如 Google 和 GitHub）使用前需要鉴权。可在 **集成** > **工具** > **工具插件** 中设置工作空间级凭据，或在应用或节点内的工具设置中配置。",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/workspace/tools#c1",
            "excerpt": "部分工具插件（如 Google 和 GitHub）使用前需要鉴权。可在 **集成** > **工具** > **工具插件** 中设置工作空间级凭据，或在应用或节点内的工具设置中配置。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/workspace/tools#p1",
            "heading_path": "Dify 工具 > 工具类型",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 268,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "3945b8c8f985cc1463a3e1976272fcdb8fd56d569d934e9aff09ce674b206fc8",
          "reconstruct_verified": true
        },
        "why_not_sufficient": "同样讲工作空间凭据和工具鉴权，但不提供模型错误code或模型唯一凭据删除结果。"
      }
    ]
  }
}
```

</details>


## dev056：自建库要模型生成结构化问答，用哪个内置方案？其材料产出顺序和适合文体呢？

参考答案：选LLM生成问答模板，产出问答模式。其处理先将上传文本分段，总结内容后为每段生成Q&A匹配对；具有完整语法结构的自然语言常见问题文档更适合该方法。

版本：未限定；预期行为：answered；最可能失败：选Simple Q&A而非LLM生成问答，或只解释QtoQ不回答处理顺序与文体。。

1. **vital**：选择LLM生成问答模板，其分段结构为问答模式。
   等价来源（任一成立）：
   - [self-host/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline L44–44](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline.mdx#L44-L44)；`self-host/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline#c5` / `self-host/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline#p2`。

     > | LLM 生成问答（LLM Generated Q&A) | 问答模式 | 高质量 | 向量搜索 - 加权评分 | 使用大型语言模型自动生成结构化的问答对，通过问题匹配机制找到相关的答案信息。 |

   - [cloud/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline L44–44](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline.mdx#L44-L44)；`cloud/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline#c5` / `cloud/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline#p2`。

     > | LLM 生成问答（LLM Generated Q&A) | 问答模式 | 高质量 | 向量搜索 - 加权评分 | 使用大型语言模型自动生成结构化的问答对，通过问题匹配机制找到相关的答案信息。 |

2. **vital**：该模式先将上传文本分段，总结内容后为每段生成Q&A匹配对。
   - [self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods.mdx#L42-L42)；`self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#c3` / `self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#p2`。

     >     开启该模式后，系统将对已上传的文本进行分段。总结内容后为每个分段自动生成 Q&A 匹配对。

3. **vital**：具备完整语法结构的自然语言常见问题文档更适合该方法。
   - [self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods L44–44](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods.mdx#L44-L44)；`self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#c3` / `self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#p2`。

     >     与常见的 「Q to P」（用户问题匹配文本段落）策略不同，Q&A 模式采用 「Q to Q」（问题匹配问题）策略。

   - [self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods L46–46](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods.mdx#L46-L46)；`self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#c3` / `self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods#p2`。

     >     这种方法特别有效，因为常见问题文档中的文本 **通常是具备完整语法结构的自然语言**。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 36,
    "vital_count": 3
  },
  "chain": {
    "bridge_type": "LLM生成模板→问答模式→生成顺序与自然语言前提",
    "bridge_explanation": "首篇由自动生成结构化问答需求定位LLM生成问答模板及问答模式；第二篇独有先分段、总结后生成配对的处理顺序及完整语法结构自然语言的适合性。明确不把SimpleQ&A表格直接转换流程混同自动生成。",
    "second_document_answer_keywords": [
      "分段",
      "总结内容",
      "自动生成",
      "Q&A 匹配对",
      "完整语法结构",
      "自然语言"
    ],
    "generic_distractor_documents": [
      "self-host/use-dify/knowledge/test-retrieval",
      "self-host/use-dify/build/chatbot"
    ],
    "semantic_status": "blueprint_independent_review_accepted_formal_question_pending_review",
    "first_document": "self-host/use-dify/knowledge/knowledge-pipeline/create-knowledge-pipeline",
    "second_document": "self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods",
    "dependency": "首篇由自动生成结构化问答需求定位LLM生成问答模板及问答模式；第二篇独有先分段、总结后生成配对的处理顺序及完整语法结构自然语言的适合性。明确不把SimpleQ&A表格直接转换流程混同自动生成。",
    "generic_distractor_proof": [
      {
        "source": {
          "document_id": "self-host/use-dify/knowledge/test-retrieval",
          "heading_path": "测试检索",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/test-retrieval.mdx#L8-L8",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/test-retrieval.mdx",
          "raw_line_start": 8,
          "raw_line_end": 8,
          "original_excerpt": "在知识库中，点击左侧边栏的 **检索测试** 图标，进入测试页面。在这里，可模拟用户提问以测试知识库的检索效果，并尝试不同的检索设置以获得最佳结果。",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/knowledge/test-retrieval#c0",
            "excerpt": "在知识库中，点击左侧边栏的 **检索测试** 图标，进入测试页面。在这里，可模拟用户提问以测试知识库的检索效果，并尝试不同的检索设置以获得最佳结果。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/knowledge/test-retrieval#p0",
            "heading_path": "测试检索",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 0,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "987a63027cb67d9ae3eb91c331351a92c5933e793c2ae2d4e2d48674d5b41a02",
          "reconstruct_verified": true
        },
        "why_not_sufficient": "同样讲知识库/检索设置及测试，不给LLM生成模板与问答模式映射或生成顺序/文体条件。"
      },
      {
        "source": {
          "document_id": "self-host/use-dify/build/chatbot",
          "heading_path": "聊天助手 > 配置 > 基于你的数据生成回复",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/chatbot.mdx#L92-L92",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/chatbot.mdx",
          "raw_line_start": 92,
          "raw_line_end": 92,
          "original_excerpt": "每当用户发送消息时，该消息会作为搜索查询从知识库中检索相关内容，然后作为上下文注入提示词供模型使用。",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/build/chatbot#c5",
            "excerpt": "每当用户发送消息时，该消息会作为搜索查询从知识库中检索相关内容，然后作为上下文注入提示词供模型使用。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/build/chatbot#p2",
            "heading_path": "聊天助手 > 配置 > 基于你的数据生成回复",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 1334,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "7e17eeff2c9b05c9bc0274034c1e2c3b5780aaea3ab7a7bb705933b02fe07cf2",
          "reconstruct_verified": true
        },
        "why_not_sufficient": "同样讲问题作为查询与检索上下文，不给材料生成顺序和完整自然语言适用条件。"
      }
    ]
  }
}
```

</details>


## dev057：本地HTTP接Notion用哪种授权？该方式谁能建，凭据怎么配才生效？

参考答案：Notion OAuth只支持HTTPS，本地HTTP部署使用内部集成。由Notion工作空间所有者创建。在Dify的.env设NOTION_INTEGRATION_TYPE=internal及NOTION_INTERNAL_SECRET为内部密钥，再重启Dify加载设置。

版本：未限定；预期行为：answered；最可能失败：误用公开OAuth，混淆Notion所有者与Dify管理员。。

1. **vital**：Notion OAuth只支持HTTPS，本地HTTP部署须用内部集成。
   - [self-host/deploy/troubleshooting/integrations L9–9](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/integrations.mdx#L9-L9)；`self-host/deploy/troubleshooting/integrations#c0` / `self-host/deploy/troubleshooting/integrations#p0`。

     > Notion OAuth 仅支持 HTTPS，因此本地部署必须使用内部集成。

2. **vital**：创建内部集成需要是Notion工作空间所有者。
   - [self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion L56–56](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion.mdx#L56-L56)；`self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#c5` / `self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#p5`。

     > 在 Notion 的[集成设置页面](https://www.notion.so/my-integrations)创建集成。默认情况下，所有集成都以内部集成开始，并与你选择的 Notion 工作空间相关联，因此你需要是工作空间所有者才能创建集成。

3. **vital**：在.env设置NOTION_INTEGRATION_TYPE=internal和NOTION_INTERNAL_SECRET为内部密钥。
   - [self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion L70–70](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion.mdx#L70-L70)；`self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#c6` / `self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#p5`。

     > 在 Dify 部署的 `.env` 文件中配置以下环境变量：

   - [self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion L73–74](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion.mdx#L73-L74)；`self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#c6` / `self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#p5`。

     > NOTION_INTEGRATION_TYPE=internal
     > NOTION_INTERNAL_SECRET=your-internal-secret

4. **vital**：需重启Dify加载新的环境变量。
   - [self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion L99–99](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion.mdx#L99-L99)；`self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#c7` / `self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion#p5`。

     > 重启 Dify 以加载新的环境变量。之后即可按上述步骤授权 Notion 并导入数据。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 35,
    "vital_count": 4
  },
  "chain": {
    "bridge_type": "部署协议条件→可用授权模式→对应权限与凭据流程",
    "bridge_explanation": "第二篇同时介绍内部和公开集成，创建权限、取密钥位置和环境变量都随模式不同；必须先用第一篇的HTTPS限制选分支，不能仅靠Notion这个名字跳页。",
    "second_document_answer_keywords": [
      "内部集成",
      "工作空间所有者",
      ".env",
      "NOTION_INTEGRATION_TYPE",
      "NOTION_INTERNAL_SECRET",
      "重启 Dify"
    ],
    "generic_distractor_documents": [
      "cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source",
      "self-host/use-dify/workspace/api-extension/api-extension"
    ],
    "semantic_status": "blueprint_independent_review_accepted_formal_question_pending_review",
    "first_document": "self-host/deploy/troubleshooting/integrations",
    "second_document": "self-host/use-dify/knowledge/create-knowledge/import-text-data/sync-from-notion",
    "dependency": "第二篇同时介绍内部和公开集成，创建权限、取密钥位置和环境变量都随模式不同；必须先用第一篇的HTTPS限制选分支，不能仅靠Notion这个名字跳页。",
    "generic_distractor_proof": [
      {
        "source": {
          "document_id": "cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source",
          "heading_path": "数据源授权",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx#L7-L7",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source.mdx",
          "raw_line_start": 7,
          "raw_line_end": 7,
          "original_excerpt": "Dify 支持多种外部数据源的连接，为了确保数据安全和访问控制，不同的数据源需要进行相应的授权配置。根据数据源的特性，Dify 提供两种主要的授权方式：**API Key** 和 **OAuth**，以确保你能够安全地访问和导入所需的数据。",
          "direct_evidence": {
            "chunk_id": "cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source#c0",
            "excerpt": "Dify 支持多种外部数据源的连接，为了确保数据安全和访问控制，不同的数据源需要进行相应的授权配置。根据数据源的特性，Dify 提供两种主要的授权方式：**API Key** 和 **OAuth**，以确保你能够安全地访问和导入所需的数据。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "cloud/use-dify/knowledge/knowledge-pipeline/authorize-data-source#p0",
            "heading_path": "数据源授权",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 0,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "63c4a5deaef95073f7fc2fc09a6d37d17e543acd0c345394ee5343d19e6bbf0a",
          "reconstruct_verified": true
        },
        "why_not_sufficient": "同样讲授权凭据与OAuth，但不决定HTTP下Notion内部模式及Notion工作空间所有者权限。"
      },
      {
        "source": {
          "document_id": "self-host/use-dify/workspace/api-extension/api-extension",
          "heading_path": "自定义端点",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/api-extension/api-extension.mdx#L13-L13",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/api-extension/api-extension.mdx",
          "raw_line_start": 13,
          "raw_line_end": 13,
          "original_excerpt": "在扩展模块能力之前，你需要准备一个 API 和用于鉴权的 API Key。",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/workspace/api-extension/api-extension#c0",
            "excerpt": "在扩展模块能力之前，你需要准备一个 API 和用于鉴权的 API Key。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/workspace/api-extension/api-extension#p0",
            "heading_path": "自定义端点",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 84,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "aa03496f560e172c5397b018c44e26fac00cd33c5fbb1fe1bf75eecef080da43",
          "reconstruct_verified": true
        },
        "why_not_sufficient": "同样讲API和鉴权密钥，不给Notion内部授权模式/创建权限和NOTION变量。"
      }
    ]
  }
}
```

</details>


## dev058：云端取消付费何时转免费档？此后知识库容量和超额旧资料的去留与检索呢？

参考答案：已付费周期结束后才恢复Sandbox；其知识库存储容量为50 MB。已有资料即使超额也不会被删除，应用仍可检索。

版本：cloud；预期行为：answered；最可能失败：把取消视为立即降级，或把50 MB当单文件上限并误称旧数据被删。。

1. **vital**：取消后保留当前计划直到已付费周期结束，随后恢复Sandbox。
   - [cloud/use-dify/workspace/subscription-management L22–22](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/subscription-management.mdx#L22-L22)；`cloud/use-dify/workspace/subscription-management#c1` / `cloud/use-dify/workspace/subscription-management#p1`。

     > - **取消或更新付款方式**：点击 **管理**（Manage）打开 Stripe 计费门户，在其中取消订阅或更改付款方式。取消后，工作空间会保留当前计划直到已付费周期结束，随后恢复为免费的 Sandbox 计划。

2. **vital**：Sandbox的知识库存储容量为50 MB。
   - [cloud/use-dify/knowledge/knowledge-storage-limit L15–15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L15-L15)；`cloud/use-dify/knowledge/knowledge-storage-limit#c0` / `cloud/use-dify/knowledge/knowledge-storage-limit#p0`。

     > | Sandbox | 50 MB |

3. **vital**：降级造成已有数据超过新限额时，数据不会被删除。
   - [cloud/use-dify/knowledge/knowledge-storage-limit L53–53](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L53-L53)；`cloud/use-dify/knowledge/knowledge-storage-limit#c3` / `cloud/use-dify/knowledge/knowledge-storage-limit#p3`。

     > 如果套餐降级或订阅到期导致现有数据超出新套餐的上限，数据不会被删除：应用仍可正常检索这些知识库，但在用量降到限额以内或重新升级前，无法再新增内容。

4. **vital**：降级造成已有数据超额时，应用仍能正常检索。
   - [cloud/use-dify/knowledge/knowledge-storage-limit L53–53](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-storage-limit.mdx#L53-L53)；`cloud/use-dify/knowledge/knowledge-storage-limit#c3` / `cloud/use-dify/knowledge/knowledge-storage-limit#p3`。

     > 如果套餐降级或订阅到期导致现有数据超出新套餐的上限，数据不会被删除：应用仍可正常检索这些知识库，但在用量降到限额以内或重新升级前，无法再新增内容。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 34,
    "vital_count": 4
  },
  "chain": {
    "bridge_type": "订阅状态变更→套餐实体→额度及超额旧数据行为",
    "bridge_explanation": "第二篇列多种套餐额度，必须先从第一篇把取消付费后的计划解析成Sandbox，才能选中50 MB；同一篇再给出降级后超额旧数据的处理。不是从A跳转到某页面即宣称链式。",
    "second_document_answer_keywords": [
      "50 MB",
      "现有数据",
      "新套餐的上限",
      "不会被删除",
      "正常检索"
    ],
    "generic_distractor_documents": [
      "cloud/use-dify/knowledge/knowledge-request-rate-limit",
      "self-host/use-dify/knowledge/readme"
    ],
    "semantic_status": "blueprint_independent_review_accepted_formal_question_pending_review",
    "first_document": "cloud/use-dify/workspace/subscription-management",
    "second_document": "cloud/use-dify/knowledge/knowledge-storage-limit",
    "dependency": "第二篇列多种套餐额度，必须先从第一篇把取消付费后的计划解析成Sandbox，才能选中50 MB；同一篇再给出降级后超额旧数据的处理。不是从A跳转到某页面即宣称链式。",
    "generic_distractor_proof": [
      {
        "source": {
          "document_id": "cloud/use-dify/knowledge/knowledge-request-rate-limit",
          "heading_path": "知识库请求频率限制 > 不同订阅版本的限制",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-request-rate-limit.mdx#L14-L14",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-request-rate-limit.mdx",
          "raw_line_start": 14,
          "raw_line_end": 14,
          "original_excerpt": "-   **Sandbox**：10 次/分钟",
          "direct_evidence": {
            "chunk_id": "cloud/use-dify/knowledge/knowledge-request-rate-limit#c1",
            "excerpt": "-   **Sandbox**：10 次/分钟",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "cloud/use-dify/knowledge/knowledge-request-rate-limit#p1",
            "heading_path": "知识库请求频率限制 > 不同订阅版本的限制",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 102,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "5e7b0e826cf599cb2dcc6da33d0b1eb5a488d288546dab3922aaf931602894e2",
          "reconstruct_verified": true
        },
        "why_not_sufficient": "同样讲套餐/知识库限制，但给请求频率，不给存储容量或取消后超额数据保留。"
      },
      {
        "source": {
          "document_id": "self-host/use-dify/knowledge/readme",
          "heading_path": "知识库 > 简介",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/readme.mdx#L12-L12",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/knowledge/readme.mdx",
          "raw_line_start": 12,
          "raw_line_end": 12,
          "original_excerpt": "这得益于检索增强生成（RAG）技术。其核心在于：LLM 不再只依赖预训练的公开数据，还会将你的自定义知识作为额外的事实来源：",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/knowledge/readme#c0",
            "excerpt": "这得益于检索增强生成（RAG）技术。其核心在于：LLM 不再只依赖预训练的公开数据，还会将你的自定义知识作为额外的事实来源：",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/knowledge/readme#p0",
            "heading_path": "知识库 > 简介",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 98,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "b398f3583244febbdfec6615fea9977b4efe8583df1a065b045e0d30dc234987",
          "reconstruct_verified": true
        },
        "why_not_sufficient": "同样讲知识库、内容、检索和建库路线，不提供Cloud订阅转Sandbox的容量与超额处理。"
      }
    ]
  }
}
```

</details>


## dev059：旧版Agent和文本生成API的返回方式有何差别？两者流式正文各用什么事件？

参考答案：旧版Agent仅支持流式，回复正文由agent_message事件承载（另有agent_thought思考事件）；文本生成可阻塞也可流式，流式正文使用message事件。只要求比较返回方式与正文事件，不考会话记忆。

版本：未限定；预期行为：answered；最可能失败：混用Agent的agent_message与普通message事件，或错误承诺旧版Agent支持阻塞返回。。

1. **vital**：旧版Agent应用仅支持流式返回。
   - [api-reference/guides/chat L17–17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/chat.mdx#L17-L17)；`api-reference/guides/chat#c1` / `api-reference/guides/chat#p1`。

     > 旧版 Agent 应用仅支持流式返回。

2. **vital**：文本生成API支持阻塞式返回，也支持流式返回。
   - [api-reference/guides/completion L17–17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/completion.mdx#L17-L17)；`api-reference/guides/completion#c1` / `api-reference/guides/completion#p1`。

     > 阻塞式返回在生成完成后一次性返回全部内容；流式返回持续输出 `message` 事件，直至 `message_end`（应用开启文字转语音自动播放时还会收到 `tts_message` 事件）。

3. **vital**：旧版Agent流式正文使用agent_message事件。
   - [api-reference/guides/chat L9–9](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/chat.mdx#L9-L9)；`api-reference/guides/chat#c0` / `api-reference/guides/chat#p0`。

     > 聊天助手应用以 `message` 事件流式返回回复，旧版 Agent 应用则返回 `agent_thought` 和 `agent_message` 事件。

4. **vital**：文本生成API流式正文使用message事件。
   - [api-reference/guides/completion L17–17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/completion.mdx#L17-L17)；`api-reference/guides/completion#c1` / `api-reference/guides/completion#p1`。

     > 流式返回持续输出 `message` 事件，直至 `message_end`（应用开启文字转语音自动播放时还会收到 `tts_message` 事件）。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 38,
    "vital_count": 4
  }
}
```

</details>

备注：最终独立审题后主agent按冻结原文修正；具体发现、原版hash和闭环见semantic-review.json及blueprint-amendments.json。


## dev060：聊天页如何隔开多主题记忆？任务页适合什么任务，跑CSV每行含义与编码呢？

参考答案：聊天网页按各对话线程分别维护记忆和上下文。Workflow任务页适合产出特定结果的离散任务；批处理CSV每一行执行一次，文件须用Unicode UTF-8编码。

版本：未限定；预期行为：answered；最可能失败：将CSV整批当一次执行，或把聊天线程的记忆套给离散任务。。

1. **vital**：聊天Web应用各对话线程维护各自记忆和上下文。
   - [self-host/use-dify/publish/webapp/chatflow-webapp L103–103](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/webapp/chatflow-webapp.mdx#L103-L103)；`self-host/use-dify/publish/webapp/chatflow-webapp#c5` / `self-host/use-dify/publish/webapp/chatflow-webapp#p5`。

     > 每个对话线程都维护自己的记忆和上下文。用户可以在不同主题或项目间无缝切换。

2. **vital**：Workflow网页用于产生特定输出的离散任务。
   - [self-host/use-dify/publish/webapp/workflow-webapp L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/webapp/workflow-webapp.mdx#L20-L20)；`self-host/use-dify/publish/webapp/workflow-webapp#c1` / `self-host/use-dify/publish/webapp/workflow-webapp#p1`。

     > 与维护对话上下文的聊天应用不同，Workflow 应用设计用于产生特定输出的离散任务。

3. **vital**：批处理CSV的每一行都是一次Workflow执行。
   - [self-host/use-dify/publish/webapp/workflow-webapp L88–88](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/webapp/workflow-webapp.mdx#L88-L88)；`self-host/use-dify/publish/webapp/workflow-webapp#c4` / `self-host/use-dify/publish/webapp/workflow-webapp#p4`。

     >     在模板中填入你的输入数据。每一行都会成为一次工作流执行。

4. **vital**：从Excel导出导入用CSV时应选Unicode UTF-8编码。
   - [self-host/use-dify/publish/webapp/workflow-webapp L108–108](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/webapp/workflow-webapp.mdx#L108-L108)；`self-host/use-dify/publish/webapp/workflow-webapp#c5` / `self-host/use-dify/publish/webapp/workflow-webapp#p5`。

     > CSV 文件必须使用 Unicode 编码以防止导入失败。从 Excel 或类似工具保存时，请明确选择「Unicode (UTF-8)」编码。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 36,
    "vital_count": 4
  }
}
```

</details>


## dev061：Windows源码调试：API前起哪些依赖，消费者需哪些兼容选项，定时服务怎么起？

参考答案：先用middleware配置启动数据库、沙箱和插件守护进程，可执行docker compose --env-file middleware.env -f docker-compose.middleware.yaml -p dify up -d。Windows的Celery Worker需-P solo --without-gossip --without-mingle兼容选项；定时服务另开终端运行uv run celery -A app.celery beat。文档完整Worker命令中的队列清单不是本题必答项。

版本：self_host；预期行为：answered；最可能失败：Windows误用默认进程池，或遗漏定时任务独立beat服务。。

1. **vital**：启动API前，用middleware配置启动数据库、沙箱和插件守护进程。
   - [self-host/deploy/advanced-deployments/local-source-code L33–33](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L33-L33)；`self-host/deploy/advanced-deployments/local-source-code#c5` / `self-host/deploy/advanced-deployments/local-source-code#p2`。

     > 启动后端前，先用 Docker Compose 启动数据库、[沙箱](https://github.com/langgenius/dify-sandbox)和[插件守护进程](https://github.com/langgenius/dify-plugin-daemon)。

   - [self-host/deploy/advanced-deployments/local-source-code L41–41](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L41-L41)；`self-host/deploy/advanced-deployments/local-source-code#c5` / `self-host/deploy/advanced-deployments/local-source-code#p2`。

     > docker compose --env-file middleware.env -f docker-compose.middleware.yaml -p dify up -d

2. **vital**：Windows的Celery Worker命令使用-P solo --without-gossip --without-mingle。
   - [self-host/deploy/advanced-deployments/local-source-code L124–124](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L124-L124)；`self-host/deploy/advanced-deployments/local-source-code#c10` / `self-host/deploy/advanced-deployments/local-source-code#p5`。

     >     如果你使用 Windows 系统启动 Worker 服务，请使用以下命令：

   - [self-host/deploy/advanced-deployments/local-source-code L128–128](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L128-L128)；`self-host/deploy/advanced-deployments/local-source-code#c11` / `self-host/deploy/advanced-deployments/local-source-code#p5`。

     >     uv run celery -A app.celery worker -P solo --without-gossip --without-mingle --loglevel INFO -Q dataset,dataset_summary,priority_dataset,priority_pipeline,pipeline,mail,ops_trace,app_deletion,plugin,workflow_storage,conversation,workflow,schedule_poller,schedule_executor,triggered_workflow_dispatcher,trigger_refresh_executor,retention,workflow_based_app_execution

3. **vital**：定时任务需另起uv run celery -A app.celery beat服务。
   - [self-host/deploy/advanced-deployments/local-source-code L201–201](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L201-L201)；`self-host/deploy/advanced-deployments/local-source-code#c16` / `self-host/deploy/advanced-deployments/local-source-code#p7`。

     > 如需调试 celery 定时任务或运行定时触发器节点，可以在另一个终端中运行以下命令启动 beat 服务：

   - [self-host/deploy/advanced-deployments/local-source-code L204–204](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/advanced-deployments/local-source-code.mdx#L204-L204)；`self-host/deploy/advanced-deployments/local-source-code#c16` / `self-host/deploy/advanced-deployments/local-source-code#p7`。

     > uv run celery -A app.celery beat

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 41,
    "vital_count": 3
  },
  "quantitative_evidence": {
    "cleaned_characters": 9408,
    "required_parent_ids": [
      "self-host/deploy/advanced-deployments/local-source-code#p2",
      "self-host/deploy/advanced-deployments/local-source-code#p5",
      "self-host/deploy/advanced-deployments/local-source-code#p7"
    ],
    "raw_excerpt_prefix_limit": 12000,
    "question_characters": 41,
    "at_most_40": false,
    "at_most_80": true,
    "vital_count": 3
  }
}
```

</details>

备注：最终独立审题后主agent按冻结原文修正；具体发现、原版hash和闭环见semantic-review.json及blueprint-amendments.json。


## dev062：自建流程外链预览、容器取文件及旧链接过期，分别查何配置，地址留空会怎样？

参考答案：外链预览/下载用FILES_URL，留空回退CONSOLE_API_URL；两者都空则无法预览。容器内取文件用INTERNAL_FILES_URL，留空用FILES_URL，内部无法访问外部地址时应单独配置。签名链接时效由FILES_ACCESS_TIMEOUT按秒控制，过期需重新请求。

版本：self_host；预期行为：answered；最可能失败：只设置公网地址，或将签名过期误作文件已被删除。。

1. **vital**：FILES_URL是预览和下载基础URL，留空回退CONSOLE_API_URL。
   - [self-host/deploy/configuration/environments L89–89](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L89-L89)；`self-host/deploy/configuration/environments#c10` / `self-host/deploy/configuration/environments#p9`。

     > 默认值：（空；回退到 `CONSOLE_API_URL`）

   - [self-host/deploy/configuration/environments L91–91](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L91-L91)；`self-host/deploy/configuration/environments#c10` / `self-host/deploy/configuration/environments#p9`。

     > 文件预览和下载链接的基础 URL。Dify 为所有文件（上传的文档、工具输出、工作空间 Logo）生成签名的限时 URL，并提供给前端和多模态模型使用。

2. **vital**：FILES_URL与CONSOLE_API_URL都为空时，文件预览无法工作。
   - [self-host/deploy/configuration/environments L93–93](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L93-L93)；`self-host/deploy/configuration/environments#c10` / `self-host/deploy/configuration/environments#p9`。

     > 如果你使用文件处理插件，或希望文件 URL 使用专用域名，请设置此变量。如果 `FILES_URL` 和 `CONSOLE_API_URL` 都为空，文件预览将无法工作。

3. **vital**：容器内部取文件用INTERNAL_FILES_URL，留空回退FILES_URL。
   - [self-host/deploy/configuration/environments L99–99](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L99-L99)；`self-host/deploy/configuration/environments#c11` / `self-host/deploy/configuration/environments#p10`。

     > 默认值：（空；回退到 `FILES_URL`）

   - [self-host/deploy/configuration/environments L101–101](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L101-L101)；`self-host/deploy/configuration/environments#c11` / `self-host/deploy/configuration/environments#p10`。

     > Docker 网络内部服务间通信使用的文件访问 URL（例如插件守护进程、PDF/Word 提取器）。这些内部服务可能无法通过 Nginx 或公共域名访问外部的 `FILES_URL`。

   - [self-host/deploy/configuration/environments L103–103](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L103-L103)；`self-host/deploy/configuration/environments#c11` / `self-host/deploy/configuration/environments#p10`。

     > 如果为空，内部服务使用 `FILES_URL`。当内部服务无法访问外部 URL 时，请设置此变量。

4. **vital**：FILES_ACCESS_TIMEOUT规定签名链接的秒级有效期，过期需重新请求。
   - [self-host/deploy/configuration/environments L111–111](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/configuration/environments.mdx#L111-L111)；`self-host/deploy/configuration/environments#c12` / `self-host/deploy/configuration/environments#p11`。

     > 签名文件 URL 的有效时长（秒）。超过此时间后 URL 将被拒绝，文件需要重新请求。对于长时间运行的流程可以增大此值；对于更严格的安全要求可以减小此值。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 36,
    "vital_count": 4
  },
  "quantitative_evidence": {
    "cleaned_characters": 79316,
    "required_parent_ids": [
      "self-host/deploy/configuration/environments#p10",
      "self-host/deploy/configuration/environments#p11",
      "self-host/deploy/configuration/environments#p9"
    ],
    "raw_excerpt_prefix_limit": 12000
  }
}
```

</details>


## dev063：官方对自部署跨机房灾备承诺的恢复点、恢复时间和切换期限各是多少？

参考答案：冻结资料没有给出自部署跨机房灾备的恢复点、恢复时间或故障切换期限承诺，不能报出具体数值；备份与迁移操作说明不等于这些保证。

版本：未限定；预期行为：acknowledge_missing_evidence；最可能失败：把备份操作建议编造成RPO/RTO或灾备SLA。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 32,
    "vital_count": 0
  }
}
```

</details>

备注：RPO/RTO/VAT等短英文片段可能命中其他词内部；不把词边界0伪装成原文子串0，另列真实近似长词。


## dev064：云版日本企业付款后，税务发票注册号与申请和开票期限怎样规定？

参考答案：资料只提到可查看账单、下载发票，没有日本税务发票注册号或申请、开票期限规定，无法给出这些参数；不能由资料不足推出不提供发票。

版本：未限定；预期行为：acknowledge_missing_evidence；最可能失败：从下载发票泛化出日本税号或税务期限。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 30,
    "vital_count": 0
  }
}
```

</details>

备注：RPO/RTO/VAT等短英文片段可能命中其他词内部；不把词边界0伪装成原文子串0，另列真实近似长词。


## dev065：把含用户输入的全部节点复制到另一实例，让原空间资源原样继承，怎么做？

参考答案：不能按该前提操作。跨画布或实例复制不包含用户输入节点。粘贴会迁移节点配置，但变量等工作流资源、集成和知识库等工作空间资源会在目标重新评估，不能保证原样继承。

版本：未限定；预期行为：corrects_premise；最可能失败：顺着错误前提给迁移步骤，遗漏用户输入例外与资源重评估。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 34,
    "vital_count": 0
  }
}
```

</details>


## dev066：知识流水线的本地文件源一批能传多少份？

参考答案：需先确认部署方式及套餐：知识流水线文件源在Cloud的Sandbox为每批1个，Professional/Team最多50个；社区自部署默认每批20个。可据此条件回答，也可先询问。

版本：未限定；预期行为：clarify_or_conditional_answer；最可能失败：混用即用型上传的5个默认值，或未区分流水线两版的20与1/50。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 19,
    "vital_count": 0
  }
}
```

</details>


## dev067：想让应用支持文件，在哪儿配置？

参考答案：你是想接收上传，还是让模型理解内容？前者在用户输入节点设单个文件或文件列表，该节点只收集、不解析内容；后者选具相应多模态能力的模型并启用文件类型。

版本：未限定；预期行为：clarify_or_conditional_answer；最可能失败：只解释上传开关，忽略接收与理解内容的两种需求。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "source_grounded": true,
    "model_or_retrieval_validation": "not_run",
    "question_characters": 15,
    "vital_count": 0
  }
}
```

</details>
