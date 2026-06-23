"""
旅行助手 源码组件。


"""

from uuid import uuid4
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Source


class RagQueryRequest(BaseModel):
    """RagQueryRequest"""
    question: str = Field(min_length=1)
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    city_hint: str | None = None
    provider: str = "auto"
    scope: Literal["global", "personal", "hybrid"] = "hybrid"


class RagQueryResponse(BaseModel):
    """RagQueryResponse"""
    answer: str
    trace_id: str
    session_id: str
    latency_ms: int
    sources: list[Source]
    rerank_scores: list[float] = Field(default_factory=list)


class IngestResponse(BaseModel):
    """IngestResponse"""
    trace_id: str
    files: int
    chunks: int
    chroma_enabled: bool
    bm25_path: str
