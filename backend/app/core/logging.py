"""日志配置：每条日志都带 trace_id。"""

import logging

from app.core.trace import trace_id_var

NOISY_LOGGERS = ("httpx", "httpcore", "huggingface_hub")
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s trace=%(trace_id)s %(message)s"


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get()
        return True


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.addFilter(TraceIdFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    for noisy in NOISY_LOGGERS:  # 第三方库每个请求都打一行 INFO，淹没真正有用的日志
        logging.getLogger(noisy).setLevel(logging.WARNING)
