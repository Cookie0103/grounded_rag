"""公开与合成规程共享的元数据。"""

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

PolicySource = Literal["public", "internal", "distractor"]
PolicyStatus = Literal["draft", "online", "offline"]
CorpusTier = Literal["S", "L"]


class PolicyMetadata(BaseModel):
    """以左闭右开的有效期标注当前快照和历史版本。"""

    model_config = ConfigDict(frozen=True)

    source: PolicySource
    synthetic: bool
    product_line: str = Field(min_length=1)
    policy_type: str = Field(min_length=1)
    policy_id: str = Field(min_length=1)
    effective_from: date
    effective_to: date | None = None
    status: PolicyStatus
    corpus_tier: CorpusTier
    based_on: tuple[str, ...] = ()
    source_url: str | None = None

    @model_validator(mode="after")
    def validate_policy(self) -> Self:
        """检查来源标记和版本日期在写库前自洽。"""
        if self.synthetic != (self.source != "public"):
            raise ValueError("合成标记必须与规程来源一致")
        if self.source == "internal" and not self.based_on:
            raise ValueError("合成内部规程必须引用公开来源 ID")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("失效日期必须晚于生效日期")
        if self.status == "offline" and self.effective_to is None:
            raise ValueError("下线规程必须有失效日期")
        return self


class PolicyChunk(BaseModel):
    """向量库与关键词索引共享的规程子块。"""

    id: str
    document_id: str
    heading_path: str
    text: str
    policy: PolicyMetadata
