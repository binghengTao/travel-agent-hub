"""
旅行助手 源码组件。


"""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field


class UserTextDocumentRequest(BaseModel):
    """UserTextDocumentRequest"""
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1)
    city: str = ""
    tags: list[str] = Field(default_factory=list)
    source_note: str = "user_note"
    trust_level: str = "user_provided"


class UserKbQueryRequest(BaseModel):
    """UserKbQueryRequest"""
    question: str = Field(min_length=1)
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    city_hint: str | None = None
    provider: str = "auto"
