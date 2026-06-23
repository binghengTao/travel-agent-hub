"""
旅行助手 源码组件。


"""

from uuid import uuid4

from pydantic import BaseModel, Field


class TripPlanRequest(BaseModel):
    """TripPlanRequest"""
    departure: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    days: int = Field(default=3, ge=1, le=30)
    style: str = "\u9002\u4e2d"
    budget: str = ""
    people: str = "1"
    preferences: str = ""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    provider: str = "auto"


class TripPlanResponse(BaseModel):
    """TripPlanResponse"""
    answer: str
    trace_id: str
    session_id: str
    latency_ms: int
    verified: bool
    warnings: list[str] = Field(default_factory=list)
