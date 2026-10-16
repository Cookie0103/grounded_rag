from app.core.errors import AppError, DependencyUnavailableError


def test_app_error_keeps_message_and_defaults_to_internal_error() -> None:
    error = AppError("boom")

    assert error.message == "boom"
    assert (error.code, error.status_code) == ("INTERNAL_ERROR", 500)


def test_dependency_unavailable_maps_to_503() -> None:
    error = DependencyUnavailableError("数据库不可用")

    assert isinstance(error, AppError)
    assert (error.code, error.status_code) == ("DEPENDENCY_UNAVAILABLE", 503)
