"""语料清单：哪些文件入库，以及文档 ID、版本、类别怎么从路径推出。"""

from pathlib import Path

from app.core.config import DATA_DIR

CORPUS_REPO = "langgenius/dify-docs"
CORPUS_COMMIT = "c80a31868611b673bd77725a6310c685068a585e"
INCLUDE_PREFIXES = (
    "zh/self-host/use-dify/",
    "zh/self-host/deploy/",
    "zh/learn/",
    "zh/api-reference/guides/",
    "zh/cloud/use-dify/knowledge/",
    "zh/cloud/use-dify/workspace/",
    "zh/cloud/use-dify/monitor/",
)
INCLUDE_FILES = ("zh/home.mdx", "zh/quick-start.mdx")
EXPECTED_DOCUMENT_COUNT = 182

RAW_DIR = DATA_DIR / "raw" / "dify-docs" / CORPUS_COMMIT

EDITION_SELF_HOST = "self_host"
EDITION_CLOUD = "cloud"
EDITION_COMMON = "common"

_USE_DIFY = "use-dify"


def is_corpus_path(path: str) -> bool:
    """仓库里的相对路径（如 `zh/learn/x.mdx`）是否属于本项目的语料。"""
    if not path.endswith(".mdx"):
        return False
    return path in INCLUDE_FILES or path.startswith(INCLUDE_PREFIXES)


def document_id(path: str) -> str:
    """去掉 `zh/` 前缀和 `.mdx` 后缀；可读、跨机器稳定，评测的金标文档也用它。"""
    return path.removeprefix("zh/").removesuffix(".mdx")


def edition_of(doc_id: str) -> str:
    if doc_id.startswith("cloud/"):
        return EDITION_CLOUD
    if doc_id.startswith("self-host/"):
        return EDITION_SELF_HOST
    return EDITION_COMMON


def category_of(doc_id: str) -> str:
    parts = doc_id.split("/")
    if _USE_DIFY in parts:
        after = parts[parts.index(_USE_DIFY) + 1 :]
        if len(after) > 1:  # use-dify 下的目录名；直接放在 use-dify 下的文件归 use-dify
            return after[0]
        return _USE_DIFY
    if doc_id.startswith("self-host/deploy"):
        return "deploy"
    return parts[0]


def list_raw_files(raw_dir: Path) -> list[Path]:
    """本地已下载的语料文件，按路径排序（遍历顺序必须确定）。"""
    return sorted(path for path in raw_dir.rglob("*.mdx") if path.is_file())
