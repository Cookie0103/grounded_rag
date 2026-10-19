# 清洗测试用的真实文档

这些文件是从 [langgenius/dify-docs](https://github.com/langgenius/dify-docs)（commit `c80a31868611b673bd77725a6310c685068a585e`，`zh/` 目录）原样复制的，
`environments-excerpt.mdx` 只取了 `environments.mdx` 的第 1～45 行和第 613～700 行（含向量数据库配置里的手风琴和表格）。许可：CC BY 4.0，© Dify 项目。

每个 `*.mdx` 对应一个 `*.expected.md`：清洗后的期望输出，由实现者逐行核对后提交（`tests/unit/ingest/test_cleaner.py` 逐字比对）。
改了清洗规则要重新核对并更新期望输出，同时把 `INGEST_VERSION` 加 1。
