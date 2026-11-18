# 开发日志（build-log）

> **进度的唯一依据**：只记观察到的事实（命令、输出、提交），不记计划。计划在 [build/](build/)，决策原因在 [context/](context/)。
> 追加规则：下面「活动记录」只追加、不改写旧条目；阶段状态表可以改。每个阶段完成时必须有验收证据才能标「完成」。
> 第一版（Dify 文档问答，阶段 00～21）的日志在 [archive/v1-dify-docs/build-log.md](archive/v1-dify-docs/build-log.md)。

## 当前状态（先读这里）

最后更新：2026-11-18（第二版计划写完，代码未动）

- **方向**：项目改为「索尼银行住宅贷款坐席 Copilot」概念验证，见 [GOALS.md](../GOALS.md)、[PLANS.md](../PLANS.md)。
- **代码**：仍是第一版的状态，等同于 git 标签 `v1-dify-docs`（即 `origin/main` 的 `4ae48f3`）。本轮只改了文档，没有改任何代码、测试、配置。
- **分支**：`2026-11-18-sony-pivot`，从 `origin/main` 的内容建立；本轮改动未推送。
- **第一版遗留**：阶段 21 的消融还有 251 份回答没评审，随第一版一起归档，不再继续。
- **下一步**：执行 [阶段 30](build/phase-30-cleanup-infra.md)。
- **阻塞**：无。阶段 31 会需要作者用浏览器保存索尼银行的公开页面。
- **提醒**：远程仓库是公开的。推送前确认没有带入公开页面原文和参考方案原文。

## 阶段状态

状态取值：未开始 / 进行中 / 阻塞 / 完成。「完成」表示验收标准已观察到，不是计划。

| 阶段 | 状态 | 说明 |
|---|---|---|
| [30 清场与基础设施](build/phase-30-cleanup-infra.md) | 未开始 | |
| [31 语料与知识库加工](build/phase-31-corpus.md) | 未开始 | 需要作者保存公开页面 |
| [32 检索](build/phase-32-retrieval.md) | 未开始 | |
| [33 模拟业务系统与工具层](build/phase-33-tools.md) | 未开始 | |
| [34 双泳道编排](build/phase-34-orchestration.md) | 未开始 | |
| [35 流式与护栏](build/phase-35-streaming-guard.md) | 未开始 | |
| [36 评测与回归门禁](build/phase-36-evaluation.md) | 未开始 | 需要作者出题、校准、跑测试集 |
| [37 Dify 对照](build/phase-37-dify-compare.md) | 未开始 | 需要作者在 Dify 界面操作 |
| [38 收尾](build/phase-38-wrapup.md) | 未开始 | |

## 活动记录（追加）

### 2026-11-18 · 第二版计划（分支 `2026-11-18-sony-pivot`）

模型：Claude Fable 5.2（只写计划，不改代码）。

- 作者要求把项目改造成贴近参考方案（坐席 Copilot：工具 + RAG、双泳道、Dify 到 LangGraph 的对照），业务背景换成索尼。作者确认四项：业务线为索尼银行住宅贷款；知识库与回答用日文；本地真搭 Dify 做对照；在本仓库原地替换。
- 核对远程：`git branch --merged origin/main` 显示全部 8 个本地分支都已并入 `origin/main`；`git diff --stat HEAD origin/main` 无输出（改动前的工作区与远程 main 内容相同）。`gh repo view` 显示仓库为 PUBLIC。
- 建本地标签 `v1-dify-docs` 指向 `origin/main`（`4ae48f3`），未推送标签。
- `.git/index.lock` 是 2026-11-16 留下的 0 字节残留文件，当时没有 git 进程在运行，已删除。
- 用 `git mv` 把第一版的 `harness/build/`、`harness/context/`、`harness/code_review/`、`harness/build-log.md`、`GOALS.md`、`PLANS.md` 移到 `harness/archive/v1-dify-docs/`（85 个文件）。
- 新写：`GOALS.md`、`PLANS.md`、`AGENTS.md`、本文件、阶段 30～38 共 9 个阶段文件、[决策记录](context/phase-30-pivot-context.md)。
- 语料来源调研（浏览器人工访问）：`https://sonybank.jp/robots.txt` 与非浏览器请求均返回 403；住宅贷款栏目侧栏约 35 个页面；FAQ 的住宅贷款分类为 `category=5314`，下有 5 个子类；[利用条件](https://sonybank.jp/guide/notice/10.html)只允许私人使用、禁止再分发。结论写进了 PLANS §3.1 的约束。
- 没有运行 `poe check`：本轮没有改动任何代码或配置。
