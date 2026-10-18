"""编排的输入输出类型。"""

from pydantic import BaseModel, Field

from app.retrieval.retriever import RetrievalResult

DIRECT, SINGLE, MULTI, CLARIFY, REFUSE = "DIRECT", "SINGLE", "MULTI", "CLARIFY", "REFUSE"
ROUTES = (DIRECT, SINGLE, MULTI, CLARIFY, REFUSE)

REFUSE_TEXT = "这个问题超出了 Dify 产品文档问答的范围，我没法回答。"
ABSTAIN_TEXT = "抱歉，在文档里没有找到足够的依据来回答这个问题。"


class ChatRequest(BaseModel):
    question: str
    edition: str | None = None  # self_host / cloud / None（不限制）
    session_id: str | None = None


class Citation(BaseModel):
    index: int
    document_id: str
    heading_path: str


class StepDetails(BaseModel):
    """检索、证据判断和实际生成上下文，随步骤一起落盘。"""

    retrievals: list[RetrievalResult] = Field(default_factory=list)
    sufficient: bool | None = None
    missing: str | None = None
    context: str | None = None


class Step(BaseModel):
    name: str
    ms: float
    note: str = ""
    details: StepDetails | None = None


class ChatResponse(BaseModel):
    answer: str
    route: str
    citations: list[Citation] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    retrieved_docs: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    cost_cny: float = 0.0
    abstained: bool = False
    degraded: bool = False  # 精排或生成不可用，已降级
    cached: bool = False
    standalone_question: str | None = None  # 追问独立化之后的问题；没改写就是 None
