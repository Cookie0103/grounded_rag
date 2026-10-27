from unittest.mock import MagicMock

import pytest
from langfuse import Langfuse
from pydantic import RootModel

from app.core.config import Settings
from app.core.records import TraceRecord
from app.orchestration.models import Step, StepDetails
from app.providers.cloud_trace import CloudTracer, build_cloud_tracer


def test_missing_credentials_do_not_initialize_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = MagicMock()
    monkeypatch.setattr("app.providers.cloud_trace.Langfuse", factory)
    cloud = build_cloud_tracer(
        Settings(_env_file=None, langfuse_public_key=None, langfuse_secret_key=None)
    )

    with cloud.observe("问", "local-trace") as run:
        run.step(Step(name="retrieve", ms=12))

    factory.assert_not_called()


async def test_cloud_keeps_step_details_expected_answer_and_local_trace_id() -> None:
    client = MagicMock(spec=Langfuse)
    span = client.start_as_current_observation.return_value.__enter__.return_value
    cloud = CloudTracer(client)
    step = Step(name="generate", ms=25, details=StepDetails(context="证据", output="初次回答"))

    with cloud.observe("问题", "local-trace", expected=RootModel({"nuggets": ["期望要点"]})) as run:
        run.step(step)
        run.finish(
            TraceRecord(trace_id="local-trace", question="问题", route="MULTI", answer="答案")
        )
    await cloud.close()

    arguments = client.start_as_current_observation.call_args.kwargs
    assert arguments["input"]["expected"] == {"nuggets": ["期望要点"]}
    assert arguments["trace_context"]["trace_id"] == Langfuse.create_trace_id(seed="local-trace")
    output = span.start_observation.call_args.kwargs["output"]
    assert output["details"]["context"] == "证据"
    assert output["details"]["output"] == "初次回答"
    assert span.update.call_args.kwargs["output"] == "答案"
    assert span.update.call_args.kwargs["metadata"]["trace_id"] == "local-trace"
    client.shutdown.assert_called_once()


async def test_cloud_failures_do_not_interrupt_local_work() -> None:
    client = MagicMock(spec=Langfuse)
    client.start_as_current_observation.side_effect = RuntimeError("unavailable")
    client.shutdown.side_effect = OSError("offline")
    cloud = CloudTracer(client)

    with cloud.observe("问", "trace") as run:
        run.step(Step(name="retrieve", ms=1))
        run.finish(TraceRecord(trace_id="trace", question="问", route="SINGLE", answer="本地答案"))
    await cloud.close()


def test_cloud_step_failure_still_allows_final_answer_record() -> None:
    client = MagicMock(spec=Langfuse)
    span = client.start_as_current_observation.return_value.__enter__.return_value
    span.start_observation.side_effect = RuntimeError("queue down")

    with CloudTracer(client).observe("问", "trace") as run:
        run.step(Step(name="retrieve", ms=1))
        run.finish(TraceRecord(trace_id="trace", question="问", route="SINGLE", answer="答案"))

    assert span.update.call_args.kwargs["output"] == "答案"
