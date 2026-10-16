"""输入护栏：只拦明显的注入、套提示词和超长输入（规则，不调用模型）。"""

import re

MAX_QUESTION_CHARS = 500
INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"忽略.{0,10}(之前|以上|上面|前面|所有).{0,10}(指令|指示|规则|提示|要求)",
        r"无视.{0,10}(指令|规则|提示|要求)",
        r"ignore\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions?|rules?|prompts?)",
        r"(system|系统)\s*(prompt|提示词|指令)",
        r"(输出|告诉我|重复|泄露|打印).{0,10}(你的|系统).{0,6}(提示词|指令|prompt)",
        r"(扮演|假装|你现在是).{0,12}(没有限制|不受限制|DAN)",
        r"jailbreak|越狱",
    )
]


def check_input(question: str) -> str | None:
    """返回拦截原因；没问题返回 None。"""
    if not question.strip():
        return "问题为空"
    if len(question) > MAX_QUESTION_CHARS:
        return f"问题超过 {MAX_QUESTION_CHARS} 字"
    for pattern in INJECTION_PATTERNS:
        if pattern.search(question):
            return "疑似提示词注入"
    return None
