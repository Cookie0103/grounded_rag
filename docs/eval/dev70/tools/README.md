# 新70题独立来源与机械检查工具

可复跑工具保存在本目录，不写题、不改业务、评分或 canonical 题集。索引和逐项校验报告默认生成到忽略目录 `.cache/dev70-completion/`，不提交原文索引；目录统计生成到 `docs/eval/dev70/corpus-distribution.json`。运行解释器使用已恢复的项目 `.venv`；除生产清洗/切块已依赖包外只用标准库，不安装新包。

仓库根目录通过向上查找同时存在的 `backend/app` 与 `AGENTS.md` 自动定位。以下命令从仓库根执行；从任意其他目录执行时，为解释器、脚本和显式传入的文件路径使用绝对路径即可。脚本默认文件路径均以自动定位的仓库根解析。

```bash
backend/.venv/bin/python docs/eval/dev70/tools/source_index.py
backend/.venv/bin/python docs/eval/dev70/tools/validate_completion.py --mode snapshot --old20 docs/eval/dev20/questions.jsonl --output .cache/dev70-completion/durable-snapshot-validation.json
backend/.venv/bin/python docs/eval/dev70/tools/validate_completion.py --mode blueprint --questions docs/eval/dev70/blueprint.json --old20 docs/eval/dev20/questions.jsonl --output .cache/dev70-completion/blueprint-independent-validation.json
backend/.venv/bin/python docs/eval/dev70/tools/validate_completion.py --mode completion --questions docs/eval/dev70/questions.jsonl --evidence docs/eval/dev70/evidence.json --old20 docs/eval/dev20/questions.jsonl --output .cache/dev70-completion/final-independent-validation.json
backend/.venv/bin/python -m unittest discover -s docs/eval/dev70/tools -p test_tools.py -v
```

`--old20` 的文件必须是已许可读取的旧20开发材料，路径按实际位置传入。工具拒绝 `backend/eval/data` 和封存路径，不自动搜索题集。退出码1表示有硬失败；`pending_scope` 表示检查范围尚未齐备；`legacy_observation` 表示未点名旧题的新硬条件观察，不要求修改它。静态脚本不会把未完成的检查标通过。

JSON默认每项检查一行，保留全部条件、实际值、目标值与失败详情；`--expanded` 可恢复多行展开，两种格式解析后内容完全一致。报告不重复原始证据全文，来源成功只记录核验数量，失败才记录具体错误。`pass`、`pending_scope`、`legacy_observation`分别统计，数量多来自逐题逐规则检查，不表示重复执行。`--semantic-review 独立审查.md` 可重复附加外部审查文件的路径、字节数与sha256；这些文件只是可核对的外部证据，不会使 `semantic_review_complete` 自动变成true，也不会把元数据自报的pass采纳为语义完成。

`corpus-index.json` 的 `documents` 是以 doc_id 为键的字典。每篇有 `raw_text`、`source_file_sha256`、`cleaned_markdown`、`cleaned_characters`、`title`、全部 `headings`、`parents`、`children`；parent/child保留生产ordinal、heading、text和稳定id。清洗统计：182篇、1252父块、2090子块、534522字符、20篇不少于6000字符。目录分布同时列全部182篇和精确少覆盖目录映射，不将整个build目录泛算为插件或模型接入。

证据模块使用方式：

```python
from artifact_helpers import load_index, locate_evidence, any_of, nugget_evidence, compare_twins
index = load_index()
source = locate_evidence(doc_id, verbatim_raw_excerpt, index=index)
item = nugget_evidence(0, "原子事实", "vital", any_of(source))
pair_id, comparison = compare_twins(doc_id, index=index)
```

可选 `cleaned_excerpt` 指定清洗后的子片段，`raw_line_start` 为重复原文消歧，`chunk_id` 指定已知子块。任何原文未找到、歧义未消除、清洗片段不在文档或跨子块的情况都抛 `EvidenceError`；应缩小片段或用多个 `all_of`，禁止编造id。`database_verified`固定false，文件重建不冒充数据库验证。`compare_twins`返回兼容现有 `twin-comparisons.json` 的逐字差异记录。

