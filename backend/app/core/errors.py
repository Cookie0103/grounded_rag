"""应用异常：错误码和状态码都定义在这里，别处不写状态码。"""


class AppError(Exception):
    """所有可预期错误的基类；API 层统一转成 `{"error": {...}, "trace_id": ...}`。"""

    code = "INTERNAL_ERROR"
    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DependencyUnavailableError(AppError):
    """数据库、模型等外部依赖不可用。"""

    code = "DEPENDENCY_UNAVAILABLE"
    status_code = 503


class CorpusError(AppError):
    """语料下载或解析失败（数量不对、文件损坏、缺少必填字段等）。"""

    code = "CORPUS_ERROR"
