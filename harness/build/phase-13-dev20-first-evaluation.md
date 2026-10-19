# 阶段 13：首批 20 题真实试评与逐轮归档

状态：进行中（2026-10-19；作者已授权运行，按长程模式批准）

## 需求

- 运行现有 dev20 草案，评测实际 ChatService（与 CLI/API 共用，包含后处理、缓存和降级标志）；每题独立，无历史会话。
- 复用已有 Question、run_system、服务工厂、Step、预算及总分函数；由当前 Codex 会话逐题对照原文及实际上下文给评审标签，产出五项计数和具体理由。不把系统 grade/verify 当真值。
- 每轮归档至 docs/eval/results/runs/<run_id>/，保存题集快照、完整过程、评审依据、版本和单轮报告。作者要求暂不创建跨轮次总览，等最终 70 dev / 30 test 完成再做。

## 非目标

- 不改题集、金标、原评分代码、评审 Prompt、检索参数、运行时 Prompt 或模型；不读封存测试题，不运行额外消融。
- 不接入新的 OpenAI API 或假称独立 API 已按 high 执行；当前会话评审记录为 agent 辅助诊断，high 为作者选择，界面实际档位不伪造。
- 不推送或发布静态站点，不创建 docs/eval/results/index.html。

## 方案与验收

| 标准 | 证据 |
|---|---|
| AC1 20题有真实结果或明确失败，保留每题完整步骤和独立trace映射 | 复用 run_system；traces.jsonl、answers.jsonl、manifest.json |
| AC2 逐题 E/A/F/C/B 有分子分母、证据与理由；沿用旧总分函数 | reviews.jsonl、results.jsonl、summary.json；人工可读报告 |
| AC3 云端实际接收，保存服务端核验结果 | 依据本地trace映射读取 Langfuse；未确认项不假报成功 |
| AC4 单轮材料可长期独立读取，旧轮次不覆盖，总览延后 | 单轮 report.html、README.md、题集/标准快照与sha256；本地页面检查 |
| AC5 不改受保护文件和预算，代码检查通过 | git diff、poe check；真实用量经原 BudgetLedger 记账 |

## 任务

- [x] T1 最小独立运行入口、快照与安全配置清单。
- [ ] T2 实际运行20题，核验本地与云端过程。
- [ ] T3 逐题审阅、复用总分计算、单轮报告与分数云端核验。
- [ ] T4 检查、记录局限、提交与交接。

## 记录

- 原 eval FullSystem 直接调 pipeline，不含 ChatService 后处理；本轮明确使用 full-service 配置，后续比较需复用同一范围。原 .cache/eval/<system> 缓存不覆盖、不混用。
- 已有设置每日上限10元，当前原账本约0.10元；不改预算值、不绕过记账。单并发避免GPU排队混淆首轮延迟与预算竞争；首题冷启动单列。
- 本轮只新增试评与归档入口，不修改既有评分程序；E/F/C 的标签由 agent 核验，汇总是确定性计算，不声称通用自动评审已实现或已人工校准。
- 作者本轮明确要求将原始结果另存持久归档，覆盖此前只将原始输出放.cache的默认约定；运行缓存仍留.cache，最终快照存入指定results目录。