新增题可使用的字段（优先放evidence，蓝图可直接放题项）：

- `form_tags`: `scenario_or_symptom` / `condition_or_exception`；脚本只计声明，形式是否实质成立仍需独立审。
- `chain`: 复用 `first_document`、`second_document`、`second_document_answer_keywords`（至少5个真实第二篇关键词）、`dependency`；新增 `bridge_type`（至少4种）、`generic_distractor_documents`（至少2篇真实文档，可为doc_id列表）。
- `synonym_title_overlap_whitelist`: `[{"trigram":"工作流","reason":"明确通用词理由"}]`；不提供隐式白名单，每个词都保留在审阅文件中。
- `answer_literals`: 数值、字段或枚举的答案字面值；`numeric_confusables`: `[{"literal":"具体数字或字段","source": source}]`，至少3条不同数字/字段/原文行，全部可定位。
- `no_answer_audit`: 兼容原来的 `lexical_checks` 和 `closest_docs`；重新扫描182篇raw，至少10不同近似词0命中，至少3近邻。词是否足够近、说明是否充分另审。
- 缺槽位 `interpretations`: `[{"interpretation":"理解一","answer":"对应答案"}, ...]`，至少两种。
- 错误前提 `contradiction_evidence` 或原来的 `boundary_evidence`，必须有真实原句；是否明确矛盾另审。
- 纯注入且无gold文档可用非空 `acceptance` / `behavioral_acceptance`，nugget的 `all_of` 可空，不伪造引用。

机械检查覆盖两组配额、含OR复用、nodes上限、少覆盖目录、vital数量、形态声明比例、同义题全语料标题三字重合、答案泄漏、链式关键词、分散证据最少父块数（正确处理OR）、清洗长文、近义词零命中、原始行/文件hash/生产子块父块/偏移/heading/url、孪生逐字符差异可重建性、相同清洗文的同组OR、指定旧题保留和点名修订数量。两份“相同事实”的同义改写、独立性、bridge必要性、版本答案差异、歧义合理性等始终列 `requires_independent_semantic_review`。未执行真实检索，未证明数据库，未验证出题时间顺序，也不输出正式评测成绩。

原样单次检索入口（需要项目数据库、已入库向量和本地模型）：

```bash
HF_HUB_OFFLINE=1 backend/.venv/bin/python docs/eval/dev70/tools/retrieval_selftest.py --device mps
```

Windows/CUDA电脑可用`--device cuda`，或省略device读取既有配置。每题只调用一次`retriever.retrieve(question)`，不传edition、不分解、不生成或评审答案。JSONL保存实际前5子块及文档、组内OR命中、模型、设备、时间和降级状态。同一query hash和设备/模型已有成功记录时续跑会跳过，不进行挑选重试；更换题目或金标的复测应指定新的`--output`，保留首轮原始记录。最终70条与当前question hash、金标组一致的核对结果见root validation。

上述机械工具的限制与真实运行证据分开：本轮确实完成了70次MPS检索和全量只读DB比对，结果见`../retrieval-selftest.jsonl`与`../runtime-verification.json`；来源helper仍只从文件重建，调用它本身不验证DB。初版蓝图的后续语义修订见`../blueprint-amendments.json`，复跑原版蓝图仅能重现当时的静态条件。
# 2026-10-20修订说明

验证器复用上限按作者已定H4规则，仅排除固定白名单题的environments配置等价OR；主金标及其他专题页仍计数。逐点来源以all_of/any_of为准，题级组不能用部分等价来源虚报整题全命中。H4边界有回归检查，`test_tools.py`可运行。

`source_index.py`用相对路径字符串显式排序，避免WindowsPath大小写排序改变分布。检查时指定`--distribution .cache/...json`，不会覆盖已提交分布文件。本轮重建与历史分布JSON相同；不声称跨平台物理换行逐字节相同。

本轮只做文件重建与静态核验，`retrieval-selftest.jsonl`仍是修订前原始记录。当前题目和金标已经变化，不得把历史召回比例当作本轮结果。当前状态见上级README与phase-17。
