"""从本机公开快照生成带标记的日文合成语料。"""

import argparse
import logging
from collections import Counter
from datetime import date

from app.core.config import DATA_DIR
from app.ingest.policy_corpus import TARGET_DOCUMENTS, build_policy_corpus

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True, help="语料快照日期")
    parser.add_argument("--target-documents", type=int, default=TARGET_DOCUMENTS)
    args = parser.parse_args()
    items = build_policy_corpus(DATA_DIR, as_of=args.as_of, target_documents=args.target_documents)
    logger.info(
        "语料篇数 %s，清单 data/policy_index.jsonl", dict(Counter(x.policy.source for x in items))
    )
