# 已知缺口与需要作者做的事

> 按「谁来补」分。代码、测试、CI 都是绿的（`poe check` 421 passed，覆盖率 95%；`poe test-int` 32 passed；`poe test-gpu` 3 passed）；下面这些**没有被验证过**，不要当成已经成立的结论。

## 一、需要作者提供 / 操作（阻塞真实数字）

| 编号 | 事项 | 影响 | 怎么做 |
|---|---|---|---|
| A1 | Gemini 出评测题（开发集 ~70、测试集 ~30） | 没有它，所有「效果」数字都出不来；M2 的模型对比只是 28 题冒烟集上的暂定结论 | [出题提示词](eval/gemini-question-prompt.md)、[运行手册](eval/runbook.md) §1 |
| A2 | `DEEPSEEK_API_KEY` | 真实生成、真实 LLM 评审、真实路由 / 评分 / 校验的提示词效果、`/chat` 的真实延迟 | 写进 `.env` |
| A3 | 评审校准：人工标 20 条，一致率 ≥ 85% | 低于它，自动评审的结果不能用来比较方案 | [运行手册](eval/runbook.md) §3 |
| A4 | 测试集只跑一次 | 最终报告 | [运行手册](eval/runbook.md) §5 + [报告模板](final-report-template.md) |
| A5 | 在 Claude Code 里注册 MCP 并试用；确认从仓库根目录启动时 `.claude/settings.json` 的 deny 规则（禁止编辑 `backend/eval/data/`）生效 | 只验证了 stdio 子进程能列工具，没在真实客户端里调用 | [运行手册](eval/runbook.md) §6 |
| A6 | 决定：版本未知时是否默认自部署版（现在是不过滤） | 版本类题的表现 | 见 [decisions.md](decisions.md) |
| A7 | GitHub 合并 / CI 要求（作者说之后再说） | 目前所有提交都在 `2026-10-16-framework-build`，没有 PR | |
| A8 | 把 Notion「开发计划_Polish」页首的进度更新同步给自己看 | | agent 已尝试更新，见当天日志 |

## 二、代码层面没验证的

- 真实模型下：路由准确率、改写 / 分解 / 证据评分 / 忠实度校验的提示词效果。**提示词都是第一版**，要用开发集调；每次改动新增 `_v2` 文件，不要覆盖。
- 追问独立化、摘要的质量（没有多轮评测集）。
- 评审：Gemini 主评 + Claude 复评的双评审只支持 `claude -p` 命令行和 DeepSeek；没有 `gemini` 命令行（本机没装）。评审调用的费用没有计进报告的成本。
- 压测数字只测了假对话模型 + 真实检索：`/retrieve` 冷查询 QPS 4.8、P95 870 毫秒（精排在 GPU 上串行，是瓶颈）。
- HTTP 模式的 MCP（只验证了 stdio）；`traces` 表没有保留期清理。
- 日文版：只保留可行性（SudachiPy），没有做。

## 三、设计上的取舍（可以推翻）

- 黑名单默认空表（`app/orchestration/postprocess.py` 的 `BLOCKED_TERMS`）。
- 答案缓存键不含对话模型名，换模型后要重启服务。
- 限流只按 IP；没有鉴权。
- Contextual Retrieval 只做了免费简化版（标题路径拼进检索文本），大模型生成上下文留作备选，要看开发集的错误归因再决定。
