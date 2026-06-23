"""
旅行助手 源码组件。


"""

from __future__ import annotations

import time
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import current_user, providers
from app.core.response import success
from app.services.model_provider import ModelMessage, ProviderRegistry

router = APIRouter()


class CopywritingGenerateRequest(BaseModel):
    """CopywritingGenerateRequest"""
    topic: str = Field(default="", description="Travel topic or destination.")
    image_caption: str = ""
    style: str = "Xiaohongshu"
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    provider: str = "auto"


@router.post("/generate")
async def generate_copywriting(payload: CopywritingGenerateRequest, registry: ProviderRegistry = Depends(providers), user: AuthenticatedUser = Depends(current_user)) -> dict:
    """说明：generate_copywriting 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    started = time.perf_counter()
    prompt = (
        f"Topic: {payload.topic}\n"
        f"Image caption: {payload.image_caption}\n"
        f"Platform style: {payload.style}\n"
        "Always answer in Simplified Chinese. Generate publish-ready travel copy with a vivid scene, practical tips and a concise title."
    )
    answer = await registry.resolve(payload.provider).chat(
        [
            ModelMessage(role="system", content="You are a travel social-media copywriting expert. Always answer in Simplified Chinese."),
            ModelMessage(role="user", content=prompt),
        ],
        model=registry.settings.qwen_fast_model,
    )
    return success({"trace_id": trace_id, "session_id": payload.session_id, "answer": answer, "latency_ms": int((time.perf_counter() - started) * 1000)})
