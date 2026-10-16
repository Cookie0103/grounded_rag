"""嵌入和 BM25 共用的检索文本。"""


def search_text(heading_path: str, text: str) -> str:
    """标题路径 + 换行 + 子块正文。

    标题路径一起检索，是为了让「S3 的配置项」这类只出现在标题里的信息也能被找到
    （Contextual Retrieval 的免费简化版，见 docs 里的 RAG 笔记）。
    """
    return f"{heading_path}\n{text}"
