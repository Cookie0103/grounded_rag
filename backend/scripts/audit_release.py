"""核查公开仓库候选工作树中的链接、配置样例和敏感材料迹象。"""

import asyncio
import logging
import re
import shutil
from collections import Counter
from functools import cache
from itertools import pairwise
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token

from app.core.config import REPO_ROOT, Settings

logger = logging.getLogger(__name__)
_MARKDOWN = MarkdownIt("commonmark").enable("table")
_DOC_TYPES = {".md", ".mdx"}
_TEXT_TYPES = _DOC_TYPES | {
    "",
    ".example",
    ".ini",
    ".json",
    ".jsonl",
    ".lock",
    ".mako",
    ".py",
    ".sha256",
    ".sql",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
_ARCHIVE = Path("harness/archive")
_FIXTURES = Path("backend/tests/fixtures")
_RAW_TYPES = {".docx", ".htm", ".html", ".mhtml", ".pdf", ".webarchive"}
_KEY_TYPES = {".key", ".p12", ".pem", ".pfx"}
_SEALED_NAME = re.compile(
    r"(?:sealed|封存)|(?:^|[-_])(?:policy-test|test-cases|test-questions)(?:[-_.]|$)", re.I
)
_REFERENCE_NAME = re.compile(r"参考方案原文|reference[-_ ](?:design|proposal|solution)", re.I)
_CONTENT_MARKERS = {
    "私钥块": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "API 密钥形态": re.compile(
        r"(?<![\w-])(?:sk-(?:lf-)?[A-Za-z0-9_-]{24,}|app-[A-Za-z0-9]{24,}"
        r"|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16})(?![\w-])"
    ),
    "银行页面快照": re.compile(r"<(?:link|meta)\b[^>]*(?:canonical|og:url)[^>]*sonybank\.jp", re.I),
}


async def _git_paths(*args: str) -> tuple[Path, ...]:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("未找到 Git，无法列出仓库文件")
    process = await asyncio.create_subprocess_exec(
        git, "ls-files", "-z", *args, cwd=REPO_ROOT, stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
    if process.returncode != 0:
        raise RuntimeError("无法列出仓库文件")
    return tuple(Path(path) for path in stdout.decode().split("\0") if path)


def _protected(path: Path) -> bool:
    return (
        bool({"data", ".cache"} & set(path.parts))
        or (path.name.startswith(".env") and path.name != ".env.example")
        or any(_SEALED_NAME.search(part) for part in path.parts)
    )


def _safe_file(root: Path, path: Path) -> bool:
    resolved = (root / path).resolve()
    return (
        not _protected(path)
        and resolved.is_relative_to(root)
        and not _protected(resolved.relative_to(root))
        and resolved.is_file()
    )


@cache
def _markdown(root: Path, path: Path) -> tuple[Token, ...]:
    return tuple(_MARKDOWN.parse((root / path).read_text(encoding="utf-8")))


def _slug(token: Token) -> str:
    text = "".join(
        node.content for node in token.children or [] if node.type in {"text", "code_inline"}
    )
    return re.sub(r"[^\w -]", "", text.lower()).replace(" ", "-")


def _anchors(root: Path, path: Path) -> set[str]:
    used: Counter[str] = Counter()
    anchors = set()
    for token, text in pairwise(_markdown(root, path)):
        if token.type == "heading_open":
            slug = _slug(text)
            count = used[slug]
            anchors.add(f"{slug}-{count}" if count else slug)
            used[slug] += 1
    return anchors


def _local_links(root: Path, path: Path) -> list[tuple[int, str, str]]:
    links = []
    line = 1
    for token in _markdown(root, path):
        if token.map:
            line = token.map[0] + 1
        for child in token.children or []:
            address = child.attrGet("href") or child.attrGet("src")
            if isinstance(address, str) and address:
                url = urlsplit(address)
                if not url.scheme and not url.netloc and not url.path.startswith("/"):
                    links.append((line, unquote(url.path), unquote(url.fragment)))
    return links


def _link_problem(root: Path, path: Path, fragment: str, published: set[Path]) -> str:
    if path not in published or not (root / path).exists():
        return "相对目标缺失"
    if (
        fragment
        and path.suffix in _DOC_TYPES
        and not path.is_relative_to(_ARCHIVE)
        and _safe_file(root, path)
        and fragment not in _anchors(root, path)
    ):
        return "相对目标锚点缺失"
    return ""


def _check_documents(root: Path, files: tuple[Path, ...]) -> tuple[list[str], int, int]:
    published = set(files) | {parent for path in files for parent in path.parents}
    findings = []
    documents = links = 0
    for path in files:
        if (
            path.suffix not in _DOC_TYPES
            or path.is_relative_to(_ARCHIVE)
            or path.is_relative_to(_FIXTURES)
            or not _safe_file(root, path)
        ):
            continue
        documents += 1
        for line, address, fragment in _local_links(root, path):
            links += 1
            target = ((root / path.parent / address) if address else (root / path)).resolve()
            relative = target.relative_to(root) if target.is_relative_to(root) else target
            if problem := _link_problem(root, relative, fragment, published):
                findings.append(f"{path}:{line} {problem} {relative} {fragment}")
    return findings, documents, links


def _publication_path_marker(path: Path) -> str:
    if _protected(path):
        return "本地数据、配置、缓存或封存路径"
    if path.suffix.lower() in _RAW_TYPES or _REFERENCE_NAME.search(path.name):
        return "原始页面或参考文件形态"
    if path.suffix.lower() in _KEY_TYPES:
        return "密钥文件形态"
    return ""


def _check_publication(root: Path, files: tuple[Path, ...]) -> tuple[list[str], int, int]:
    findings = []
    examined = skipped = 0
    for path in files:
        if marker := _publication_path_marker(path):
            findings.append(f"{path} {marker}")
        if path.suffix not in _TEXT_TYPES or not _safe_file(root, path):
            skipped += 1
            continue
        text = (root / path).read_text(encoding="utf-8", errors="replace")
        examined += 1
        findings.extend(
            f"{path} {marker}"
            for marker, pattern in _CONTENT_MARKERS.items()
            if pattern.search(text)
        )
    return findings, examined, skipped


def _check_env(root: Path) -> tuple[list[str], int]:
    example = (root / ".env.example").read_text(encoding="utf-8")
    keys = Counter(re.findall(r"^([A-Z][A-Z0-9_]*)\s*=", example, flags=re.MULTILINE))
    expected = {field.upper() for field in Settings.model_fields}
    findings = [f".env.example 缺少字段 {field}" for field in sorted(expected - keys.keys())]
    findings.extend(f".env.example 多余字段 {field}" for field in sorted(keys.keys() - expected))
    findings.extend(f".env.example 重复字段 {field}" for field, count in keys.items() if count > 1)
    return findings, len(keys)


async def _run() -> int:
    tracked = await _git_paths("--cached")
    other = await _git_paths("--others", "--exclude-standard")
    files = tuple(sorted(set(tracked) | set(other)))
    link_findings, documents, links = _check_documents(REPO_ROOT, files)
    env_findings, settings = _check_env(REPO_ROOT)
    release_findings, examined, skipped = _check_publication(REPO_ROOT, tracked)
    logger.info("活动文档 %s 份，相对链接 %s 条，问题 %s 项", documents, links, len(link_findings))
    logger.info(".env.example 配置字段 %s 个，问题 %s 项", settings, len(env_findings))
    logger.info(
        "跟踪路径 %s 个，扫描文本 %s 份，跳过内容 %s 份，发现 %s 项",
        len(tracked),
        examined,
        skipped,
        len(release_findings),
    )
    for finding in [*link_findings, *env_findings, *release_findings]:
        logger.error("%s", finding)
    return int(bool(link_findings or env_findings or release_findings))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(asyncio.run(_run()))
