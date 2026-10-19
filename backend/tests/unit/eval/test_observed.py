from unittest.mock import MagicMock

from langfuse import Langfuse

from app.providers.cloud_trace import CloudTracer
from app.providers.fakes import FakeChatModel
from eval.dataset import Nugget, Question
from eval.observed import ObservedSystem
from eval.systems import NoRetrievalSystem


async def test_cloud_eval_includes_question_reference_and_model_answer() -> None:
    client = MagicMock(spec=Langfuse)
    span = client.start_as_current_observation.return_value.__enter__.return_value
    system = ObservedSystem(
        NoRetrievalSystem(FakeChatModel(responses=["生成答案"])), CloudTracer(client)
    )
    question = Question("dev-001", "问题", ("文档甲",), nuggets=(Nugget("正确要点", "vital"),))

    answer = await system.answer(question)

    reference = client.start_as_current_observation.call_args.kwargs["input"]["expected"]
    assert reference["gold_docs"] == ["文档甲"]
    assert reference["nuggets"] == [{"text": "正确要点", "importance": "vital"}]
    assert span.update.call_args.kwargs["output"] == "生成答案"
    assert answer.answer == "生成答案"
