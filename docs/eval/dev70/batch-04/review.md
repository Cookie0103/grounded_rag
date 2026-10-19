# batch-04审阅稿

固定语料：langgenius/dify-docs @ c80a31868611b673bd77725a6310c685068a585e（CC BY 4.0）。新70为dev021～090，旧20独立回归。题目为交审草案，未运行完整系统、无检索基线或付费评分。原样单次检索的实际状态见validation.json和retrieval-selftest.jsonl。

等价来源组内OR、必要来源组间AND；现有正式评分加载器尚不保留gold_doc_groups。静态符合条件和候选召回不等于难度、答案效果或人工审核通过。

| ID | 行为 / 子类 | vital数 | 预期路由 | 题目 |
|---|---|---:|---|---|
| dev068 | 单跳 / 同义改写 | 2 | SINGLE | 上游偶发失败，怎样让后续用备用文案照跑，文案类型有何要求？ |
| dev069 | 单跳 / 同义改写 | 3 | SINGLE | 范例待审时能撤回吗，递交前插件来源和试跑环境有何要求？ |
| dev070 | 单跳 / 数值/表格 | 2 | SINGLE | 导入Skill包默认多大，调上限用哪个配置？ |
| dev071 | 单跳 / 数值/表格 | 2 | SINGLE | 上传文件给外部存储该选哪种正文，非文本响应会变成什么变量？ |
| dev072 | 单跳 / 易混 | 3 | SINGLE | 思考混进答复时，哪些模型能拆开，拆后两份输出各去哪儿？ |
| dev073 | 单跳 / 易混 | 2 | SINGLE | 每轮沿用上一稿再润色，该用什么节点？没设退出条件会何时停？ |
| dev074 | 单跳 / 短问 | 2 | SINGLE | 在哪查哪步最慢和单步最近的入出参？ |
| dev075 | 单跳 / 单问版本 | 2 | SINGLE | 云端Sandbox能存流水线模板吗，获准发布后模板在哪？ |
| dev076 | 单跳 / 单问版本 | 2 | SINGLE | 从市场给云端装集成却跳到别处，怎样改回？谁能调整安装权限？ |
| dev077 | 多跳 / 链式 | 4 | MULTI | 后端跑完流程后该留哪个持久编号？运营拿它怎样查到各步并按原输入重演？ |
| dev078 | 多跳 / 链式 | 4 | MULTI | Chatflow等人填写时，携带交互凭证和结束当前响应的事件各是哪一个？用它附本地文件怎样引用，提交被拒后凭证还能复用吗？ |
| dev079 | 多跳 / 链式 | 4 | MULTI | Dify第9课的固定排版环节放在哪，正文取谁的值？该环节怎样读嵌套姓名并兜底缺失项？ |
| dev080 | 多跳 / 并列/比较 | 3 | MULTI | Arize AX与Phoenix Cloud除密钥、项目名外各缺哪个空间字段？后者要哪类密钥？ |
| dev081 | 多跳 / 并列/比较 | 4 | MULTI | Langfuse除保密凭据还填什么地址和公开标识？LangSmith凭据选哪类，项目名写错会怎样？ |
| dev082 | 多跳 / 并列/比较 | 4 | MULTI | 无现成插件的接口如何接入，在画布怎样选操作和凭证，默认凭证在哪改？ |
| dev083 | 多跳 / 并列/比较 | 4 | MULTI | 自建拆子域后登录失效，要改哪两个Cookie变量？换域名后401看哪个控制台跨域项，域名共享有何边界？ |
| dev084 | 多跳 / 分散/有序 | 4 | MULTI | 外置Weaviate接v4客户端前要升到哪版、通哪个端口？Dify1.11后Worker迁移加什么选项，如何验收？ |
| dev085 | 多跳 / 分散/有序 | 4 | MULTI | Agent构建时放弃、运行时新增文件、重开对话和恢复旧版，分别怎样影响文件或构建笔记？ |
| dev086 | 拒答与纠正 / 库内缺依据 | 0 | null | 社区集成报漏洞后，官方承诺多久响应、多久发补丁？ |
| dev087 | 拒答与纠正 / 错误前提 | 0 | null | 教我保留事件触发器，把同一流程直接发布成MCP服务。 |
| dev088 | 拒答与纠正 / 无关 | 0 | REFUSE | 我用LangGraph搭RAG，给它的PostgreSQL业务库写一套Patroni跨机房故障转移配置。 |
| dev089 | 模糊 / 版本不明 | 0 | CLARIFY | 别人导出的DSL，导入就一定兼容吗？ |
| dev090 | 模糊 / 缺关键信息 | 0 | CLARIFY | 想把外部系统的资料接进来，怎么配？ |

## dev068：上游偶发失败，怎样让后续用备用文案照跑，文案类型有何要求？

参考答案：将节点错误处理设为“默认值”，失败时以备用值替代后继续运行；备用文案类型必须与该节点输出类型相同。

