# 阶段 11 决策：云端观测与本机核验

- 2026-10-19：作者明确选择先接 Langfuse 免费托管，定稿后静态归档。新增官方 Python SDK v5（锁定 5.0.2），无升级原有依赖；凭据统一进 Settings，沿用根目录 `.env`。
- 复用 Step / RetrievalResult / TraceRecord。粗召回记录融合后全部候选及两路排名，精排记录完整输入候选的打分排序，最终 top-k 与检索策略保持不变。结构化查询、合并父块、各次原始生成输出和后处理随原 JSONB / JSONL 保存，无数据库迁移。
- API、终端和 MCP ask_docs 共用 ChatService。云端根观测覆盖请求，节点完成后发送事件，实际节点耗时保存在 ms，避免把补发时刻当作真实节点运行时间。评测通过包装已有 System 发送原题、金标文档、期望要点及答案，不改评分；当前评测步骤在该题作答完成后发送。
- 回答缓存只记录本次命中事件，费用为零，不回放上次生成过程；检索缓存另加 cached 标记，其子阶段耗时属于原始检索。
- 未配置密钥完全停用 SDK；云端初始化、记录、队列关闭的常见异常只记类型，不影响问答。后台上传不等于服务端已接收，真实云端必须由上传后读取或页面记录验证。
- 本机现有数据库容器端口为 15432，作者的 DATABASE_URL 已修为合法地址但误写 5432。连接原容器并读取语料成功后，仅把 `.env` 的数据库端口与 DB_PORT 对齐为 15432；未改用户名、密码、API key 或预算配置。
- 已实际加载 Qwen3 / BGE 两套嵌入和精排，使用本地权重离线执行；两套库内向量完整。DeepSeek 真实调用与一次完整单跳问答通过。证据见 build-log 与 `.cache/runtime-audit-2026-10-19.json`，不据此宣称正式评测性能。
- 第一批正式 20 题仍计入开发集 70；按现有题型配额近似覆盖 7 事实 / 3 归纳 / 4 跨篇 / 2 版本 / 4 不可回答。闲聊另做两句手工检查，不硬塞进文档问答评分；题型与路由是不同维度，rewrite 不是路由。
- 长期展示选 GitHub Pages，作者熟悉且 HTML/JSON 与平台无关。HF Static Space 无需为此次迁移特别采用。正式测试封存至验收结束；当前未创建或发布静态站点。

官方资料（本轮核对）：
- [Langfuse 价格](https://langfuse.com/pricing)：Hobby 每月 50k units、30 天历史访问，无须信用卡；开源许可与托管服务是两回事。
- [Langfuse Python SDK](https://langfuse.com/docs/observability/sdk/python/overview)、[API 参考](https://python.reference.langfuse.com/langfuse)：使用已安装版本签名核对接口，并通过真实 SDK + 内存导出器离线验证父子观测。
- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)、[HF Static HTML Space](https://huggingface.co/docs/hub/spaces-sdks-static)：均支持静态文件托管，选择前者。
