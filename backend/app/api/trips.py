"""
旅行助手 源码组件。


"""

from __future__ import annotations

import json
import time
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agents.supervisor import SupervisorAgent
from app.api.deps import context_builder, current_user, sessions, supervisor
from app.schemas.trips import TripPlanRequest, TripPlanResponse
from app.services.auth_service import AuthenticatedUser
from app.services.context_memory import ContextBuilder
from app.services.session_store import SessionStore

router = APIRouter()


@router.post("/plan")
async def plan_trip(
    payload: TripPlanRequest,
    agent: SupervisorAgent = Depends(supervisor),
    store: SessionStore = Depends(sessions),
    memory: ContextBuilder = Depends(context_builder),
    user: AuthenticatedUser = Depends(current_user),
) -> TripPlanResponse:
    """说明：plan_trip 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    started = time.perf_counter()
    enriched_payload = await _with_memory_context(payload, store=store, memory=memory, user=user)
    result = await agent.plan_trip(enriched_payload, trace_id=trace_id)
    await store.append(payload.session_id, "user", _plan_user_message(payload), user_id=user.user_id)
    await store.append(payload.session_id, "assistant", result.answer, user_id=user.user_id)
    await memory.compressor.compress_if_needed(user_id=user.user_id, session_id=payload.session_id, store=store)
    return TripPlanResponse(
        answer=result.answer,
        trace_id=trace_id,
        session_id=payload.session_id,
        latency_ms=int((time.perf_counter() - started) * 1000),
        verified=result.verified,
        warnings=result.warnings,
    )


@router.post("/plan/stream")
async def plan_trip_stream(
    payload: TripPlanRequest,
    agent: SupervisorAgent = Depends(supervisor),
    store: SessionStore = Depends(sessions),
    memory: ContextBuilder = Depends(context_builder),
    user: AuthenticatedUser = Depends(current_user),
) -> StreamingResponse:
    """说明：plan_trip_stream 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex

    async def event_stream():
        """说明：event_stream 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        started = time.perf_counter()
        enriched_payload = await _with_memory_context(payload, store=store, memory=memory, user=user)
        answer_parts: list[str] = []
        async for token in agent.stream_trip(enriched_payload):
            answer_parts.append(token)
            yield _sse("token", {"token": token, "trace_id": trace_id})
        answer = "".join(answer_parts)
        await store.append(payload.session_id, "user", _plan_user_message(payload), user_id=user.user_id)
        await store.append(payload.session_id, "assistant", answer, user_id=user.user_id)
        await memory.compressor.compress_if_needed(user_id=user.user_id, session_id=payload.session_id, store=store)
        yield _sse("done", {"trace_id": trace_id, "session_id": payload.session_id, "latency_ms": int((time.perf_counter() - started) * 1000)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _with_memory_context(
    payload: TripPlanRequest,
    *,
    store: SessionStore,
    memory: ContextBuilder,
    user: AuthenticatedUser,
) -> TripPlanRequest:
    """说明：_with_memory_context 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    context = await memory.build(
        user_id=user.user_id,
        session_id=payload.session_id,
        store=store,
        current_message=_plan_user_message(payload),
    )
    if not context.prompt_context:
        return payload
    preferences = (
        f"{payload.preferences or '无'}\n\n"
        "分层记忆上下文如下，请尊重用户长期偏好和最近对话，但不要暴露内部字段名：\n"
        f"{context.prompt_context}"
    )
    return payload.model_copy(update={"preferences": preferences})


def _plan_user_message(payload: TripPlanRequest) -> str:
    """说明：_plan_user_message 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return f"请从 {payload.departure} 出发，安排 {payload.destination} {payload.days} 天游。预算：{payload.budget or '未指定'}。偏好：{payload.preferences or '无'}。"


def _sse(event: str, payload: dict) -> str:
    """说明：_sse 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
