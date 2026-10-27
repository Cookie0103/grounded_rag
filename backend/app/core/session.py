"""会话数据：多轮问答的短期记忆。存储实现在 app/db/sessions.py 和 app/orchestration/memory.py。"""

from pydantic import BaseModel, Field


class Turn(BaseModel):
    question: str
    answer: str


class Session(BaseModel):
    id: str
    edition: str | None = None  # 用户的版本：self_host / cloud
    summary: str = ""  # 更早的对话摘要
    turns: list[Turn] = Field(default_factory=list)  # 最近几轮原文
