# AGENTS.md

grounded_rag（第二版）：以索尼银行住宅贷款客服为背景的坐席 Copilot 概念验证——LangGraph 编排「只读查数工具 + 日文规程 RAG」，坐席与客户双泳道，对外提供 REST API（SSE）。代码主要由 AI 编写，本文件对所有 agent（Codex、Claude Code、Cursor）生效。

第一版（Dify 中文文档问答）已整体归档：文档在 `harness/archive/v1-dify-docs/`，代码状态在 git 标签 `v1-dify-docs`。**现有代码是第一版的，正在按 `PLANS.md` 逐阶段改造**；看到与 Dify 文档、`edition`、jieba 相关的代码不要惊讶，按阶段文件处理。

## 文档地图

根目录放稳定的规则和目标，`harness/` 放随阶段变化的东西。**计划、决策、证据分开写**：build 里的计划不能当作已完成的证据，进度只认 build-log。

| 想知道 | 读什么 |
|---|---|
| 现在做到哪了、下一步、阻塞 | `harness/build-log.md` 的「当前状态」（每次开工先读） |
| 做什么、不做什么、成功条件、合规边界 | `GOALS.md` |
| 怎么做：现状与差距、数据来源、设计、评测口径、阶段顺序 | `PLANS.md` |
| 某个阶段的范围、任务、验收标准（文中的 Spec 即这些文件） | `harness/build/phase-NN-*.md`（第二版从 30 编号到 38） |
| 某件事为什么这样定、本机环境和已知的坑 | `harness/context/phase-NN-*-context.md`（已定的事不要重新讨论） |
| 写或改代码、测试、接口、表结构 | `CODING-STANDARDS.md` |
| 开始阶段、提交、自查、Review | `WORKFLOW.md`；可复用的任务指令见 `PROMPTS.md` |
| 第一版的全部计划、日志、评测记录 | `harness/archive/v1-dify-docs/`（只读，不再追加） |
| Review 结果 | `harness/code_review/` |

`CODING-STANDARDS.md`、`WORKFLOW.md`、`PROMPTS.md` 是第一版写的，规则仍然有效，里面的例子可能还是 Dify 场景；阶段 38 统一更新。

## 常用命令（在 `backend/` 目录下执行）

```bash
uv sync
uv run poe check      # 格式 + lint + 分层 + 类型 + 单元测试，提交前必须通过
uv run poe test-int   # 集成测试，先 docker compose up -d
uv run poe eval-dev   # 开发集评测，花钱，Spec 要求时才跑
```

## 长程任务模式

- 一律用中文回复、写文档和日志。知识库、提示词、评测题、模型回答用日文。
- 不再等作者批准：Spec 可以自己细化、自己标「已批准」，一个阶段做完直接做下一个，直到最后。
- 下面「先问」那一栏改为：做了就在阶段文件的「记录」和 build-log 里写明原因，不再停下来等回复。
- **交接**：每完成一个任务就追加 `harness/build-log.md` 并更新其「当前状态」（做到哪、剩什么、阻塞项），提交；用量快到上限或要停下时，先把它写完整再停，方便换一个模型接着做（模板见 `PROMPTS.md` §5）。
- 只有缺少**外部输入**才算阻塞（作者保存公开页面、作者出评测题、人工校准、Dify 界面操作、API 密钥）：先把不依赖它的部分做完，再在日志和最终报告里集中说明。

## 权限

| 直接做 | 先问（长程模式下改为：做了要写明原因） | 禁止 |
|---|---|---|
| 在当前阶段范围内改 `backend/`、`mock_core/`、`docker-compose.yml`、本阶段的 `harness/build/` 文件、`harness/context/`、`harness/build-log.md`、`harness/code_review/` | 新增或升级依赖（`PLANS.md` §8 已列出预期的） | 自动批量抓取 sonybank.jp，或用任何方式绕过它的访问限制 |
| 运行 `poe` 任务、本地 docker compose、写 `.cache/` 和 `data/` | 改数据表、改 REST 的字段 | 提交 `.env`、密钥、`data/`、`.cache/`、公开页面原文、参考方案原文 |
| 每日预算内真实调用 DeepSeek（¥10/天） | 改本文件、`GOALS.md`、`PLANS.md`、`CODING-STANDARDS.md`、`WORKFLOW.md`、CI、`pyproject.toml` 的检查配置 | 读取测试集；改评分规则、评审 Prompt |
| 在当天分支（`<日期>-<两个英文单词>`，见 WORKFLOW.md §3）提交 | 删除不是本任务创建的文件（阶段文件里点名要删的除外） | 为了通过检查而加 `noqa` / `type: ignore` / `skip`，或降低门槛 |
| | 推送、开 PR（仓库是公开的，推送前按阶段 38 的检查项确认） | 推 main、`push --force`、合并自己的 PR |
| | | 改预算配置或绕过用量统计 |
| | | 估算或编造没有实测的指标（坐席采纳率、AHT、办结率等一律写「未测」） |
| | | 把合成数据写成真实数据；合成内容必须带 `synthetic` 标记 |

## 完成的定义

1. 阶段文件里本任务的验收标准逐条满足，并给出证据（命令 + 输出摘要）。没有运行过的命令不算通过。
2. `uv run poe check` 通过；动了数据库或外部服务的，`poe test-int` 也通过。
3. 改了接口、配置或行为，同步更新文档和 `.env.example`。
4. 阶段文件里的任务已勾选。
5. `harness/build-log.md` 已追加：做了什么、验证命令与结果；新的决定写进 `harness/context/`。

## 什么时候停下

- 同一检查修了 3 次仍失败；
- Spec 有歧义，或与代码事实冲突，且无法按「记录原因后继续」处理；
- 当日 DeepSeek 预算用完；
- 需要作者提供外部输入，且不依赖它的部分已经做完。

停下时在 Spec 的「阻塞」写清：现象、试过什么、需要谁决定。然后结束本任务，不跳去做别的任务。
