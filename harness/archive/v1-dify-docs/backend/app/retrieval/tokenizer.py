"""BM25 的分词：jieba3 搜索模式，切词前先保护变量名和术语。

查询和文档必须用同一个函数。字符二元组分词留作 M2 对照实验的另一个选项。
"""

import re

import jieba3

from app.retrieval.terms import PROTECTED_TERMS, STOPWORDS

_IDENTIFIER = r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+"  # UPLOAD_FILE_SIZE_LIMIT 这类变量名（已转小写）
_TERMS = "|".join(sorted(map(re.escape, PROTECTED_TERMS), key=len, reverse=True))
_PROTECTED = re.compile(f"({_IDENTIFIER}|{_TERMS})")
_HAS_WORD_CHARACTER = re.compile(r"\w")
_CHINESE_RUN = re.compile(r"[一-鿿]+")
_ASCII_WORD = re.compile(r"[a-z0-9_]+")

_cutter = jieba3.jieba3(model="base")


def tokenize(text: str) -> list[str]:
    """jieba3 的 cut_query（长词同时给出子词，召回更高）；变量名和术语整体保留。"""
    tokens: list[str] = []
    for index, part in enumerate(_PROTECTED.split(text.lower())):
        if index % 2:  # 奇数位是被保护的变量名 / 术语
            tokens.append(part)
        else:
            tokens += [
                token
                for token in _cutter.cut_query(part)
                if _HAS_WORD_CHARACTER.search(token) and token not in STOPWORDS
            ]
    return tokens


def bigram_tokenize(text: str) -> list[str]:
    """字符二元组：中文连续汉字切成相邻两字，英文单词和变量名整体保留。不需要词典。"""
    tokens: list[str] = []
    for part in re.findall(f"{_ASCII_WORD.pattern}|{_CHINESE_RUN.pattern}", text.lower()):
        if _ASCII_WORD.fullmatch(part) or len(part) == 1:
            tokens.append(part)
        else:
            tokens += [part[i : i + 2] for i in range(len(part) - 1)]
    return tokens
