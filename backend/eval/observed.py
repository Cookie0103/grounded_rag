"""评测的云端副本：同一道题的期望要点、检索证据和回答放在一次观测中。"""

from pydantic import RootModel

from app.core.records import TraceRecord
from app.core.trace import new_trace_id
from app.providers.cloud_trace import CloudTracer
from eval.dataset import Question
from eval.systems import System, SystemAnswer


class ObservedSystem:
    def __init__(self, system: System, cloud: CloudTracer) -> None:
        self._system = system
        self._cloud = cloud
        self.name = system.name

    async def answer(self, question: Question) -> SystemAnswer:
        """保持评测与评分不变，只发送已有题目和结果。"""
        trace_id = new_trace_id()
        with self._cloud.observe(
            question.question,
            trace_id,
            name=f"eval/{self.name}",
            expected=RootModel[Question](question),
        ) as run:
            answer = await self._system.answer(question)
            for step in answer.steps:
                run.step(step)
            run.finish(
                TraceRecord(
                    trace_id=trace_id,
                    question=question.question,
                    route=answer.route or self.name,
                    edition=question.edition,
                    answer=answer.answer or "",
                    cost_cny=answer.cost_cny,
                    steps=[step.model_dump(mode="json") for step in answer.steps],
                    retrieved_docs=list(answer.retrieved_docs),
                )
            )
            return answer
