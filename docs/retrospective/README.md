# 第二版交接与复盘

2026-11-20 冻结提交 `fdd5a5eb16e9fb1e7a4e10e9fba9f7e6881cb4c0`。这是住宅贷款 Copilot 的本机 PoC，已完成开发回放、Dify 同题对照、合规专项与一次封存技术回放。 [当前状态](../../harness/build-log.md#当前状态先读这里) · [封存结果](../eval/mac-poc-report.md#冻结版一次封存回放)

## 按目的查资料

| 你要做什么 | 入口 |
|---|---|
| 快速了解代码、接口和纯合成启动 | [项目 README](../../README.md) |
| 核对 LangGraph、Dify 和模型的详细结果 | [实测复盘](metrics.md)、[主报告](../eval/mac-poc-report.md) |
| 换机、复现、定位踩坑和后续改进 | [换机复现与工程复盘](migration.md) |
| 恢复 Dify 实例或核对 37 节点 | [Dify 本机手册](../eval/dify-local.md)、[画布和平台边界](../../infra/dify/chatflow.md) |
| 作者运行封存集、确认预算与回传格式 | [作者封存命令](../eval/copilot-author.md#作者运行一次封存评测) |
| 找决策、验收命令和完成证据 | [开发日志](../../harness/build-log.md)、[目标](../../GOALS.md)、[计划](../../PLANS.md) |
| 回看最初的 Dify 中文文档问答 | [第一版归档](../../harness/archive/v1-dify-docs/README.md) |

## 阶段文件索引

`harness/build/` 记录每阶段的验收条款及实测，`harness/context/` 记录当时的技术决策和设备条件，`harness/build-log.md` 给出按时间排列的工作记录。阶段文件保留原路径，旧报告的证据链接仍可用。

| 模块 | 阶段验收与技术记录 |
|---|---|
| Mac 环境、容器与模型 | [30 基础设施](../../harness/build/phase-30-cleanup-infra.md)、[Mac 实测配置](../../harness/context/phase-30-mac-context.md) |
| 语料、版本、双库与工具 | [31 语料](../../harness/build/phase-31-corpus.md)、[32 检索](../../harness/build/phase-32-retrieval.md)、[33 模拟业务](../../harness/build/phase-33-tools.md) |
| 坐席/客户泳道、会话与流式护栏 | [34 编排](../../harness/build/phase-34-orchestration.md)、[35 流式](../../harness/build/phase-35-streaming-guard.md) |
| 评测口径、Dify 对照、边界修复与冻结 | [36 评测](../../harness/build/phase-36-evaluation.md)、[37 Dify](../../harness/build/phase-37-dify-compare.md)、[38 收尾](../../harness/build/phase-38-wrapup.md) |

## 工程和本机文件

| 目录或文件 | 用途 |
|---|---|
| `backend/app/` | REST、MCP、LangGraph 编排、检索、模型网关和工具实现 |
| `backend/eval/`、`backend/scripts/` | 评分、报告、回放与调试入口 |
| `mock_core/` | 带明确 `synthetic` 标记的模拟业务，含种子和只读接口 |
| `infra/`、`docker-compose.yml` | 网关、Dify 画布、Elasticsearch 和本机服务 |
| `backend/uv.lock`、`mock_core/uv.lock` | 两个跟踪的正式依赖锁文件，换机同步依赖时使用 |
| `.cache/uv`、`.cache/uv-phase37`、`backend/.venv` | 原机生成的缓存、阶段日志或虚拟环境，换机可重新生成 |
| `.cache/handoff-2026-11-20/` | 原机汇总资料、指纹清单和 `development-metrics.zip`，便于换机留档 |
| `.cache/copilot-dev/`、`.cache/copilot-eval/` 等 | 原始开发证据和中间产物；具体运行见 [证据索引](metrics.md#证据定位与未测项) |
| `.env`、`data/` | 本机密钥、语料及业务样例派生数据，由作者按各自使用条件保管 |

## Git 交接

- `2026-11-20-project-handoff` 提交冻结运行代码和冻结记录，草稿 PR 目标为 `main`。 [冻结代码 PR](https://github.com/Cookie0103/grounded_rag/pull/3)
- `2026-11-20-retrospective-docs` 从代码交接分支派生，草稿 PR 目标为代码交接分支，只包含复盘和换机资料。冻结标签留在原机；新机也可以通过完整提交号核对运行文件。 [交接文档 PR](https://github.com/Cookie0103/grounded_rag/pull/4) · [换机命令](migration.md#换机先准备什么)
