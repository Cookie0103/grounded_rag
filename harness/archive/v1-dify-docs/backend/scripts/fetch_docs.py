"""下载语料到 data/raw/：`uv run poe fetch-docs`。已存在且校验一致的文件会跳过。"""

import http.client
import logging
from urllib.parse import urlsplit

from app.core.errors import CorpusError
from app.core.logging import configure_logging
from app.ingest.corpus import CORPUS_COMMIT, RAW_DIR
from app.ingest.fetch import fetch_entries, sync_corpus

TIMEOUT_SECONDS = 60
USER_AGENT = "grounded-rag-fetch"

logger = logging.getLogger("fetch_docs")


def fetch_bytes(url: str) -> bytes:
    """只走 HTTPS；GitHub 的 API 和 raw 地址都不需要重定向。"""
    parts = urlsplit(url)
    target = parts.path + (f"?{parts.query}" if parts.query else "")
    connection = http.client.HTTPSConnection(parts.netloc, timeout=TIMEOUT_SECONDS)
    try:
        connection.request("GET", target, headers={"User-Agent": USER_AGENT})
        response = connection.getresponse()
        if response.status != http.HTTPStatus.OK:
            raise CorpusError(f"下载失败 {response.status}：{url}")
        return response.read()
    finally:
        connection.close()


def main() -> None:
    configure_logging("INFO")
    entries = fetch_entries(fetch_bytes)
    logger.info("语料 commit %s，共 %d 篇", CORPUS_COMMIT[:7], len(entries))
    stats = sync_corpus(entries, RAW_DIR, fetch_bytes)
    if stats.downloaded == 0:
        logger.info("已存在，跳过：%d 篇都已下载且校验一致（%s）", stats.skipped, RAW_DIR)
    else:
        logger.info("下载 %d 篇，跳过 %d 篇 → %s", stats.downloaded, stats.skipped, RAW_DIR)


if __name__ == "__main__":
    main()
