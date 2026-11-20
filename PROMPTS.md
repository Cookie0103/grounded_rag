# 提示词模板

> 给 Claude / Codex / Cursor 复用的任务指令，开新会话时整段粘贴即可。每条只写「怎么做」，目标和计划不在这里重复，只引用 [GOALS.md](GOALS.md)、[PLANS.md](PLANS.md)、[harness/build/](harness/build/)。
> 运行时代码用的提示词在 `backend/app/prompts/` 和 `backend/eval/prompts/`，与本文件无关。

## 1. 开始一个阶段

```text
先读 AGENTS.md、harness/build-log.md 的「当前状态」，再读 harness/build/phase-NN-*.md 和对应的 harness/context/phase-NN-*-context.md。
先说明这个阶段的范围、依赖和假设。普通模式按 WORKFLOW.md 确认后开工。长程任务按 AGENTS.md 自行细化已授权阶段并继续推进。
开始时在 harness/context/ 建（或续写）本阶段的 context 文件，只记会改变后续范围、决策或验证方式的东西，不记过程。
```

## 2. 执行并验收一个阶段

```text
按 harness/build/phase-NN-*.md 的任务顺序做：先写失败的测试，再写实现，最后只在任务范围内整理。
每个任务做完：在 backend/ 下跑 uv run poe check，把命令和输出摘要追加到 harness/build-log.md 的「活动记录」（只追加，不改旧条目）。
阶段验收：对照该文件的验收标准逐条给出证据（命令 + 输出）；没有运行过的命令不算通过。全部满足才把 build-log 的阶段状态改为「完成」。
遇到阻塞（见 AGENTS.md「什么时候停下」）就写进 build-log 并停止。
```

## 3. 静态检查与测试（review 的基础）

这些问题都由工具检查，不要靠人眼看：

| 问题 | 谁负责 | 命令（在 `backend/` 下） |
|---|---|---|
| 引用了不存在的库、import 了没用的库、变量没用 | ruff | `uv run poe lint` |
| 违反分层依赖（例如 core 反向 import api） | import-linter | `uv run poe lint`（含 `lint-imports`） |
| 类型不对（要 int 却给了 str）、缺类型标注 | mypy --strict | `uv run poe typecheck` |
| 逻辑错误 | pytest | `uv run poe check` 含单元测试；`uv run poe test-int` 跑集成测试 |

`uv run poe check` 一条命令包含以上全部。**不允许**为了通过检查加 `noqa` / `type: ignore` / `skip`，或降低门槛。

## 4. Code review

```text
用一个新会话，只看 diff（git diff <前一天的分支>...HEAD）和对应的 harness/build/phase-NN-*.md，不要读实现过程的聊天记录。
先跑 uv run poe check，把输出贴出来；失败就先报失败，不继续。
然后对照 WORKFLOW.md §4.3 的表（功能、设计、复杂度、测试、命名与注释、文档）逐项审。
只报影响正确性或违背计划的问题；风格偏好记下即可。
每条写：文件:行、问题、复现方式或失败场景、建议。
把结果写成 harness/code_review/<日期>-phase-NN-<审查者>.md（审查者填 claude / codex）。不要直接改代码，除非我说「顺手修掉」。
```

## 5. 交接（Claude ↔ Codex 互相接手）

```text
停下前更新 harness/build-log.md 顶部的「当前状态」：做到哪、剩什么、阻塞项、下一步命令。
未完成的任务在对应 harness/build/phase-NN-*.md 里保持未勾选；做出的新决定写进 harness/context/。
在当天分支提交交接，推送按 AGENTS.md 的权限处理。用量快到上限（95% 以上）也先完成本地交接再停。
接手的人：先读 AGENTS.md，再读 build-log 的「当前状态」。
```

## 6. 住宅贷款规程出题

作者从本机出题包 `.cache/policy-question-pack.zip` 准备日文开发题与封存题，流程、出题与审题模板均见[作者评测手册](docs/eval/copilot-author.md)。
