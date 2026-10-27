> 本文件保留写题作者冻结时的交接记录；最终状态以本批validation.json、../blueprint-amendments.json和../semantic-review.json为准，后续修正不回写为作者初稿已通过。

# batch-03独占草稿

来源、事实、子类和金标OR组固定为通过的蓝图dev045～067；未改canonical、后半批或backend，未提交、未调用模型。

| ID | vital | 题干字符数 |
|---|---:|---:|
| dev045 | 4 | 31 |
| dev046 | 3 | 28 |
| dev047 | 2 | 25 |
| dev048 | 2 | 26 |
| dev049 | 2 | 28 |
| dev050 | 3 | 35 |
| dev051 | 3 | 30 |
| dev052 | 2 | 19 |
| dev053 | 1 | 19 |
| dev054 | 2 | 23 |
| dev055 | 4 | 51 |
| dev056 | 3 | 36 |
| dev057 | 4 | 35 |
| dev058 | 4 | 34 |
| dev059 | 4 | 29 |
| dev060 | 4 | 36 |
| dev061 | 3 | 41 |
| dev062 | 4 | 36 |
| dev063 | 0 | 32 |
| dev064 | 0 | 30 |
| dev065 | 0 | 34 |
| dev066 | 0 | 19 |
| dev067 | 0 | 15 |

23题由项目load_questions和validate_questions读取检查，格式错误0；<=40字符21题，最大51字符。

dev045拆出插入后映射操作，满足guardrail；dev046快捷键、@node范围和备用入口拆点；dev050能力与任务分开；dev052恢复与发布分开；dev053保留唯一单vital短问，另附Docker运行方式okay。

所有source经durable locate_evidence严格定位；长蓝图摘录拆短，Windows命令和FILES_*配置各必要父块单独定位。未采用fuzzy或最长重合映射。

纯拒答/纠正/模糊题nuggets=[]；缺依据与错误前提expected_route=null。无依据重新扫182篇raw；RPO/VAT短词内部伪命中按真实子串非零列旁证，不计零命中配额，另列有意义长近似词。

链式各保留蓝图桥接、5+第二篇识别词、2泛词干扰及真实原文；dev056明确自建，避免Cloud未知Q&A节外推。

数据库全部留false，主agent统一复核DB和全70原样检索。另一半未纳入本文件，机械snapshot中全局计数pending不冒充完成；语义独立审题仍待主agent。

## 实际机械自检

命令：`backend/.venv/bin/python docs/eval/dev70/tools/validate_completion.py --mode snapshot --questions .cache/dev70-completion/batch-03-draft/questions.jsonl --evidence .cache/dev70-completion/batch-03-draft/evidence.json --twin-comparisons .cache/dev70-completion/batch-03-draft/twin-comparisons.json --old20 docs/eval/dev20/questions.jsonl --output .cache/dev70-completion/batch-03-draft/validation.json`

结果：{'pass': 239, 'pending_scope': 18}，硬失败0；逐项核对原文/文件哈希/子块/父块/heading/偏移/URL共99处source。18项pending是另一半/全量口径未齐，不宣称全70完成。50项语义判定仍需独立审题。

首轮8项机械失败：同义题外部数据标题三字、易混两个标题同名Agent、同时词筛选、3条英文/中文关键词空格、1条真实原句写法、dev056 edition与共享模板OR条件；已改自然措辞、按原文精确空格列关键词、保留题干自建上下文并设置edition=null且写source_applicability。未改来源或蓝图事实。
