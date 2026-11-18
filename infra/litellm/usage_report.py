"""只记录网关实际返回的聊天模型用量。"""

import json
from datetime import UTC, datetime
from pathlib import Path

from litellm.integrations.custom_logger import CustomLogger

LOG_PATH = Path("/app/local-usage/phase-37-gateway-usage.jsonl")
CHAT_MODELS = {"small", "deepseek-v4-pro"}


class LocalUsageReport(CustomLogger):
    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        params = kwargs.get("litellm_params") or {}
        metadata = params.get("metadata") or {}
        observed_model = getattr(response_obj, "model", None) or str(kwargs.get("model", ""))
        model = metadata.get("model_group") or observed_model
        if model not in CHAT_MODELS and "qwen3:4b-instruct" in observed_model:
            model = "small"
        if model not in CHAT_MODELS:
            return
        complete = kwargs.get("complete_streaming_response") or response_obj
        usage = getattr(complete, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None)
        output_tokens = getattr(usage, "completion_tokens", None)
        request_id = getattr(complete, "id", None) or kwargs.get("litellm_call_id")
        if not request_id or not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
            return
        entry = {
            "request_id": request_id,
            "model": model,
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "observed_at": datetime.now(UTC).isoformat(),
        }
        with LOG_PATH.open("a", encoding="utf-8") as output:
            output.write(json.dumps(entry) + "\n")


usage_report = LocalUsageReport()
