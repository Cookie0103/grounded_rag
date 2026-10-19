# Batch-04 正式题作者交接

范围：dev068～dev090，23题。只写本目录；未修改canonical题集、前半批或backend，未提交，未调用模型、完整RAG、无检索基线或花费接口。来源是冻结182篇文档。正式独立审题、与另一半及旧24/20的最终事实查重、全70原样检索和数据库核验仍由主任务完成。

## 本批结果

- 类别为single 9、multi 9、refuse_correct 3、clarify 2；子类严格保持通过的蓝图：同义2、枚举/数值2、易混2、短问1、单版本2、链式3、并列4、分散2，以及五种不可答/澄清各1。
- 16/23题不超过40字符，全部不超过80字符；最长61字符。正文均为正式自然题干，不把蓝图选题意图直接用作题干。
- 18道可答题各有2～4个vital；single至少2、multi至少3。5道不可答/澄清nuggets为空，拒答边界、矛盾句或两种实际理解另附来源。所有guessable_without_docs=null。
- scenario_or_symptom声明14题，condition_or_exception声明11题；这些是作者按实际问句标记，仍需独立语义复核。
- 57条vital的76个来源叶子重新调用durable locate_evidence严格定位，原文行、完整清洗摘录、child及parent、hash、偏移均可重建。跨子块用all_of；等价来源用any_of。没有沿用蓝图fuzzy或mapping_pending。所有database_verified=false。
- 11组实际存在的金标孪生均保存逐字raw/clean hash与完整差异；题点等价与全文等价分开记录，等价金标两版各有真实来源。
- dev084清洗16351字符，必要父块p1/p6/p10共3个；dev085清洗6225字符，必要父块p9/p10/p11/p12共4个。每条必要引用均位于现评审器前12000字符内。没有用OR孪生虚增父块数。

## 逐题收窄和来源修正

- dev068用“默认值”标题和继续运行正文两个all_of支持模式名称与行为；类型约束另为一条vital。
- dev070只考Skill导入包50MB与配置名，三条真实Builder文件限制作为相似干扰；不把库容量等无关数值硬塞为答案。
- dev071未在题干泄漏“二进制”；明确为正文枚举/配置查读，无答案数值，JSON/表单数据/原始文本为真实同类干扰。
- dev072仅保留两输出通道、适用模型及API事件四个题干已问事实；未将关闭开关的结果加为未问vital。
- dev073只考上轮依赖和未设退出条件时的上限停止，不再捆绑所有其他停止方式。
- dev075只从Cloud明示套餐约束推断Sandbox；不从self-host缺段推出一切自部署均无限制。
- dev076把Sandbox 7天、两档付费30天、一键恢复拆为三个独立vital；没有复用旧题的手动禁用/排除检索事实。
- dev077从API持久运行标识桥接控制台定位/追踪/按原输入测试，四vital；引用日志两版等价OR。机械检查曾拒绝关键词“运行ID”因原文有空格，已改真实原文“运行 ID”后复检通过。没有改题干以迎合检索。
- dev078首问明确Chatflow携带凭证与结束当前响应的两个事件；第二跳考上传id到upload_file_id映射和被拒后同token重试，恰四vital。未把旧连接重连、成功token失效等未问事项强加得分。
- dev079为本批唯一教程→节点链：课程定位实际节点及正文交接，随后查嵌套取值与缺失兜底。题干不泄模板/Jinja2/default或第二篇所列五个以上答案关键词。
- dev080只考两平台空间字段与Phoenix系统密钥三个事实；不再把所有接入凭据组合捆绑。
- dev081仅考Langfuse Host/Public Key及LangSmith PAT/错名结果四事实；不强制题干未问的Secret Key。
- dev082接入方式、节点操作选择、节点凭据、默认凭据入口四事实分别定位。
- dev083只考两Cookie配置、更域名后控制台CORS项、不可跨可注册域名的共享边界；边界使用明确原句，不靠浏览器常识推断。
- dev084只考最低服务端版本、端口、迁移选项、界面检索验收四事实，未纳入未问的停机或对象数量检查。
- dev085四个动作分别对应四个必要父块：放弃的长期文件改动、运行时新增内容临时性、新对话重读构建笔记、恢复版本的长期文件；已消除旧蓝图早期事实/行号错位。
- dev086对10个近似安全/漏洞政策词逐篇raw扫描均零命中，附3篇近邻的完整阅读边界说明；仅判库内没有时限承诺，不否认现实处理服务。
- dev087操作式错误前提引用“只有用户输入才能发布MCP”及“开始与触发器互斥”的直接矛盾句。
- dev089题干无版本字样、edition=null，保留Cloud与较旧自部署导入DSL的两个实际条件答案。
- dev090保留外部检索服务接入与业务API动态补充Prompt两种具体理解、各自答案和两版来源。

构建过程中，长行跨child或清洗链接空格导致的locate_evidence拒绝均未强行通过：llm事件句、human-input-flow上传句、streaming干扰句、Cookie边界句改为完整可包含的短引；需多段支持时拆all_of；Agent放弃和外部工具链接句显式使用实际清洗文本并保留原始原文。没有填造chunk或跳过严格包含检查。没有弃用已批准的蓝图题材；正式化收窄均保持对应主题、行为与金标组。

## 已运行验证

1. `backend/.venv/bin/python .cache/dev70-completion/batch-04-draft/build.py`：退出0，生成23题、16短题、严格来源全部定位；可按冻结索引重建本批文件。
2. 现有`eval.dataset.load_questions`与`validate_questions`：loaded=23，issues=[]；报告`loader-validation.json`。没有修改旧QUOTAS。
3. `backend/.venv/bin/python docs/eval/dev70/tools/validate_completion.py --mode snapshot --questions .cache/dev70-completion/batch-04-draft/questions.jsonl --evidence .cache/dev70-completion/batch-04-draft/evidence.json --twin-comparisons .cache/dev70-completion/batch-04-draft/twin-comparisons.json --old20 docs/eval/dev20/questions.jsonl --output .cache/dev70-completion/batch-04-draft/validation.json`：退出0，234 pass、18 pending_scope、0 fail，50项需要独立语义审阅。pending_scope来自只提交半批而尚未齐备的全局范围。

这不是全70最终通过：未声称机械字段齐全等于语义通过，未声称已完成检索、无检索基线、最终评分或数据库验证。主任务合并时保留所有OR组与all_of，不可把一个来源叶子替代整条跨块事实。

## 交付文件SHA-256

- `questions.jsonl`：`f34a81ffcada35bc522b6f2150789d2938a4e05d3ce44a3c79a7eede7d34be59`
- `evidence.json`：`c90099ec011f51dbd52b7fcbd6e41254e3f6fff5aef3caa3c7cd4b9e214da0e1`
- `twin-comparisons.json`：`f09572e0e219b32b669f0635e37fbd8dac96e9402f18a81373b06f48b5b86b4f`
- `validation.json`：`22a52f157db032f1d8edc599fc332135bb740b049de8cc1c8fc3f143d0fe971c`
- `loader-validation.json`：`fb991b01b71df98b4729cb073c9f919516770fe0df2a9450a77f1e1e714f9293`
- `build.py`：`aac0743812e09d3c9d1b623dc93ce8b12515b4f4efd2280e1c53a2f3c65dd526`
