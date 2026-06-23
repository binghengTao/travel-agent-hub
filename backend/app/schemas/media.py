"""
旅行助手 源码组件。


"""

from uuid import uuid4

from pydantic import BaseModel, Field


class CaptionResponse(BaseModel):
    """CaptionResponse"""
    trace_id: str
    caption: str
    latency_ms: int


class CopywritingRequest(BaseModel):
    """CopywritingRequest"""
    image_caption: str
    style: str = "\u5c0f\u7ea2\u4e66"
    session_id: str = Field(default_factory=lambda: str(uuid4()))


class TextRequest(BaseModel):
    """TextRequest"""
    text: str = Field(min_length=1)
    session_id: str = Field(default_factory=lambda: str(uuid4()))


class ImageRequest(BaseModel):
    """ImageRequest"""
    prompt: str = Field(min_length=1)
    session_id: str = Field(default_factory=lambda: str(uuid4()))


class MediaJobResponse(BaseModel):
    """MediaJobResponse"""
    trace_id: str
    output_url: str | None = None
    message: str
    latency_ms: int
