"""输入护栏：只拦明显的注入、套提示词和超长输入（规则，不调用模型）。"""

import re
import unicodedata

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
        r"(これまで|ここまで|以前|今まで|先ほど|上記|前の|従来|すべての|全ての)"
        r"[^。！？!?]{0,12}(指示|命令|ルール|プロンプト|制約)"
        r"[^。！？!?]{0,12}(無視|忘れ|破棄|取り消|上書き|従わな)",
        r"(システム|開発者)\s*(プロンプト|メッセージ|命令|指示)",
        r"(内部指示|隠された指示|隠しプロンプト)"
        r"[^。！？!?]{0,15}(開示|出力|表示|公開|見せ|教え|書き出)",
        r"(制約|制限|ルール)(がない|のない|なしの|を持たない)"
        r"[^。！？!?]{0,15}(演じ|なりき|振る舞|ふるま|になって)",
    )
]


def check_input(question: str) -> str | None:
    """返回拦截原因；没问题返回 None。"""
    if not question.strip():
        return "问题为空"
    if len(question) > MAX_QUESTION_CHARS:
        return f"问题超过 {MAX_QUESTION_CHARS} 字"
    normalized = unicodedata.normalize("NFKC", question)
    for pattern in INJECTION_PATTERNS:
        if pattern.search(normalized):
            return "疑似提示词注入"
    return None