版本：self_host；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：选择默认值模式可在节点失败时用备用值继续运行。
   - [self-host/use-dify/build/predefined-error-handling-logic L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/predefined-error-handling-logic.mdx#L23-L23)；`self-host/use-dify/build/predefined-error-handling-logic#c0` / `self-host/use-dify/build/predefined-error-handling-logic#p0`。

     > <Accordion title="默认值">

   - [self-host/use-dify/build/predefined-error-handling-logic L24–24](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/predefined-error-handling-logic.mdx#L24-L24)；`self-host/use-dify/build/predefined-error-handling-logic#c0` / `self-host/use-dify/build/predefined-error-handling-logic#p0`。

     > 当节点失败时，使用备用值代替。工作流继续运行。

2. **vital**：备用值必须与节点输出类型相同。
   - [self-host/use-dify/build/predefined-error-handling-logic L31–31](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/predefined-error-handling-logic.mdx#L31-L31)；`self-host/use-dify/build/predefined-error-handling-logic#c0` / `self-host/use-dify/build/predefined-error-handling-logic#p0`。

     > - 默认值必须与节点的输出类型匹配，如果输出字符串，你的默认值也必须是字符串。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 29,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 2,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev069：范例待审时能撤回吗，递交前插件来源和试跑环境有何要求？

参考答案：Pending状态可撤回到Draft，修改后重新提交。插件须直接从Dify市场安装；应用须在最新Community Edition上至少运行一次，以此核验兼容性。

版本：self_host；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：Pending状态的模板可撤回为Draft后修改并重新提交。
   - [self-host/use-dify/publish/publish-to-marketplace L17–17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/publish-to-marketplace.mdx#L17-L17)；`self-host/use-dify/publish/publish-to-marketplace#c1` / `self-host/use-dify/publish/publish-to-marketplace#p1`。

     > 模板处于 **Pending** 状态时，可随时撤回。撤回后，模板将回到 **Draft** 状态，你可修改任意内容后重新提交。

2. **vital**：提交前应用使用的所有插件须直接从市场安装。
   - [self-host/use-dify/publish/publish-to-marketplace L21–21](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/publish-to-marketplace.mdx#L21-L21)；`self-host/use-dify/publish/publish-to-marketplace#c1` / `self-host/use-dify/publish/publish-to-marketplace#p1`。

     > - 请确保应用中使用的所有插件都 **直接从市场安装**。

3. **vital**：提交前应在最新Community Edition上至少运行一次应用。
   - [self-host/use-dify/publish/publish-to-marketplace L22–22](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/publish/publish-to-marketplace.mdx#L22-L22)；`self-host/use-dify/publish/publish-to-marketplace#c1` / `self-host/use-dify/publish/publish-to-marketplace#p1`。

     > - 在最新 Community Edition 上至少运行一次应用，确认其正常工作。市场会根据最新 Community Edition 来审核应用模板的兼容性。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 27,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 3,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev070：导入Skill包默认多大，调上限用哪个配置？

参考答案：导入包默认最大50 MB；用UPLOAD_SKILL_FILE_SIZE_LIMIT调整上限。

版本：self_host；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：导入Skill包的默认大小上限为50 MB。
   - [self-host/use-dify/build/skills L61–61](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/skills.mdx#L61-L61)；`self-host/use-dify/build/skills#c5` / `self-host/use-dify/build/skills#p3`。

     > 大小默认不超过 50 MB

2. **vital**：导入包体积上限由UPLOAD_SKILL_FILE_SIZE_LIMIT调整。
   - [self-host/use-dify/build/skills L61–61](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/skills.mdx#L61-L61)；`self-host/use-dify/build/skills#c5` / `self-host/use-dify/build/skills#p3`。

     > `UPLOAD_SKILL_FILE_SIZE_LIMIT`

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "kind": "数值及配置查读",
    "similarity": "均为Skill页面文件处理限制；Builder每消息10附件、图片10MB、其他文件15MB是同类干扰，不能套作导入包上限。"
  },
  "quantitative_evidence": {
    "question_characters": 22,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 2,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev071：上传文件给外部存储该选哪种正文，非文本响应会变成什么变量？

参考答案：发送前序文件变量时选“二进制”请求正文；返回的二进制等非文本内容会成为文件变量，供后续节点使用。

版本：self_host；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：上传文件变量使用二进制请求正文。
   - [self-host/use-dify/nodes/http-request L95–95](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/http-request.mdx#L95-L95)；`self-host/use-dify/nodes/http-request#c8` / `self-host/use-dify/nodes/http-request#p8`。

     > **文件上传** 使用二进制请求正文选项。从先前节点选择文件变量，将文件发送到外部服务进行文档存储、媒体处理或备份。

2. **vital**：二进制响应内容成为文件变量。
   - [self-host/use-dify/nodes/http-request L85–85](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/http-request.mdx#L85-L85)；`self-host/use-dify/nodes/http-request#c7` / `self-host/use-dify/nodes/http-request#p7`。

     > 基于文本的响应（JSON、XML、HTML 等）被视为常规数据，而二进制内容则成为文件变量。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "hardness_evidence": {
    "kind": "正文格式枚举/配置查读，无答案数值",
    "similarity": "JSON、表单数据、原始文本三种真实正文格式是同类选项；不借不同单位的数字冒充干扰。"
  },
  "quantitative_evidence": {
    "question_characters": 29,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 2,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev072：思考混进答复时，哪些模型能拆开，拆后两份输出各去哪儿？

参考答案：仅适用于以think标签包裹思考的模型；开启“启用推理标签分离”后，text仅保留回答，思考内容移至reasoning_content输出。

版本：self_host；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：开启推理标签分离后，text仅保留回答。
   - [self-host/use-dify/nodes/llm L143–143](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/llm.mdx#L143-L143)；`self-host/use-dify/nodes/llm#c11` / `self-host/use-dify/nodes/llm#p10`。

     > 打开 **启用推理标签分离** 开关即可将两者分开：`text` 输出仅保留回答，思考过程则移至独立的 `reasoning_content` 输出变量。开关关闭时，`reasoning_content` 为空。

2. **vital**：分离的思考内容进入reasoning_content输出。
   - [self-host/use-dify/nodes/llm L143–143](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/llm.mdx#L143-L143)；`self-host/use-dify/nodes/llm#c11` / `self-host/use-dify/nodes/llm#p10`。

     > 打开 **启用推理标签分离** 开关即可将两者分开：`text` 输出仅保留回答，思考过程则移至独立的 `reasoning_content` 输出变量。开关关闭时，`reasoning_content` 为空。

3. **vital**：该开关只适用于以think标签包裹思考的模型。
   - [self-host/use-dify/nodes/llm L148–148](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/llm.mdx#L148-L148)；`self-host/use-dify/nodes/llm#c12` / `self-host/use-dify/nodes/llm#p10`。

     > 此设置仅对用 `<think>` 标签包裹推理内容的模型生效。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "distractor_docs": [
    "self-host/use-dify/nodes/parameter-extractor"
  ],
  "quantitative_evidence": {
    "question_characters": 27,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 3,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>

备注：最终独立审题后主agent按冻结原文修正；具体发现、原版hash和闭环见semantic-review.json及blueprint-amendments.json。


## dev073：每轮沿用上一稿再润色，该用什么节点？没设退出条件会何时停？

参考答案：用循环节点，因为每轮依赖前一轮结果；不设终止条件时会持续到达到最大循环次数。

版本：self_host；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：依赖上一轮结果继续处理应使用循环节点。
   - [self-host/use-dify/nodes/loop L8–8](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/loop.mdx#L8-L8)；`self-host/use-dify/nodes/loop#c0` / `self-host/use-dify/nodes/loop#p0`。

     > 循环节点执行重复性工作流，每个循环都基于前一个循环的结果进行构建。与迭代处理数组元素独立不同，循环创建的是随着每次重复而演进的渐进式工作流。

2. **vital**：未指定终止条件时，循环持续到最大循环次数。
   - [self-host/use-dify/nodes/loop L53–53](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/loop.mdx#L53-L53)；`self-host/use-dify/nodes/loop#c3` / `self-host/use-dify/nodes/loop#p3`。

     > 当满足终止条件、达到最大次数或执行退出循环节点时，循环终止。如果未指定条件，循环将继续直到达到最大次数。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "distractor_docs": [
    "self-host/use-dify/nodes/iteration"
  ],
  "quantitative_evidence": {
    "question_characters": 29,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 2,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev074：在哪查哪步最慢和单步最近的入出参？

参考答案：在应用运行历史的“追踪”查看每个节点耗时；单节点配置面板点“最后运行”，查看该节点最近输入、输出和时间详情。

版本：self_host；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：应用运行历史的追踪展示各节点耗时。
   - [self-host/use-dify/debug/history-and-logs L44–44](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/history-and-logs.mdx#L44-L44)；`self-host/use-dify/debug/history-and-logs#c4` / `self-host/use-dify/debug/history-and-logs#p4`。

     > 准确显示工作流的执行过程，包括哪些节点按什么顺序运行、每个节点耗时多长，以及数据在节点间如何流动。这对于找出瓶颈和理解具有分支或循环的复杂工作流很有用。

2. **vital**：节点配置面板的最后运行展示最近输入、输出和时间。
   - [self-host/use-dify/debug/history-and-logs L52–52](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/history-and-logs.mdx#L52-L52)；`self-host/use-dify/debug/history-and-logs#c5` / `self-host/use-dify/debug/history-and-logs#p5`。

     > 你也可以检查任何单个节点的最后一次执行。在节点配置面板中点击"最后运行"，查看其最近的输入、输出和时间详情。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 17,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 2,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev075：云端Sandbox能存流水线模板吗，获准发布后模板在哪？

参考答案：Sandbox不能发布为可复用流水线模板，该功能限Professional和Team；在允许的套餐中发布为流水线后，模板出现在“自定义模板”中。

版本：cloud；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：云端Sandbox不能将流水线发布为可复用模板。
   - [cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline L54–54](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline.mdx#L54-L54)；`cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline#c1` / `cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline#p0`。

     > Sandbox 账户无法将流水线发布为可复用模板。

2. **vital**：发布为流水线后，模板出现在自定义模板中。
   - [cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline L49–49](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline.mdx#L49-L49)；`cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline#c1` / `cloud/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline#p0`。

     > 你可以点击发布为知识流水线将该流水线保存为可复用的模版，该模版将出现在自定义模版中。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "counterpart_docs": [
    "self-host/use-dify/knowledge/knowledge-pipeline/publish-knowledge-pipeline"
  ],
  "quantitative_evidence": {
    "question_characters": 28,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 2,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev076：从市场给云端装集成却跳到别处，怎样改回？谁能调整安装权限？

参考答案：清除“安装偏好设置”中保存的URL，即可重新安装到Dify Cloud。工作空间所有者和管理员可以在“集成”页面底部的“权限”中调整谁能安装和调试集成。

版本：cloud；预期行为：answered；最可能失败：把自部署填入部署URL的步骤套给Cloud，或把权限设置者误判为普通成员。。

1. **vital**：市场安装目标误指别处时，清除安装偏好设置中保存的URL以恢复安装到Dify Cloud。
   - [cloud/use-dify/workspace/plugins L36–36](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/plugins.mdx#L36-L36)；`cloud/use-dify/workspace/plugins#c2` / `cloud/use-dify/workspace/plugins#p2`。

     > 如果从市场安装时打开的是其他 Dify 环境而非你的 Dify Cloud 工作空间，清除 **安装偏好设置** 中保存的 URL 即可重新安装到 Dify Cloud。

2. **vital**：工作空间所有者和管理员可以在集成页面底部的权限中设置安装权限。
   - [cloud/use-dify/workspace/plugins L46–46](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/plugins.mdx#L46-L46)；`cloud/use-dify/workspace/plugins#c3` / `cloud/use-dify/workspace/plugins#p3`。

     > 工作空间所有者和管理员可在 **集成** 页面底部的 **权限** 中，设置谁能安装和调试集成。每项权限都可以设为所有人可用、仅管理员可用或无人可用：

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "counterpart_docs": [
    "self-host/use-dify/workspace/plugins"
  ],
  "quantitative_evidence": {
    "question_characters": 29,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 2,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>

备注：最终独立审题reject原自动停用题：self-host只省略该机制，无法证明实际版本不同。改为双版均正面规定的市场安装目标选择；独立审查者已核对并认可此候选，正式来源由主agent严格定位。


## dev077：后端跑完流程后该留哪个持久编号？运营拿它怎样查到各步并按原输入重演？

参考答案：保留workflow_run_id，它指向运行结束后持久保存的记录。运营在应用“日志”中粘贴该编号定位记录，点击该次运行查看逐节点追踪，再点“按此参数测试”，在编辑器中以原输入重新运行。后者是新测试，并非恢复原运行。

版本：未限定；预期行为：answered；最可能失败：不能用task_id定位持久记录，也不能把重新测试描述为继续原运行；它是用原输入发起新测试。。

1. **vital**：应保留workflow_run_id作为运行结束后的持久化记录标识。
   - [api-reference/guides/workflow L24–24](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/workflow.mdx#L24-L24)；`api-reference/guides/workflow#c2` / `api-reference/guides/workflow#p2`。

     > 无论选择哪种模式，响应都会携带两个 ID：`task_id` 用于控制运行中的任务，`workflow_run_id` 用于标识运行结束后持久保存的记录。

2. **vital**：在应用日志页粘贴运行ID可定位该次运行。
   等价来源（任一成立）：
   - [self-host/use-dify/monitor/logs L8–8](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/logs.mdx#L8-L8)；`self-host/use-dify/monitor/logs#c0` / `self-host/use-dify/monitor/logs#p0`。

     > 在任意应用的 **日志** 页面中，可看到应用的真实使用情况：用户提交了什么、应用如何响应、收到了哪些反馈。

   - [cloud/use-dify/monitor/logs L8–8](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/logs.mdx#L8-L8)；`cloud/use-dify/monitor/logs#c0` / `cloud/use-dify/monitor/logs#p0`。

     > 在任意应用的 **日志** 页面中，可看到应用的真实使用情况：用户提交了什么、应用如何响应、收到了哪些反馈。

   等价来源（任一成立）：
   - [self-host/use-dify/monitor/logs L33–33](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/logs.mdx#L33-L33)；`self-host/use-dify/monitor/logs#c3` / `self-host/use-dify/monitor/logs#p2`。

     > 要查找某次对话，可搜索消息中的文字或终端用户的会话 ID。要查找某次工作流运行，可搜索运行的输入或输出，或直接粘贴运行 ID。

   - [cloud/use-dify/monitor/logs L33–33](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/logs.mdx#L33-L33)；`cloud/use-dify/monitor/logs#c3` / `cloud/use-dify/monitor/logs#p2`。

     > 要查找某次对话，可搜索消息中的文字或终端用户的会话 ID。要查找某次工作流运行，可搜索运行的输入或输出，或直接粘贴运行 ID。

3. **vital**：点击该次运行可查看逐节点执行追踪。
   等价来源（任一成立）：
   - [self-host/use-dify/monitor/logs L48–48](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/logs.mdx#L48-L48)；`self-host/use-dify/monitor/logs#c5` / `self-host/use-dify/monitor/logs#p4`。

     > 对于 Workflow 应用，点击某次运行可查看其结果、带状态和 token 总量的输入输出，以及逐节点的执行追踪，便于定位运行失败或变慢的环节。

   - [cloud/use-dify/monitor/logs L48–48](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/logs.mdx#L48-L48)；`cloud/use-dify/monitor/logs#c5` / `cloud/use-dify/monitor/logs#p4`。

     > 对于 Workflow 应用，点击某次运行可查看其结果、带状态和 token 总量的输入输出，以及逐节点的执行追踪，便于定位运行失败或变慢的环节。

4. **vital**：按此参数测试会在编辑器中用原输入重新运行。
   等价来源（任一成立）：
   - [self-host/use-dify/monitor/logs L50–50](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/logs.mdx#L50-L50)；`self-host/use-dify/monitor/logs#c5` / `self-host/use-dify/monitor/logs#p4`。

     > 要复现问题，点击 **按此参数测试**：工作流会在编辑器中以该次运行的输入重新运行。

   - [cloud/use-dify/monitor/logs L50–50](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/logs.mdx#L50-L50)；`cloud/use-dify/monitor/logs#c5` / `cloud/use-dify/monitor/logs#p4`。

     > 要复现问题，点击 **按此参数测试**：工作流会在编辑器中以该次运行的输入重新运行。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "distractor_docs": [
    "self-host/use-dify/debug/history-and-logs",
    "cloud/use-dify/monitor/analysis"
  ],
  "chain": {
    "bridge_type": "API响应持久化标识→控制台精确定位与原参数重演",
    "first_document": "api-reference/guides/workflow",
    "second_document": "self-host/use-dify/monitor/logs",
    "second_document_answer_keywords": [
      "运行 ID",
      "日志",
      "输入或输出",
      "逐节点的执行追踪",
      "按此参数测试",
      "编辑器"
    ],
    "dependency": "必须先从返回中的两个ID选出持久运行ID，再将该实体传给第二篇中的界面定位机制；第二篇新增精确搜索、逐节点追踪和原参数复现的操作，不能只回答导航到日志页。",
    "generic_distractor_documents": [
      {
        "document_id": "self-host/use-dify/debug/history-and-logs",
        "shared_generic_terms": [
          "流程",
          "各步",
          "运营"
        ],
        "why_not_sufficient": "同样讲执行追踪和每节点耗时，不给API两个ID含义、真实日志按运行ID查找及按此参数测试入口。",
        "source": {
          "document_id": "self-host/use-dify/debug/history-and-logs",
          "heading_path": "运行历史 > 应用运行历史 > 追踪",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/history-and-logs.mdx#L44-L44",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/debug/history-and-logs.mdx",
          "raw_line_start": 44,
          "raw_line_end": 44,
          "original_excerpt": "准确显示工作流的执行过程，包括哪些节点按什么顺序运行、每个节点耗时多长，以及数据在节点间如何流动。这对于找出瓶颈和理解具有分支或循环的复杂工作流很有用。",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/debug/history-and-logs#c4",
            "excerpt": "准确显示工作流的执行过程，包括哪些节点按什么顺序运行、每个节点耗时多长，以及数据在节点间如何流动。这对于找出瓶颈和理解具有分支或循环的复杂工作流很有用。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/debug/history-and-logs#p4",
            "heading_path": "运行历史 > 应用运行历史 > 追踪",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 246,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "87a6a5ef2af483e92601eb56d23ac4c6173cbd897051294a961c670997d2b577",
          "reconstruct_verified": true
        }
      },
      {
        "document_id": "cloud/use-dify/monitor/analysis",
        "shared_generic_terms": [
          "流程",
          "各步",
          "运营"
        ],
        "why_not_sufficient": "同样讲应用监控和token指标，但为聚合趋势，不提供单次运行定位和原参数重演。",
        "source": {
          "document_id": "cloud/use-dify/monitor/analysis",
          "heading_path": "仪表盘",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/analysis.mdx#L8-L8",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/analysis.mdx",
          "raw_line_start": 8,
          "raw_line_end": 8,
          "original_excerpt": "该仪表盘随时间跟踪四个指标，以展示你的应用的表现：",
          "direct_evidence": {
            "chunk_id": "cloud/use-dify/monitor/analysis#c0",
            "excerpt": "该仪表盘随时间跟踪四个指标，以展示你的应用的表现：",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "cloud/use-dify/monitor/analysis#p0",
            "heading_path": "仪表盘",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 0,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "0a26258a0d24b24186c04733dc3a1e178ee94b4317e9937642f66d958ebab7e1",
          "reconstruct_verified": true
        }
      }
    ]
  },
  "quantitative_evidence": {
    "question_characters": 34,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 4,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev078：Chatflow等人填写时，携带交互凭证和结束当前响应的事件各是哪一个？用它附本地文件怎样引用，提交被拒后凭证还能复用吗？

参考答案：human_input_required事件携带form_token，随后workflow_paused事件结束当前响应流。先上传本地文件，取返回的id，在提交中用upload_file_id引用。提交被拒时表单保持不变；修正输入后可用同一form_token重新提交。

版本：未限定；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：human_input_required事件携带form_token交互凭证。
   - [api-reference/guides/chatflow L47–47](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/chatflow.mdx#L47-L47)；`api-reference/guides/chatflow#c5` / `api-reference/guides/chatflow#p5`。

     > 事件流会推送 `human_input_required` 事件，其中携带 `form_token` 和本次运行的 `workflow_run_id`，随后以 `workflow_paused` 事件结束。

2. **vital**：workflow_paused事件结束当前响应流。
   - [api-reference/guides/chatflow L47–47](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/chatflow.mdx#L47-L47)；`api-reference/guides/chatflow#c5` / `api-reference/guides/chatflow#p5`。

     > 事件流会推送 `human_input_required` 事件，其中携带 `form_token` 和本次运行的 `workflow_run_id`，随后以 `workflow_paused` 事件结束。

3. **vital**：本地附件先上传，返回的id在提交中以upload_file_id引用。
   - [api-reference/guides/human-input-flow L33–33](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/human-input-flow.mdx#L33-L33)；`api-reference/guides/human-input-flow#c2` / `api-reference/guides/human-input-flow#p1`。

     > 若接收者为 `file` 或 `file-list` 输入附加了本地文件，请先通过 [上传文件](/zh/api-reference/files/upload-file) 上传。

   - [api-reference/guides/human-input-flow L33–33](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/human-input-flow.mdx#L33-L33)；`api-reference/guides/human-input-flow#c2` / `api-reference/guides/human-input-flow#p1`。

     > 该接口返回一个 `id`，提交时作为 `upload_file_id` 引用。

4. **vital**：提交被拒后可修正输入，以同一form_token重新提交。
   - [api-reference/guides/human-input-flow L44–44](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/human-input-flow.mdx#L44-L44)；`api-reference/guides/human-input-flow#c4` / `api-reference/guides/human-input-flow#p1`。

     > 若提交被拒绝（操作无效、缺少必填输入，或远程文件抓取失败），表单保持不变，修正输入后可用同一个 `form_token` 重新提交。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "distractor_docs": [
    "api-reference/guides/workflow",
    "api-reference/guides/streaming"
  ],
  "chain": {
    "bridge_type": "暂停事件产物→表单状态机与恢复关联",
    "first_document": "api-reference/guides/chatflow",
    "second_document": "api-reference/guides/human-input-flow",
    "second_document_answer_keywords": [
      "form_token",
      "id",
      "upload_file_id",
      "表单保持不变",
      "重新提交"
    ],
    "dependency": "Chatflow篇是所问workflow_paused原流结束事件的来源，第一步产生form_token；后续本地附件引用和提交被拒绝后的令牌复用由第二篇补足。第一篇不能完成后续，第二篇未给workflow_paused结束事件名。",
    "generic_distractor_documents": [
      {
        "document_id": "api-reference/guides/workflow",
        "shared_generic_terms": [
          "事件",
          "交互",
          "本地",
          "提交"
        ],
        "why_not_sufficient": "同样包含暂停事件和句柄，是第一步的邻近来源；没有本地附件upload_file_id及被拒绝后同token重试的第二步规则。",
        "source": {
          "document_id": "api-reference/guides/workflow",
          "heading_path": "Workflow 应用 API > 人工介入暂停",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/workflow.mdx#L37-L37",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/workflow.mdx",
          "raw_line_start": 37,
          "raw_line_end": 37,
          "original_excerpt": "运行的事件流会推送 `human_input_required` 事件，其中携带 `form_token` 和本次运行的 `workflow_run_id`，随后以 `workflow_paused` 事件结束。",
          "direct_evidence": {
            "chunk_id": "api-reference/guides/workflow#c3",
            "excerpt": "运行的事件流会推送 `human_input_required` 事件，其中携带 `form_token` 和本次运行的 `workflow_run_id`，随后以 `workflow_paused` 事件结束。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "api-reference/guides/workflow#p3",
            "heading_path": "Workflow 应用 API > 人工介入暂停",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 685,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "c41724a7896a140c6f5fc53c109a145ca4505ca07684c230aa37f00f1709dc32",
          "reconstruct_verified": true
        }
      },
      {
        "document_id": "api-reference/guides/streaming",
        "shared_generic_terms": [
          "事件",
          "交互",
          "本地",
          "提交"
        ],
        "why_not_sufficient": "同样讲暂停/恢复/同user，但不提供表单本地附件映射或拒绝后的表单/令牌状态。",
        "source": {
          "document_id": "api-reference/guides/streaming",
          "heading_path": "处理流式响应 > 重连与恢复",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx#L99-L99",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/api-reference/guides/streaming.mdx",
          "raw_line_start": 99,
          "raw_line_end": 99,
          "original_excerpt": "对由工作流驱动的运行（Workflow 和 Chatflow 应用），连接断开并非致命问题。",
          "direct_evidence": {
            "chunk_id": "api-reference/guides/streaming#c7",
            "excerpt": "对由工作流驱动的运行（Workflow 和 Chatflow 应用），连接断开并非致命问题。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "api-reference/guides/streaming#p5",
            "heading_path": "处理流式响应 > 重连与恢复",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 2346,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "ea6e8df7088ec0bcb72b76009a9e3ae8cefc50df645b59be675fdf654a9fdd50",
          "reconstruct_verified": true
        }
      }
    ]
  },
  "quantitative_evidence": {
    "question_characters": 61,
    "at_most_40": false,
    "at_most_80": true,
    "vital_count": 4,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev079：Dify第9课的固定排版环节放在哪，正文取谁的值？该环节怎样读嵌套姓名并兜底缺失项？

参考答案：在Agent之后、输出节点之前插入模板转换节点，其body变量接Agent的text输出。该环节可用点号或括号读取嵌套对象或数组，例如{{user.name}}；缺失字段可用default过滤器提供默认值，例如{{user.name | default("there")}}。

版本：self_host；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：第9课的模板转换节点放在Agent之后、输出之前。
   - [learn/tutorials/workflow-101/lesson-09 L35–35](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/learn/tutorials/workflow-101/lesson-09.mdx#L35-L35)；`learn/tutorials/workflow-101/lesson-09#c2` / `learn/tutorials/workflow-101/lesson-09#p2`。

     > 在 Agent 节点之后、输出节点之前插入一个模板转换节点。

2. **vital**：模板body变量接Agent的text输出。
   - [learn/tutorials/workflow-101/lesson-09 L45–45](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/learn/tutorials/workflow-101/lesson-09.mdx#L45-L45)；`learn/tutorials/workflow-101/lesson-09#c2` / `learn/tutorials/workflow-101/lesson-09#p2`。

     > - `body`：`Agent /{x} text`

3. **vital**：该环节用点号或括号访问嵌套对象或数组元素。
   - [self-host/use-dify/nodes/template L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/template.mdx#L20-L20)；`self-host/use-dify/nodes/template#c2` / `self-host/use-dify/nodes/template#p2`。

     > 使用双花括号引用工作流变量：`{{ variable_name }}`。可使用点号和括号语法访问嵌套对象属性和数组元素。

4. **vital**：该环节用default过滤器给缺失字段提供默认值。
   - [self-host/use-dify/nodes/template L76–76](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/template.mdx#L76-L76)；`self-host/use-dify/nodes/template#c6` / `self-host/use-dify/nodes/template#p6`。

     > {{ user.email | default('No email provided') }}

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "distractor_docs": [
    "self-host/use-dify/nodes/llm",
    "self-host/use-dify/nodes/answer"
  ],
  "chain": {
    "bridge_type": "教程数据交接→格式语法及缺失值处理",
    "first_document": "learn/tutorials/workflow-101/lesson-09",
    "second_document": "self-host/use-dify/nodes/template",
    "second_document_answer_keywords": [
      "点号",
      "括号",
      "嵌套对象",
      "数组元素",
      "default",
      "默认值"
    ],
    "dependency": "课程确定把正文与客户名交给模板，第二篇提供课程挑战所缺的兜底与嵌套取值语法；仅保留一题教程→节点。仍待独立必要性审核。",
    "generic_distractor_documents": [
      {
        "document_id": "self-host/use-dify/nodes/llm",
        "shared_generic_terms": [
          "正文",
          "值",
          "排版",
          "环节"
        ],
        "why_not_sufficient": "同样支持变量/条件/Jinja2，可能误导把排版放回模型；无本题所问default兜底完整说明与课程的模板交接。",
        "source": {
          "document_id": "self-host/use-dify/nodes/llm",
          "heading_path": "大语言模型 > Jinja2 模板支持",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/llm.mdx#L125-L125",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/llm.mdx",
          "raw_line_start": 125,
          "raw_line_end": 125,
          "original_excerpt": "大型语言模型提示词支持 Jinja2 模板以进行高级变量处理。当你使用 Jinja2 模式（`edition_type: \"jinja2\"`）时，你可以：",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/nodes/llm#c9",
            "excerpt": "大型语言模型提示词支持 Jinja2 模板以进行高级变量处理。当你使用 Jinja2 模式（`edition_type: \"jinja2\"`）时，你可以：",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/nodes/llm#p8",
            "heading_path": "大语言模型 > Jinja2 模板支持",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 2003,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "59563d365a33233f7573a29afca12f97a841a8b5b1043a407a44a904b632d125",
          "reconstruct_verified": true
        }
      },
      {
        "document_id": "self-host/use-dify/nodes/answer",
        "shared_generic_terms": [
          "正文",
          "值",
          "排版",
          "环节"
        ],
        "why_not_sufficient": "同样将固定文本与变量组合，但只给变量插入，不提供default过滤器和嵌套对象/数组语法契约。",
        "source": {
          "document_id": "self-host/use-dify/nodes/answer",
          "heading_path": "直接回复 > 内容配置",
          "source_url": "https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/answer.mdx#L16-L16",
          "frozen_path": "data/raw/dify-docs/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/answer.mdx",
          "raw_line_start": 16,
          "raw_line_end": 16,
          "original_excerpt": "直接回复节点提供了一个灵活的文本编辑器，你可以使用固定文本、来自先前节点的变量或两者的组合来制作响应。",
          "direct_evidence": {
            "chunk_id": "self-host/use-dify/nodes/answer#c1",
            "excerpt": "直接回复节点提供了一个灵活的文本编辑器，你可以使用固定文本、来自先前节点的变量或两者的组合来制作响应。",
            "contains_excerpt": true
          },
          "supporting_parent": {
            "parent_id": "self-host/use-dify/nodes/answer#p1",
            "heading_path": "直接回复 > 内容配置",
            "contains_excerpt": true
          },
          "cleaned_character_offset": 138,
          "within_current_judge_first_12000_chars": true,
          "database_verified": true,
          "verification_method": "固定原文逐字定位+生产清洗/切块完整包含；只读实库全量比对182篇hash、2090子块及1252父块全部一致（runtime-verification.json）",
          "source_file_sha256": "fffd1acf415df11983ca5c6b7154c60db80a4f4312f339bd6a9ca0c3ab927589",
          "reconstruct_verified": true
        }
      }
    ]
  },
  "quantitative_evidence": {
    "question_characters": 42,
    "at_most_40": false,
    "at_most_80": true,
    "vital_count": 4,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev080：Arize AX与Phoenix Cloud除密钥、项目名外各缺哪个空间字段？后者要哪类密钥？

参考答案：Arize AX还需Space ID；Phoenix Cloud还需空间主机名。Phoenix Cloud应在空间设置中创建“系统密钥”。

版本：未限定；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：Arize AX还需Space ID。
   等价来源（任一成立）：
   - [self-host/use-dify/monitor/integrations/integrate-arize L37–37](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-arize.mdx#L37-L37)；`self-host/use-dify/monitor/integrations/integrate-arize#c3` / `self-host/use-dify/monitor/integrations/integrate-arize#p3`。

     > 点击配置后，将在 Arize 中创建的 **API Key**, **Space ID** 和 **项目名称**粘贴到配置中并保存。

   - [cloud/use-dify/monitor/integrations/integrate-arize L37–37](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-arize.mdx#L37-L37)；`cloud/use-dify/monitor/integrations/integrate-arize#c3` / `cloud/use-dify/monitor/integrations/integrate-arize#p3`。

     > 点击配置后，将在 Arize 中创建的 **API Key**, **Space ID** 和 **项目名称**粘贴到配置中并保存。

2. **vital**：Phoenix Cloud还需空间主机名。
   等价来源（任一成立）：
   - [self-host/use-dify/monitor/integrations/integrate-phoenix L87–87](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-phoenix.mdx#L87-L87)；`self-host/use-dify/monitor/integrations/integrate-phoenix#c7` / `self-host/use-dify/monitor/integrations/integrate-phoenix#p7`。

     > 点击配置后，粘贴从 Phoenix Cloud 中获取的 API 密钥、项目名称 和 空间主机名 到配置项中并保存。

   - [cloud/use-dify/monitor/integrations/integrate-phoenix L87–87](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-phoenix.mdx#L87-L87)；`cloud/use-dify/monitor/integrations/integrate-phoenix#c7` / `cloud/use-dify/monitor/integrations/integrate-phoenix#p7`。

     > 点击配置后，粘贴从 Phoenix Cloud 中获取的 API 密钥、项目名称 和 空间主机名 到配置项中并保存。

3. **vital**：Phoenix Cloud在空间设置中创建系统密钥。
   等价来源（任一成立）：
   - [self-host/use-dify/monitor/integrations/integrate-phoenix L73–73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-phoenix.mdx#L73-L73)；`self-host/use-dify/monitor/integrations/integrate-phoenix#c6` / `self-host/use-dify/monitor/integrations/integrate-phoenix#p6`。

     > 启动空间后，你可以在左下角的用户菜单中点击 设置 来创建 Phoenix API 密钥。点击 系统密钥，然后为你的 API 密钥命名：

   - [cloud/use-dify/monitor/integrations/integrate-phoenix L73–73](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-phoenix.mdx#L73-L73)；`cloud/use-dify/monitor/integrations/integrate-phoenix#c6` / `cloud/use-dify/monitor/integrations/integrate-phoenix#p6`。

     > 启动空间后，你可以在左下角的用户菜单中点击 设置 来创建 Phoenix API 密钥。点击 系统密钥，然后为你的 API 密钥命名：

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 47,
    "at_most_40": false,
    "at_most_80": true,
    "vital_count": 3,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev081：Langfuse除保密凭据还填什么地址和公开标识？LangSmith凭据选哪类，项目名写错会怎样？

参考答案：Langfuse还需Host和Public Key；LangSmith凭据选择Personal Access Token。LangSmith配置的项目名与已有项目不一致时，会自动创建新项目。

版本：未限定；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：Langfuse需要填写Host。
   等价来源（任一成立）：
   - [self-host/use-dify/monitor/integrations/integrate-langfuse L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-langfuse.mdx#L42-L42)；`self-host/use-dify/monitor/integrations/integrate-langfuse#c1` / `self-host/use-dify/monitor/integrations/integrate-langfuse#p1`。

     > 复制并保存 **Secret Key**、**Public Key** 和 **Host**。

   - [cloud/use-dify/monitor/integrations/integrate-langfuse L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-langfuse.mdx#L42-L42)；`cloud/use-dify/monitor/integrations/integrate-langfuse#c1` / `cloud/use-dify/monitor/integrations/integrate-langfuse#p1`。

     > 复制并保存 **Secret Key**、**Public Key** 和 **Host**。

2. **vital**：Langfuse需要填写Public Key。
   等价来源（任一成立）：
   - [self-host/use-dify/monitor/integrations/integrate-langfuse L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-langfuse.mdx#L42-L42)；`self-host/use-dify/monitor/integrations/integrate-langfuse#c1` / `self-host/use-dify/monitor/integrations/integrate-langfuse#p1`。

     > 复制并保存 **Secret Key**、**Public Key** 和 **Host**。

   - [cloud/use-dify/monitor/integrations/integrate-langfuse L42–42](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-langfuse.mdx#L42-L42)；`cloud/use-dify/monitor/integrations/integrate-langfuse#c1` / `cloud/use-dify/monitor/integrations/integrate-langfuse#p1`。

     > 复制并保存 **Secret Key**、**Public Key** 和 **Host**。

3. **vital**：LangSmith凭据类型选择Personal Access Token。
   等价来源（任一成立）：
   - [self-host/use-dify/monitor/integrations/integrate-langsmith L49–49](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-langsmith.mdx#L49-L49)；`self-host/use-dify/monitor/integrations/integrate-langsmith#c2` / `self-host/use-dify/monitor/integrations/integrate-langsmith#p1`。

     > 选择 **Personal Access Token** ，用于后续的 API 身份校验。

   - [cloud/use-dify/monitor/integrations/integrate-langsmith L49–49](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-langsmith.mdx#L49-L49)；`cloud/use-dify/monitor/integrations/integrate-langsmith#c2` / `cloud/use-dify/monitor/integrations/integrate-langsmith#p1`。

     > 选择 **Personal Access Token** ，用于后续的 API 身份校验。

4. **vital**：LangSmith配置的项目名不一致会自动创建新项目。
   等价来源（任一成立）：
   - [self-host/use-dify/monitor/integrations/integrate-langsmith L76–76](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/monitor/integrations/integrate-langsmith.mdx#L76-L76)；`self-host/use-dify/monitor/integrations/integrate-langsmith#c2` / `self-host/use-dify/monitor/integrations/integrate-langsmith#p1`。

     > 配置项目名需要与 LangSmith 内设置的项目一致，若项目名不一致，数据同步时 LangSmith 会自动创建一个新的项目。

   - [cloud/use-dify/monitor/integrations/integrate-langsmith L76–76](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/monitor/integrations/integrate-langsmith.mdx#L76-L76)；`cloud/use-dify/monitor/integrations/integrate-langsmith#c2` / `cloud/use-dify/monitor/integrations/integrate-langsmith#p1`。

     > 配置项目名需要与 LangSmith 内设置的项目一致，若项目名不一致，数据同步时 LangSmith 会自动创建一个新的项目。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 49,
    "at_most_40": false,
    "at_most_80": true,
    "vital_count": 4,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev082：无现成插件的接口如何接入，在画布怎样选操作和凭证，默认凭证在哪改？

参考答案：在工作空间的工具中导入OpenAPI（Swagger）规范生成工具接口。画布点击“添加节点 > 工具”，选具体操作；需要认证时选择现有凭证或新建凭证。默认凭证在“集成 > 工具 > 工具插件”修改。

版本：未限定；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：可通过导入OpenAPI规范生成工具接口。
   等价来源（任一成立）：
   - [self-host/use-dify/workspace/tools L28–28](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/tools.mdx#L28-L28)；`self-host/use-dify/workspace/tools#c1` / `self-host/use-dify/workspace/tools#p1`。

     > 通过导入标准的 OpenAPI（Swagger）规范，将尚未以工具插件形式提供的服务集成进来。

   - [cloud/use-dify/workspace/tools L28–28](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/tools.mdx#L28-L28)；`cloud/use-dify/workspace/tools#c1` / `cloud/use-dify/workspace/tools#p1`。

     > 通过导入标准的 OpenAPI（Swagger）规范，将尚未以工具插件形式提供的服务集成进来。

   等价来源（任一成立）：
   - [self-host/use-dify/workspace/tools L30–30](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/workspace/tools.mdx#L30-L30)；`self-host/use-dify/workspace/tools#c1` / `self-host/use-dify/workspace/tools#p1`。

     > 粘贴规范、从 URL 导入，或从提供的示例开始，Dify 会自动生成工具接口。

   - [cloud/use-dify/workspace/tools L30–30](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/cloud/use-dify/workspace/tools.mdx#L30-L30)；`cloud/use-dify/workspace/tools#c1` / `cloud/use-dify/workspace/tools#p1`。

     > 粘贴规范、从 URL 导入，或从提供的示例开始，Dify 会自动生成工具接口。

2. **vital**：画布中通过添加节点>工具选择具体操作。
   - [self-host/use-dify/nodes/tools L15–15](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/tools.mdx#L15-L15)；`self-host/use-dify/nodes/tools#c0` / `self-host/use-dify/nodes/tools#p0`。

     > 1. 在画布上，点击 **添加节点** > **工具**，然后从可用工具中选择一个操作。

3. **vital**：需认证的工具可在节点选择现有凭证或创建新凭证。
   - [self-host/use-dify/nodes/tools L17–17](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/tools.mdx#L17-L17)；`self-host/use-dify/nodes/tools#c0` / `self-host/use-dify/nodes/tools#p0`。

     > 2. 可选：如果工具需要认证，选择已有凭证或创建新凭证。

4. **vital**：默认凭证在集成>工具>工具插件中修改。
   - [self-host/use-dify/nodes/tools L20–20](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/nodes/tools.mdx#L20-L20)；`self-host/use-dify/nodes/tools#c0` / `self-host/use-dify/nodes/tools#p0`。

     > 要更改默认凭证，前往 **集成** > **工具** > **工具插件**。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 33,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 4,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev083：自建拆子域后登录失效，要改哪两个Cookie变量？换域名后401看哪个控制台跨域项，域名共享有何边界？

参考答案：拆分子域后可检查COOKIE_DOMAIN是否为共享顶级域名，并把NEXT_PUBLIC_COOKIE_DOMAIN设为1，然后重启。更换域名后的401可检查控制台CORS变量CONSOLE_CORS_ALLOW_ORIGINS。Cookie不能跨不同可注册域名共享。这些是对应故障的排查方向，不代表唯一病因。

版本：self_host；预期行为：answered；最可能失败：忽略条件或套用邻近说明。。

1. **vital**：COOKIE_DOMAIN应设为前后端共享的顶级域名。
   - [self-host/deploy/quick-start/faqs L75–75](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/quick-start/faqs.mdx#L75-L75)；`self-host/deploy/quick-start/faqs#c5` / `self-host/deploy/quick-start/faqs#p4`。

     > - **`COOKIE_DOMAIN`**：设为前后端共享的顶级域名（例如 `example.com`），前导点可省略。

2. **vital**：NEXT_PUBLIC_COOKIE_DOMAIN应设为1以启用跨子域Cookie。
   - [self-host/deploy/quick-start/faqs L76–76](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/quick-start/faqs.mdx#L76-L76)；`self-host/deploy/quick-start/faqs#c5` / `self-host/deploy/quick-start/faqs#p4`。

     > - **`NEXT_PUBLIC_COOKIE_DOMAIN`**：设为 `1`，启用前端的跨子域名 Cookie。

3. **vital**：更换域名后401可检查CONSOLE_CORS_ALLOW_ORIGINS。
   - [self-host/deploy/troubleshooting/common-issues L23–23](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/common-issues.mdx#L23-L23)；`self-host/deploy/troubleshooting/common-issues#c1` / `self-host/deploy/troubleshooting/common-issues#p1`。

     > 这通常发生在更改域名之后。请更新以下环境变量：

   - [self-host/deploy/troubleshooting/common-issues L25–25](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/common-issues.mdx#L25-L25)；`self-host/deploy/troubleshooting/common-issues#c1` / `self-host/deploy/troubleshooting/common-issues#p1`。

     > - `CONSOLE_CORS_ALLOW_ORIGINS` - 控制台 CORS 策略

4. **vital**：Cookie不能跨不同可注册域名共享。
   - [self-host/deploy/quick-start/faqs L83–83](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/quick-start/faqs.mdx#L83-L83)；`self-host/deploy/quick-start/faqs#c6` / `self-host/deploy/quick-start/faqs#p4`。

     > Cookie 无法跨顶级域名共享，因此前端和后端必须位于同一可注册域名下。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 51,
    "at_most_40": false,
    "at_most_80": true,
    "vital_count": 4,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev084：外置Weaviate接v4客户端前要升到哪版、通哪个端口？Dify1.11后Worker迁移加什么选项，如何验收？

参考答案：服务端至少需要1.27.0，外置连接须能访问gRPC端口50051。Dify1.11.0及以后在Worker运行迁移脚本时使用uv run --no-cache。完成后在Dify界面针对迁移后的知识库测试检索功能。

版本：self_host；预期行为：answered；最可能失败：把v4客户端升级和逐小版本服务器阶梯混淆；不考dev026备份cp-a/Aggregate/回滚事实。。

1. **vital**：Weaviate v4客户端需要服务端1.27.0或更高版本。
   - [self-host/deploy/troubleshooting/weaviate-v4-migration L18–18](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L18-L18)；`self-host/deploy/troubleshooting/weaviate-v4-migration#c1` / `self-host/deploy/troubleshooting/weaviate-v4-migration#p1`。

     > **破坏性变更**：新的 weaviate-client v4 与 1.27.0 以下的 Weaviate 服务器版本不向后兼容。如果你正在运行 1.19.0 或更旧版本的自部署 Weaviate 实例，则必须在升级 Dify 之前升级 Weaviate 服务器。

2. **vital**：外置Weaviate须确保gRPC端口50051可达。
   - [self-host/deploy/troubleshooting/weaviate-v4-migration L91–91](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L91-L91)；`self-host/deploy/troubleshooting/weaviate-v4-migration#c7` / `self-host/deploy/troubleshooting/weaviate-v4-migration#p6`。

     > - 如果使用外部 Weaviate，确认 gRPC 端口 (50051) 可访问

3. **vital**：Dify1.11.0及之后用uv run --no-cache运行迁移脚本。
   - [self-host/deploy/troubleshooting/weaviate-v4-migration L300–300](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L300-L300)；`self-host/deploy/troubleshooting/weaviate-v4-migration#c22` / `self-host/deploy/troubleshooting/weaviate-v4-migration#p10`。

     > # 运行迁移脚本（Dify 1.11.0+ 请使用 --no-cache）

   - [self-host/deploy/troubleshooting/weaviate-v4-migration L301–301](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L301-L301)；`self-host/deploy/troubleshooting/weaviate-v4-migration#c22` / `self-host/deploy/troubleshooting/weaviate-v4-migration#p10`。

     > uv run --no-cache /app/api/storage/migrate_weaviate_collections.py

4. **vital**：迁移后应在Dify界面测试迁移知识库的检索功能。
   - [self-host/deploy/troubleshooting/weaviate-v4-migration L319–319](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/deploy/troubleshooting/weaviate-v4-migration.mdx#L319-L319)；`self-host/deploy/troubleshooting/weaviate-v4-migration#c23` / `self-host/deploy/troubleshooting/weaviate-v4-migration#p10`。

     > 4. **在 UI 中验证**：打开 Dify，针对迁移后的知识库测试检索功能。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 57,
    "at_most_40": false,
    "at_most_80": true,
    "vital_count": 4,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。",
    "cleaned_characters": 16351,
    "necessary_parent_ids": [
      "self-host/deploy/troubleshooting/weaviate-v4-migration#p1",
      "self-host/deploy/troubleshooting/weaviate-v4-migration#p10",
      "self-host/deploy/troubleshooting/weaviate-v4-migration#p6"
    ],
    "within_current_judge_first_12000_chars": true
  }
}
```

</details>


## dev085：Agent构建时放弃、运行时新增文件、重开对话和恢复旧版，分别怎样影响文件或构建笔记？

参考答案：放弃构建会丢弃本次对长期文件的改动；发布后的运行中新增内容均为临时，不会改变Agent本身。每次新对话会重新读取构建笔记；恢复旧版时，沙箱长期文件也恢复到该版本。

版本：self_host；预期行为：answered；最可能失败：把构建阶段永久状态与发布后运行临时状态混淆。。

1. **vital**：放弃构建会丢弃本轮对长期文件的改动。
   - [self-host/use-dify/build/new-agent/build L137–137](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/build.mdx#L137-L137)；`self-host/use-dify/build/new-agent/build#c11` / `self-host/use-dify/build/new-agent/build#p9`。

     > **放弃** 会丢弃本次构建对话中的一切：对配置以及 [**文件系统**](#文件系统) 中长期文件的所有更改。

2. **vital**：发布后的运行中新添加内容都是临时的。
   - [self-host/use-dify/build/new-agent/build L150–150](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/build.mdx#L150-L150)；`self-host/use-dify/build/new-agent/build#c14` / `self-host/use-dify/build/new-agent/build#p10`。

     > 在发布后的运行中，Agent 添加的任何内容都是临时的，因此运行中发生的一切都不会改变 Agent 本身。

3. **vital**：每次新对话开始时Agent都会重新读取构建笔记。
   - [self-host/use-dify/build/new-agent/build L156–156](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/build.mdx#L156-L156)；`self-host/use-dify/build/new-agent/build#c15` / `self-host/use-dify/build/new-agent/build#p11`。

     > 这份笔记会随 Agent 的配置一起保存。每次新对话开始时，Agent 都会重新读取笔记，将它与你的 **提示词** 组合成自己的指令。

4. **vital**：恢复Agent版本时，沙箱长期文件也恢复到该版本。
   - [self-host/use-dify/build/new-agent/build L179–179](https://github.com/langgenius/dify-docs/blob/c80a31868611b673bd77725a6310c685068a585e/zh/self-host/use-dify/build/new-agent/build.mdx#L179-L179)；`self-host/use-dify/build/new-agent/build#c17` / `self-host/use-dify/build/new-agent/build#p12`。

     > 恢复版本时，Agent 沙箱中的长期文件也会一并恢复到该版本。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 43,
    "at_most_40": false,
    "at_most_80": true,
    "vital_count": 4,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。",
    "cleaned_characters": 6225,
    "necessary_parent_ids": [
      "self-host/use-dify/build/new-agent/build#p10",
      "self-host/use-dify/build/new-agent/build#p11",
      "self-host/use-dify/build/new-agent/build#p12",
      "self-host/use-dify/build/new-agent/build#p9"
    ],
    "within_current_judge_first_12000_chars": true
  }
}
```

</details>


## dev086：社区集成报漏洞后，官方承诺多久响应、多久发补丁？

参考答案：冻结资料没有给出第三方社区集成漏洞的官方首次响应时限或补丁交付期限，无法据此报时长。这不等于官方或维护方不会处理漏洞，应查具体维护方的安全政策或支持约定。

版本：未限定；预期行为：refused；最可能失败：忽略条件或套用邻近说明。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 24,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 0,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev087：教我保留事件触发器，把同一流程直接发布成MCP服务。

参考答案：不能按这个前提操作。只有以用户输入启动的工作流才能发布为MCP；用户输入和触发器在同一画布互斥。若要改成这种发布方式，需切换开始节点，不能保留原触发器与用户输入并存。

版本：self_host；预期行为：corrects_premise；最可能失败：直接给出发布步骤，漏掉启动方式限制。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 26,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 0,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev088：我用LangGraph搭RAG，给它的PostgreSQL业务库写一套Patroni跨机房故障转移配置。

参考答案：这属于LangGraph RAG服务的PostgreSQL/Patroni高可用运维，超出冻结Dify文档范围；不能据库内资料提供完整配置，应说明范围并建议查相应系统的部署资料。

版本：未限定；预期行为：refused；最可能失败：看到RAG与PostgreSQL就误认为库内有对应运维方案，编造Patroni完整配置。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 52,
    "at_most_40": false,
    "at_most_80": true,
    "vital_count": 0,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>

备注：最终独立审题后主agent按冻结原文修正；具体发现、原版hash和闭环见semantic-review.json及blueprint-amendments.json。


## dev089：别人导出的DSL，导入就一定兼容吗？

参考答案：需要确认导入目标是Dify Cloud还是社区自部署。冻结Cloud资料说明平台始终使用最新DSL版本，导入文件兼容；自部署导入由较新Dify导出的DSL前可能需要升级。可先澄清目标部署和相对版本，也可给上述条件答案。

版本：未限定；预期行为：clarified_or_conditional_answer；最可能失败：把平台持续更新与某个旧的社区实例当作相同前提。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "counterpart_docs": [
    "cloud/use-dify/workspace/app-management",
    "self-host/use-dify/workspace/app-management"
  ],
  "quantitative_evidence": {
    "question_characters": 18,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 0,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>


## dev090：想把外部系统的资料接进来，怎么配？

参考答案：先确认外部系统是已有知识检索服务，还是按当前输入返回资料的业务API。前者连接外部知识库API，数据和检索逻辑仍由外部维护，Dify只有检索权限；后者用外部数据工具，把应用变量或对话输入交给API，返回字符串补进提示词。

版本：未限定；预期行为：clarified_or_conditional_answer；最可能失败：忽略条件或套用邻近说明。。

本题不设可答事实得分点；按拒答/纠正/澄清行为审查。

<details><summary>边界、干扰与难度证据</summary>

```json
{
  "quantitative_evidence": {
    "question_characters": 17,
    "at_most_40": true,
    "at_most_80": true,
    "vital_count": 0,
    "formal_nugget_atomicity": "原子性及题干对齐已自读；仍待fresh独立审题，不因字段齐全判pass。"
  }
}
```

</details>
