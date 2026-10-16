"""检索文本与问题归一化。"""

import re


def search_text(heading_path: str, text: str) -> str:
    """标题路径 + 换行 + 子块正文。

    标题路径一起检索，是为了让「S3 的配置项」这类只出现在标题里的信息也能被找到
    （Contextual Retrieval 的免费简化版，见 docs 里的 RAG 笔记）。
    """
    return f"{heading_path}\n{text}"


def question_key(question: str) -> str:
    """干预库的匹配键：小写，去掉空白和标点，「怎么上传？」和「怎么 上传」是同一个问题。"""
    return re.sub(r"[\W_]+", "", question.lower())
