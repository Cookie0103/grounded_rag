"""运行阶段 30 的合成日文意图冒烟与网关验证。"""

import argparse
import asyncio
import json
import logging
from math import ceil
from statistics import median
from time import perf_counter

from app.core.config import get_settings
from app.providers.base import ChatMessage, ChatTier
from app.providers.deepseek import OpenAIChat
from app.providers.factory import get_chat_model

logger = logging.getLogger(__name__)

# 本地冒烟题全部是 synthetic，不用于正式评测。
CASES = (
    ("今月の返済額を確認してもらえますか。", "照会"),
    ("契約中の住宅ローンの残高を教えてください。", "照会"),
    ("次の引き落としは何日ですか。", "照会"),
    ("私の契約に適用されている金利は何％ですか。", "照会"),
    ("私の口座で返済の遅れが記録されていますか。", "照会"),
    ("繰上返済を申し込む手順を教えてください。", "規程"),
    ("年末残高証明書を再発行するにはどうしますか。", "規程"),
    ("固定金利から変動金利へ切り替える手続きはありますか。", "規程"),
    ("住宅ローンを完済した後に必要な手続きは何ですか。", "規程"),
    ("団体信用生命保険の保障内容はどこで確認できますか。", "規程"),
    ("こんにちは。", "雑談"),
    ("ありがとうございます。助かりました。", "雑談"),
    ("今日は冷えますね。", "雑談"),
    ("挨拶だけです。よろしくお願いします。", "雑談"),
    ("明日の天気はどうですか。", "雑談"),
    ("前回の説明が違っていて納得できません。", "苦情"),
    ("対応がひどかったので責任者と話したいです。", "苦情"),
    ("何度電話しても折り返しがなく、困っています。正式に苦情を申し立てたいです。", "苦情"),
    ("窓口の案内で損害が出ました。苦情として受け付けてください。", "苦情"),
    ("私の返済額を勝手に変更されたと思います。この対応に抗議します。", "苦情"),
)

INSTRUCTION = (
    "住宅ローン窓口への発話を、照会（個別の契約・残高・返済・金利・延滞）、"
    "規程（一般の手続き・条件）、雑談（挨拶や業務外の話題）、苦情（不満や抗議）の"
    'いずれかに分類してください。JSON オブジェクト {"intent":"分類名"} だけを返してください。'
)
P95_QUANTILE = 0.95
GATEWAY_TIERS: tuple[ChatTier, ...] = ("small", "large")


async def _benchmark(tag: str, base_url: str) -> None:
    model = OpenAIChat(api_key="ollama", base_url=base_url, model=tag, is_free=True)
    system = ChatMessage(role="system", content=INSTRUCTION)
    await model.complete(
        [system, ChatMessage(role="user", content="返済手続きの一般的な流れを知りたいです。")],
        json_mode=True,
    )
    timings = []
    correct = 0
    for index, (question, expected) in enumerate(CASES, 1):
        start = perf_counter()
        response = await model.complete(
            [system, ChatMessage(role="user", content=question)], json_mode=True
        )
        elapsed_ms = (perf_counter() - start) * 1000
        timings.append(elapsed_ms)
        try:
            parsed = json.loads(response.text)
        except json.JSONDecodeError:
            parsed = None
        actual = parsed.get("intent") if isinstance(parsed, dict) else None
        correct += actual == expected
        logger.info("%02d %s → %s %.1f 毫秒", index, expected, actual, elapsed_ms)
    p95 = sorted(timings)[ceil(len(timings) * P95_QUANTILE) - 1]
    logger.info(
        "%s：准确 %d/%d，中位数 %.1f 毫秒，P95 %.1f 毫秒",
        tag,
        correct,
        len(CASES),
        median(timings),
        p95,
    )


async def _check_gateway() -> None:
    settings = get_settings().model_copy(update={"chat_model": "gateway"})
    question = ChatMessage(role="user", content="「確認しました。」とだけ答えてください。")
    for tier in GATEWAY_TIERS:
        model = get_chat_model(settings, tier=tier)
        result = await model.complete([question])
        if not result.text.strip() or min(result.prompt_tokens, result.completion_tokens) <= 0:
            raise RuntimeError(f"网关 {tier} 缺少回答或 token 用量")
        logger.info(
            "%s：%s，输入 %d tokens，输出 %d tokens，保守记账 ¥%.6f",
            tier,
            result.model,
            result.prompt_tokens,
            result.completion_tokens,
            result.cost_cny,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ollama-model", help="运行 20 条本机意图冒烟题")
    mode.add_argument("--gateway", action="store_true", help="验证大小模型档，会调用一次 DeepSeek")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434/v1")
    args = parser.parse_args()
    if args.gateway:
        asyncio.run(_check_gateway())
    else:
        asyncio.run(_benchmark(args.ollama_model, args.ollama_url))
