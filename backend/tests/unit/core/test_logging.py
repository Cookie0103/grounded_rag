import logging

import pytest

from app.core.logging import configure_logging
from app.core.trace import trace_id_var


def test_log_records_carry_the_current_trace_id(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    token = trace_id_var.set("trace-abc")
    try:
        logging.getLogger("demo").info("hello")
    finally:
        trace_id_var.reset(token)

    assert "trace=trace-abc" in capsys.readouterr().err


def test_log_level_is_applied() -> None:
    configure_logging("warning")

    assert logging.getLogger().level == logging.WARNING
