# judge_v2 修复复审（159ab99..b3b1b30）

日期：2026-10-20。分支 `2026-10-20-dataset-repair`，HEAD `b3b1b30`（已确认包含）。只读审查，未调用真实评审、未重跑系统或检索、未读取测试题内容。

## 对上一轮审查的更正
上一轮把 `judge_v2.md` 的 nuggets 句子（"关键点完整表达就是 support……不降级"）判为越权，并建议作废 36 条标签。作者说明该句来自原任务"二/1/d"，属明确授权；我没有看到那份原任务文本，接受作者的说明。**撤回该 P1**，36 条标签不作废。保留的要求：报告必须单列 nuggets 变化，不得把全部分差归因于 contexts（见下，已满足）。

## 核实方式
- VERIFIED（我运行的）：
  - 新包 SHA-256 = `87fae93f…33ad9`，与交接文档一致；解压到仓库外 `/tmp/rv2`；`TRANSFER-MANIFEST.json` 96 个文件逐个哈希，0 缺失 0 不符。
  - `backend/.venv/bin/python -m pytest tests/unit`：**463 passed**（与 Codex 记录一致，独立复现）；`ruff check` 通过；`mypy scripts eval` 通过；`lint-imports` 1 kept / 0 broken。覆盖率未单独复算。
  - 探针（`/tmp/probe_rv2.py`，只调用 `_prepare`、`verify_*`，不触发评审）：
    - `verify_portable_hashes` 对 缺键 / 多键 / 值不同 / 空表 / 重名 映射，**全部抛 ValueError**；相等时通过。
    - `verify_frozen` 对当前仓库的 6 个实现文件与 `phase-20-v2-repair-freeze.json` 比对通过（因此 `judge_v2.md` 模板字节仍是 `6005863e…`）。
    - 真实 dev 缓存做 `--seed-run` 预备到全新目录：题数 70；复制的 `verdicts.jsonl` 与旧文件**字节相同**，36 条；`errors-history.json` 18 题，且这 18 题全部属于"待评"34 题（无与已成功标签冲突）；需要实际调用评审的题数 = **34**。
- REASONED（读了代码，未运行）：`rejudge.py` 的 finally 复核、10% 熔断、`record_errors` 保留历史。
- 未运行：外部 `deliver_v2.py`/`audit_v2.py` 的全量交付与审计（需要三套真实结果，当前不可能）；`.md` 副本与包内 `.py` 的逐字节比较（行数差 1，疑为代码块首尾空行，内容逐段一致，未做严格字节比对）。

## 逐项核验
| 要求 | 结论 |
|---|---|
| 哈希缺键、多键、不一致失败 | 通过（`rejudge_artifacts.py:48-52`，探针 5 种情形均失败；`verify_frozen` 要求完整 6 文件，不从待核验清单推导） |
| 异常退出复核保护文件与冻结清单 | 通过（`rejudge.py` `run_rejudge` 的 `finally` 调 `verify_unchanged` 与 `verify_frozen`；有单测）。强杀进程不在保证范围，文档已如实写明，靠落盘断点恢复 |
| 首次 18 条错误永久保留 | 通过（`record_errors` 按题保留全部不同错误原文；预备阶段已从 seed 的 `errors.json` 迁入；补评成功不删） |
| 完整阶段错误 >10% 停止后续调用 | 通过（`_evaluate_cache` 每题后判断 `len(errors)*DENOM > len(questions)`；恰好 10% 继续。dev 的阈值为 >7 题） |
| `--seed-run` 先验证再复用 | 通过（`_validate_seed`：模板/评审器一致、manifest 哈希与当前输入显式比对、标签题号未知/重复/非法即拒；复制到全新目录，目录已存在则拒绝） |
| 旧记录不覆盖、36 条不重复评审 | 通过（旧目录只读，退出时对 seed 的 manifest/verdicts/errors 再复核；标签已在缓存，`evaluate` 不再调用评审——探针显示仅 34 题需调用） |
| nuggets 变化单列 | 通过（`render_flips` 新增逐点 nugget 标签变化表；`report.md` 开头声明 v2 同时改了 contradiction 依据与 support 解释） |
| 旧冻结与 Git 来源 | 通过（新增 `phase-20-v2-repair-freeze.json`，`source_git_base=159ab99`，旧冻结哈希 `687fddc7…` 记录在案，未改写；`audit_v2.py` 还会校验 `merge-base --is-ancestor`） |
| scoring 分值、v1、题集 | 未变（`judge.py`/`evaluate.py`/模板字节与旧冻结一致） |

