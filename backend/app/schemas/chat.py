"""
旅行助手 源码组件。


"""

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """ChatMessage"""
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatRequest(BaseModel):
    """ChatRequest"""
    message: str = Field(min_length=1)
    mode: Literal["general", "rag", "agent"] = "general"
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    history: list[ChatMessage] = Field(default_factory=list)
    provider: Literal["qwen", "deepseek", "local", "auto"] = "auto"


class ChatResponse(BaseModel):
    """ChatResponse"""
    answer: str
    trace_id: str
    session_id: str
    latency_ms: int
