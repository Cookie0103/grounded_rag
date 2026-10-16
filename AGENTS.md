# AGENTS.md

grounded_rag：Dify 中文文档问答后端（RAG），对外提供 REST API 和 MCP。代码主要由 AI 编写，本文件对所有 agent（Codex、Claude Code、Cursor）生效。

## 按需阅读

| 什么时候 | 读什么 |
|---|---|
| 了解范围、架构、里程碑 | `docs/proposal-2026-10-15.md` |
| 写或改代码、测试、接口、表结构 | `docs/coding-standards.md` |
| 开始里程碑或任务、提交、自查 | `docs/workflow.md` |
| 当前在做什么 | `docs/specs/` 下状态为「进行中」的 Spec，以及最近一天的 `docs/implementation-log/` |
| 某件事为什么这样定 | `docs/decisions.md`（已定的事不要重新讨论） |

## 常用命令（M0 建立，在 `backend/` 目录下执行）

```bash
uv sync
uv run poe check      # 格式 + lint + 分层 + 类型 + 单元测试，提交前必须通过
uv run poe test-int   # 集成测试，先 docker compose up -d db
uv run poe eval-dev   # 开发集评测，花钱，Spec 要求时才跑
```

## 长程任务模式（作者 2026-10-16 起）

- 一律用中文回复、写文档和日志。
- 不再等作者批准：Spec 自己写、自己标「已批准」，一个里程碑做完直接做下一个，直到最后。
- 下面「先问」那一栏改为：做了就在 Spec「记录」和当天日志里写明原因，不再停下来等回复。
- 只有缺少**外部输入**才算阻塞（API 密钥、作者用 Gemini 出的评测题、需要真人评审的步骤）：先把不依赖它的部分做完，再在日志和最终报告里集中说明。

## 权限

| 直接做 | 先问（写进 Spec「待确认」或 PR 说明，等作者回复） | 禁止 |
|---|---|---|
| 在当前 Spec 范围内改 `backend/` 下的代码与测试、本任务的 Spec、当天的开发日志 | 新增或升级依赖 | 读取测试集；改 `backend/eval/data/`、评分规则、评审 Prompt |
| 运行 `poe` 任务、本地 docker compose、写 `.cache/` | 改数据表、改 REST / MCP 的字段 | 为了通过检查而加 `noqa` / `type: ignore` / `skip`，或降低门槛 |
| 每日预算内真实调用 DeepSeek（¥10/天，见规范 §8） | 改本文件、`docs/` 下的规范与计划、CI、`pyproject.toml` 的检查配置 | 提交 `.env`、密钥、`data/`、`.cache/` |
| 在当天分支（`<日期>-<两个英文单词>`，见 workflow §3）提交、推送、开 PR | 删除不是本任务创建的文件 | 推 main、`push --force`、合并自己的 PR |
| | | 改预算配置或绕过用量统计 |
| | | 改与当前任务无关的文件（发现问题记到 Spec「记录」） |

## 完成的定义

1. Spec 里本任务的验收标准逐条满足，并给出证据（命令 + 输出摘要）。没有运行过的命令不算通过。
2. `uv run poe check` 通过；动了数据库的，`poe test-int` 也通过。
3. 改了接口、配置或行为，同步更新文档和 `.env.example`。
4. Spec 中任务已勾选，PR 说明按 `docs/workflow.md` §4 填写。
5. 当天的开发日志已更新：`docs/implementation-log/<日期>/README.md`。

## 什么时候停下

- 同一检查修了 3 次仍失败；
- Spec 有歧义，或与代码事实冲突；
- 需要做「先问」里的事；
- 当日 DeepSeek 预算用完。

停下时在 Spec 的「阻塞」写清：现象、试过什么、需要谁决定。然后结束本任务，不跳去做别的任务。
