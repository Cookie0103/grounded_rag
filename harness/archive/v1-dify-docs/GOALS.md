# 目标

> 只写「要做成什么样、做到什么算成功、不做什么」。怎么做见 [PLANS.md](PLANS.md)，做到哪了见 [harness/build-log.md](harness/build-log.md)。

## 一句话

Dify 官方中文文档的问答后端（RAG）：按问题复杂度选择检索流程，答案带引用，文档里没有就拒答。对外提供 REST API 和 MCP。

这是求职作品集：评测的故事要能让实习生讲清楚，文档保持简洁。

## 要解决的 7 个问题

1. 文档太长，关键信息被淹没（环境变量大全单篇约 126KB）
2. 用户口语和文档术语对不上（“把资料喂给机器人” vs “知识库”）
3. 一个问题要跨多篇文档才能答
4. 简单问题不该走重流程
5. 检索错了还自信地答
6. 版本差异（云版、自部署版同名页内容不同）
7. 问题含糊、多轮追问指代不明

## 成功条件

| 条件 | 怎么算 |
|---|---|
| 评测有说服力 | 100 道题（开发集 70 / 测试集 30）上报 4 个核心指标：可信得分（CRAG 口径）、关键点召回（nugget）、Recall@5、P95 延迟与单题成本；指标定义见 [PLANS.md §6](PLANS.md) |
| 消融如实 | 无检索 → naive RAG → 混合检索与精排 → 改写与路由 → 校验与拒答，每行报 4 个指标；差距小于置信区间时不宣称提升，如实记录“没用”的项 |
| 可复现 | 固定语料 commit；克隆仓库后按 README 一条条命令能跑通；测试集只在最后跑一次 |
| 可调用 | MCP 能被 Claude Code 调用；关掉精排仍能答；有 QPS 与 P95 |
| 可复盘 | 任意一次回答可按 `trace_id` 复盘每一步 |

## 范围

- 语料：Dify 中文文档 182 篇（自部署版 137、云版 45），来源 [langgenius/dify-docs `zh/`](https://github.com/langgenius/dify-docs/tree/main/zh)，固定 commit，不入库。
- 接口：REST（`/chat` 含 SSE、`/retrieve`、`/feedback`、`/health`）+ MCP（`search_docs`、`ask_docs`）。
- 先做中文版；日文版只保留可行性。

## 非目标

前端界面、登录与多租户、SDK、模型微调、生产级高可用部署、Agent runtime / 多智能体 / 多模态。

## 约束

- 嵌入和精排在本机 GPU（RTX 5070 Ti 16GB）运行；只有 DeepSeek 走 API，agent 每天不超过 ¥10，作者手动测试不限。
- 评测分工：Gemini 出题与主评，Claude 审题与复评，DeepSeek 是被测方；开发的 agent 看不到测试集。
- 许可：代码 MIT；Dify 文档 CC BY 4.0（不入库，README 注明来源）；评测集改编自 Dify 文档，按 CC BY 4.0 发布并注明来源。
