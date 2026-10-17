# 开发流程

## 1. 总览

每个里程碑都按 **Spec → Plan → Implement → Verify** 推进。
一句话就能说清的小改动（错字、调一个阈值）不写 Spec，直接改，但仍要过 Verify。

| 阶段 | 产出 | 谁做 | 人工关口 |
|---|---|---|---|
| Spec | `harness/build/phase-NN-<名称>.md` 的「需求」部分（M0～M9 即 phase-00～09） | agent 起草 | **作者批准后才能进入 Plan** |
| Plan | 同一文件的「方案」和「任务」部分 | agent | 作者确认任务拆分 |
| Implement | 代码与测试；每个任务一组提交，放在当天的分支上 | agent | — |
| Verify | `poe check`、验收证据、自审、当天的 PR | agent | **作者合并 PR** |

实际做了什么、测试结果、阻塞，追加到 `harness/build-log.md` 的「活动记录」（只追加；进度以它为准）。
重要决定记进 `harness/context/phase-NN-*-context.md`。里程碑完成时，在该阶段文件的「记录」里写一段总结：做了什么、指标变化（链接报告）、遗留问题。
`harness/archive/` 是历史归档（2026-10-16 的完整日志和调研笔记），不再追加。

## 2. Spec 与 Plan

一个里程碑一个文件。不确定的地方写进「待确认」，不要猜。

```markdown
# Mx：标题

状态：草稿 / 已批准 / 进行中 / 阻塞 / 完成

## 需求
### 目标        1～3 条，都能被验证
### 非目标      这次明确不做的事
### 接口与数据  本里程碑新增或修改的 API、MCP 工具、表、配置项
### 验收标准    编号 AC1、AC2…，每条写清怎么验证（命令或测试名）
### 待确认      agent 拿不准、需要作者决定的问题

## 方案
关键设计与选型理由，不超过一屏；列出涉及的模块。

## 任务
- [ ] T1 名称：对应 AC1；验证命令 …

## 阻塞
## 记录          偏离 Spec 的地方及原因；任务外发现的问题
```

任务粒度：半天左右能完成并验证，非测试代码大约 300 行以内。

## 3. Implement

- **按天开分支**：分支名为 `<日期>-<两个英文单词>`，例如 `2026-10-16-framework-build`、`2026-10-17-ingest-pipeline`，看名字就知道当天在做什么。
  - 每天的新分支从**前一天的分支**创建，不等前一天的 PR 合并；第一天从 `main` 创建。
  - 当天所有提交都放在当天分支上；同一天开了多个会话也用同一个分支。
  - 收工前推送，并开一个 PR 合并到 `main`，标题为 `<日期> <当天做了什么>`；PR 按日期顺序合并。
  - 因为分支是一天接一天叠起来的，合并时**用 merge commit，不用 squash**，否则后一天的 PR 会重复出现前一天的提交并产生冲突。
- 每完成一个任务至少提交一次；提交说明里写上任务编号，例如 `feat(M1-T3): 父子块切分`。
- 按红 → 绿 → 重构推进：先写失败的测试，再写刚好能通过的实现，最后只在任务范围内整理代码。
- 重构、格式调整和功能改动分开提交。
- 提交说明用 Conventional Commits：`feat:`、`fix:`、`test:`、`refactor:`、`docs:`、`chore:`。
- 任务范围外发现的问题不在这次修，记到 Spec 的「记录」。
- 收工前更新 `harness/build-log.md`：做了什么、验证命令与结果、遇到的困难和解决方法；查阅的资料写进对应的 context 文件。没写日志的一天不算完成。

## 4. Verify

### 4.1 自动检查

| 命令（在 `backend/` 下执行） | 内容 |
|---|---|
| `poe fmt` | `ruff format .` 加 `ruff check --fix .` |
| `poe check` | `ruff format --check .`、`ruff check .`、`lint-imports`、`mypy`、`pytest -m "not integration" --cov` |
| `poe test-int` | `pytest -m integration`，使用独立的测试库 `grounded_rag_test`，由夹具自动建库并迁移 |
| `poe eval-dev` | 开发集评测，输出报告，不进 CI |

CI（`.github/workflows/ci.yml`，push 到 main 或提 PR 时触发）：

- **check**：`uv sync --locked` → `poe check`（working-directory 为 `backend`）
- **integration**：用 `pgvector/pgvector:pg16` service container 跑 `poe test-int`
- 不进 CI 的：评测、GPU 推理、真实 DeepSeek 调用

其他自动化：

- pre-commit：ruff、`detect-private-key`、`check-added-large-files`
- main 分支保护：CI 全绿，并由作者合并（merge commit，见 §3）
- agent 侧硬限制：Claude Code 的 `.claude/settings.json` 禁止编辑 `backend/eval/data/**`；Codex 用 `workspace-write` 沙箱

### 4.2 PR 说明模板

```markdown
## 做了什么
## 验收证据      AC 编号 → 运行的命令 → 结果摘要
## 偏离 Spec / 待确认
## 新增依赖或配置项（附理由）
```

### 4.3 评审

开当天的 PR 前，用一个新会话或另一个 agent（`/code-review`、Codex review）只看 diff 和阶段文件审一遍（提示词见 [PROMPTS.md §4](PROMPTS.md)），对照下表；审查结果写进 `harness/code_review/`：

| 看什么 | 问题 |
|---|---|
| 功能 | 是否满足 Spec 的验收标准？边界情况是否处理？ |
| 设计 | 放在正确的模块里了吗？有没有重复已有代码？ |
| 复杂度 | 有没有比需要的更复杂？有没有为“以后可能用”写的代码？ |
| 测试 | 代码错了，测试会不会真的失败？ |
| 命名与注释 | 名字是否说清用途？注释是否在解释“为什么”？ |
| 文档 | 接口、配置、命令变了，文档是否同步？ |

只修影响正确性或违背 Spec 的问题；风格偏好记下即可，不追，避免越改越复杂。
作者合并前看三样东西：PR 说明、验收证据、测试是否真的有效。

## 5. 预算

- agent 真实调用 DeepSeek 每天不超过 ¥10，由 `providers/` 统计并强制执行（见代码规范 §8）。
- 开发时优先用 `.cache/` 里的响应缓存和假实现；评测按 Spec 要求才跑。
- 作者手动测试不设上限。

## 6. 文档维护

- 每件事只在一处写，其他地方链接过去。
- 已定的决策一行一条记在 `harness/context/phase-NN-*-context.md`；推翻决策时改那一行，并写上日期和原因。
- 同类错误出现两次，就把教训写成规则（AGENTS.md）、检查配置或回归测试，不能只留在聊天记录里。
- 每个里程碑结束后检查 AGENTS.md，删掉 agent 已经不需要的规则。
