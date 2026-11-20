# MDX 清洗用合成夹具

这里的日文材料是为测试编写的架空观测室示例。每份 MDX 都在 front matter 和正文中标记为 `synthetic`。

| 夹具（文件名主干） | 主要覆盖 |
| --- | --- |
| `inline-note-in-table` | Markdown 表格内联提示、换行与徽章，保留图片框说明 |
| `html-table-bt-panel` | HTML 表格转 Markdown，合并单元格列表、转义竖线，保留代码围栏 |
| `import-text-data` | 去除旧版自动翻译声明、链接地址与图片，保留正文和嵌套列表 |
| `tabs-ifelse` | 嵌套选项卡和列表、图片框、章节标题路径 |
| `steps-pipeline` | 步骤内嵌卡片、属性换行、分组重新编号 |
| `accordion-cards-publish` | 步骤、卡片组、内嵌提示的折叠块 |
| `environments-excerpt` | 列表内代码围栏、折叠块内环境变量表格，长表格切块 |

每个 `*.mdx` 对应一个 `*.expected.md`，由 `tests/unit/ingest/test_cleaner.py` 逐字比对。
修改夹具或清洗规则后，逐行核对期望输出，确认应保留的结构、正文和代码仍然完整。
清洗规则发生变更时，将 `INGEST_VERSION` 加 1。
