from scripts.stream_client import Event, StreamResult


def test_client_ignores_duplicate_events_and_applies_retract_before_final_answer() -> None:
    result = StreamResult("example-id")
    base = {"response_id": result.response_id}
    first = Event(1, "delta", {**base, "text": "誤った回答"})
    result.receive(first, 30)
    result.receive(first, 31)
    result.receive(
        Event(
            2,
            "retract",
            {**base, "replacement": "回答を控えます。", "reasons": ["unsupported_number"]},
        ),
        39,
    )
    result.receive(Event(3, "answer", {**base, "answer": "回答を控えます。"}), 40)

    assert result.text == "回答を控えます。"
    assert result.last_id == 3
    assert result.first_delta_ms == 30
    assert result.total_ms == 40
    assert result.retractions == [("unsupported_number",)]
