# M9：收尾

状态：完成（2026-10-16，验收证据见 [build-log](../build-log.md)）

> 这是计划和记录，不是完成证据；进度以 build-log 为准。

## 需求

1. README：是什么、流程图、快速开始（一键复现）、接口、评测命令、文档索引。
2. 评测运行手册：作者拿到密钥和题目后一步步该做什么；完整消融（5 行）和模型对比各有对应命令。
3. 最终报告模板（数字留空）。
4. 已知缺口清单：所有没验证的、要作者做的事。
5. 消融需要的系统入口：`no-retrieval`、`naive-rag`、`hybrid-rag`、`routed`（关掉证据评分和校验）、`full`。
6. 最后一次全量检查：`poe check`、`poe test-int`、`poe test-gpu`、CI。

### 非目标

- 真实的最终数字（要作者的题目、密钥和测试集）。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | README 里每条命令都对应存在的 poe 任务 / 文件 | 脚本检查 |
| AC2 | 消融的 5 行都有 `--system` 入口，`CHAT_MODEL=fake` 下都能跑通 | 命令输出 |
| AC3 | 全量检查通过，CI 绿 | |

## 任务

- [x] T1 README、运行手册、报告模板、已知缺口
- [x] T2 消融系统入口（`hybrid-rag`、`routed`）
- [x] T3 全量检查与收尾

## 记录

2026-10-16 完成。
- AC2：`ChatPipeline(grade=, verify=)` 开关 + `NaiveRagSystem(mode=, rerank=)`；`--system hybrid-rag|routed` 在 `CHAT_MODEL=fake` 下跑通。
- AC3：见 HANDOFF 的最终状态。
- 剩下的都是需要作者的事，见 [known-gaps.md](../../PLANS.md)。
