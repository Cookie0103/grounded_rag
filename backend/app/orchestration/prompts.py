"""提示词文件：`app/prompts/<名字>_v<版本>.md`，用 `{{名字}}` 做占位符。改提示词就新增版本文件。"""

import hashlib
import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def placeholders(name: str) -> set[str]:
    return set(PLACEHOLDER.findall((PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")))


def render(name: str, **values: str) -> str:
    """填占位符；传多了或少了都报错，免得提示词里留下没填的 `{{...}}`。"""
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    expected = set(PLACEHOLDER.findall(text))
    if expected != set(values):
        raise ValueError(f"提示词 {name} 需要 {sorted(expected)}，给了 {sorted(values)}")
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], text)


def version() -> str:
    """所有提示词内容的短哈希：缓存键里带上它，改了提示词旧缓存自动失效。"""
    digest = hashlib.sha256()
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:8]