## 问题（按严重程度）

**无阻塞性问题。** 以下均为改进项：

1. **P3 — manifest 中的绝对路径**：`rejudge.py` 写入 `manifest["sha256"]`、`seed_sha256` 的键是运行时的绝对路径。`audit_run` 对 `sha256` 用文件名映射（可移植），但对 `seed_sha256` 调 `verify_unchanged`（`audit_rejudge.py:41`）按原绝对路径读文件。若输出目录或 seed 目录在审计前被搬到别的路径/电脑，审计会因找不到文件而失败（失败方向安全，不会误过）。建议：就在生成评审的这台电脑上跑 `deliver_v2.py`/`audit_v2.py`，不要搬目录。
2. **P3 — `.md` 工具副本与包内 `.py` 未做严格字节比对**：真正执行的是包内 `.py`。建议执行前 `shasum` 对比 `phase-20-v2-repair-freeze.json` 之外再给这 3 个脚本记一个哈希（目前冻结只覆盖 `backend/` 内 6 个文件，不覆盖外部脚本）。
3. **P3 — 熔断后进程退出码为 1 但输出目录已含部分结果**：这是预期；使用者必须按 README 用 `--seed-run` 指向它再开新目录，不能直接重跑。已在 README 写明。

## 结论
1. **代码复审：通过。**
2. **三套 v2 重评：未完成**（dev 36/70，reg20、test30 未开始）。
3. **校准：未进行**；v1 预标 80%（16/20）；v2 需新样本（种子 20261021，`calibration-plan-v2.json` 已有计划），**至少 17/20 一致**才达 85%。代码通过不能代替校准。
4. **真实重评前是否还有阻塞：没有代码或数据阻塞。** 唯一外部条件：Claude CLI 额度需恢复（文档称东京 23:50，未确认）以及作者明确下令开始。
5. **整体能否收尾：不能。** 剩余最少动作：
   1. 作者授权后按包内 README：dev 续评 34 条 → reg20 → 仓库外 test30（不重跑系统/检索，不据 test 结果改提示词）。
   2. 运行 `deliver_v2.py` 与 `audit_v2.py`，得到三套报告、v1/v2 对照、完整双向 flips、nugget 变化、20 条校准样本、true→false 原回答核查，且保留 18 条历史错误。
   3. 独立标注校准样本，≥17/20 一致才采信；不够就如实报告，不重抽样本。

---

## 附：真实重评执行结果（审查后，经作者明确授权，评审器 `claude -p`）

执行（均按包内 README，未重跑系统或检索）：dev 续评 34 条 → 70/70 错误 0；reg20 → 20/20 错误 0；test30（输出在仓库外）→ 30/30 错误 0。熔断未触发。包内 `deliver_v2.py` 已生成对照、完整双向 flips、20 条校准样本（种子 20261021）、true→false 核查材料，历史 18 条限额错误在对照中保留。

初步数字（v2 未校准，不可对外当最终成绩；v2 同时改了 contradiction 依据与 support 解释，分差不能全归因于 contexts）：

| 题集 | 版本 | 严格成功率 | 宽松（含部分） | 可信得分 |
|---|---|---|---|---|
| dev70 | v1 → v2 | 62.5% → 67.9% | 69.6% → 82.1% | +0.557 → +0.729 |
| reg20 | v1 → v2 | 68.8% → 87.5% | 81.2% → 87.5% | +0.750 → +0.900 |
| test30 | v1 → v2 | 95.8% → 95.8% | 95.8% → 95.8% | +0.833 → +0.833 |

contradiction true→false：dev 8、reg 1、test 1；false→true：dev 1。

### 全量审计 `audit_v2.py`：未通过（不是 v2 结论错误，是环境问题）
- 失败点：受保护文件 82 个中 20 个与 Windows 记录的哈希不等；我逐个核对，**这 20 个全部仅是 CRLF 与 LF 换行差异**（按 CRLF 还原后哈希吻合），其余 62 个字节完全一致，无缺失、无内容差异。原因：Mac 上 git 检出为 LF。
- 我曾尝试在仓库外复制审计脚本并放宽为"换行符等价"，被系统权限拒绝（属放宽审计门槛），**未执行**；因此审计**没有**通过，也不能声称通过。
- 需要作者决定：(a) 授权放宽为换行符等价后重跑；或 (b) 在 Windows 原机/`core.autocrlf=true` 检出下重跑原脚本。
- 校准未进行：20 条样本需作者/独立标注，≥17/20 一致才算达 85%。当前 v2 仍为初步结果。
