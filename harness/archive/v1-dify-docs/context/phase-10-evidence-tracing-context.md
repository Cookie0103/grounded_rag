# 阶段 10 决策：实验过程记录

- 2026-10-18：作者要求保存每轮查询、返回 chunk、缺失信息和实际生成上下文。复用 `Step`、`RetrievalResult` 及 `traces.steps` JSONB，只新增可选 `StepDetails`，不新建数据库表、日志器或 chunk 类型。
- 评测复用 `SystemAnswer.to_json/from_json` 与现有 JSONL 写入器保存步骤；不改题集、评分规则、评审 Prompt 或检索决策。
- `generate.details.context` 是实际传入生成提示词的资料字符串；原 `contexts` 保持父块列表语义，避免静默改变现有评测归因。
- 记录检索器返回的 top-k 候选，不扩大到粗召回全部候选；每个结果自带 query，步骤顺序表示轮次。未执行模型生成时不伪造 context。
- REST/SSE 步骤详情和 trace 共用结构；缓存返回原过程，服务降级保留已完成的编排步骤。旧评测缓存兼容读取但不补造历史。
- 本机数据库配置格式错误；本次测试仅临时覆盖容器的本地连接地址，作者启动服务前仍需修正 `.env` 的 `DATABASE_URL`。
- 已读公开 Notion 的进度与评测第 7 节：100 题、70/30 划分及先事实后问题与仓库一致；Notion 的旧文档路径已由 harness/PROMPTS 取代，Gemini 主评/Claude 复评仍是计划，当前评测入口只支持 Claude/DeepSeek。
