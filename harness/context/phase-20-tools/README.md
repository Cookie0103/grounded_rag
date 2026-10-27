# 仓库外工具的审查副本

这里以Markdown代码块保存新版迁移包中3个脚本的完整源码，不含题目或系统回答，供Claude在Git上审查。运行版.py文件保存在仓库外迁移包。

运行需要仓库外迁移包的文件结构，不要直接在这里执行。命令与数据位置见上级 `phase-20-review-repair.md` 和新版包内README。

- `resume_dev70.py.md`：运行版命令为`resume_dev70.py --repo <REPO> --transfer <TRANSFER>`，调用已单测的 `scripts.rejudge`，验证36条成功标签后迁入全新目录；开始和退出核对冻结实现。
- `deliver_v2.py.md`：运行版命令为`deliver_v2.py <REPO>`，三套完整无当前错误后生成对照、完整flips、固定种子的校准样本和原回答核查。保留18条历史错误，人工栏留空。
- `audit_v2.py.md`：运行版命令为`audit_v2.py <REPO>`，核验原保护文件映射、新冻结、完整标签集合、交付材料和历史错误留存。模板哈希核验委托 `scripts.audit_rejudge.audit_run`，缺键会失败。

这些外部脚本已检查语法；实际完整生成和审计须等三套真实重评完成后执行。合成单元测试与真实dev缓存只读迁移预检的范围见上级文档，不能声称尚未运行的全量交付审计已通过。
