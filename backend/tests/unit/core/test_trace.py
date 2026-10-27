import pytest

from app.core.trace import is_valid_trace_id, new_trace_id


def test_new_trace_id_is_valid_and_unique() -> None:
    first, second = new_trace_id(), new_trace_id()

    assert first != second
    assert is_valid_trace_id(first)


@pytest.mark.parametrize("value", ["abc-123", "A" * 64, "0"])
def test_valid_trace_ids_are_accepted(value: str) -> None:
    assert is_valid_trace_id(value)


@pytest.mark.parametrize("value", ["", "A" * 65, "has space", "semi;colon", "中文", "a\nb"])
def test_invalid_trace_ids_are_rejected(value: str) -> None:
    assert not is_valid_trace_id(value)
