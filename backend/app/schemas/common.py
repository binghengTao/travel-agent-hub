"""
旅行助手 源码组件。


"""

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Source"""
    source: str
    city: str | None = None
    page: int | None = None
    chunk_id: str
    score: float | None = None
    preview: str = ""
    scope: str | None = None
    owner_id: str | None = None
    source_type: str | None = None
    trust_level: str | None = None


class ToolCall(BaseModel):
    """ToolCall"""
    name: str
    arguments: dict = Field(default_factory=dict)
    result: str | dict | None = None
    error: str | None = None


