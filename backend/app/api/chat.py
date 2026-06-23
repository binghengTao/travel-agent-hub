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
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.auth_service import AuthenticatedUser
from app.services.context_memory import ContextBuilder
from app.services.model_provider import ModelMessage
from app.services.session_store import SessionStore

router = APIRouter()


@router.post("")
async def chat_once(
    payload: ChatRequest,
    agent: SupervisorAgent = Depends(supervisor),
    store: SessionStore = Depends(sessions),
    memory: ContextBuilder = Depends(context_builder),
    user: AuthenticatedUser = Depends(current_user),
) -> ChatResponse:
    """说明：chat_once 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    started = time.perf_counter()
    user_id = user.user_id
    context = await memory.build(
        user_id=user_id,
        session_id=payload.session_id,
        store=store,
        current_message=payload.message,
    )
    if payload.mode == "agent":
        result = await agent.handle(
            _message_with_context(payload.message, context.prompt_context),
            session_id=payload.session_id,
            trace_id=trace_id,
            provider=payload.provider,
        )
        answer = result.answer
    elif payload.mode == "rag":
        result = await agent.rag.query(
            payload.message,
            session_id=payload.session_id,
            trace_id=trace_id,
            provider_name=payload.provider,
        )
        answer = result.answer
    else:
        provider = agent.providers.resolve(payload.provider)
        messages = [ModelMessage(role="system", content="你是中文旅游助手，默认使用中文回答。")]
        if context.prompt_context:
            messages.append(ModelMessage(role="system", content=f"分层记忆上下文:\n{context.prompt_context}"))
        messages.append(ModelMessage(role="user", content=payload.message))
        answer = await provider.chat(messages)
    await store.append(payload.session_id, "user", payload.message, user_id=user_id)
    await store.append(payload.session_id, "assistant", answer, user_id=user_id)
    await memory.compressor.compress_if_needed(user_id=user_id, session_id=payload.session_id, store=store)
    return ChatResponse(answer=answer, trace_id=trace_id, session_id=payload.session_id, latency_ms=_latency(started))


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    agent: SupervisorAgent = Depends(supervisor),
    store: SessionStore = Depends(sessions),
    memory: ContextBuilder = Depends(context_builder),
    user: AuthenticatedUser = Depends(current_user),
) -> StreamingResponse:
    """说明：chat_stream 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    user_id = user.user_id

    async def event_stream():
        """说明：event_stream 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        started = time.perf_counter()
        context = await memory.build(
            user_id=user_id,
            session_id=payload.session_id,
            store=store,
            current_message=payload.message,
        )
        answer_parts: list[str] = []
        if payload.mode == "general":
            provider = agent.providers.resolve(payload.provider)
            messages = [ModelMessage(role="system", content="你是中文旅游助手，默认使用中文回答。")]
            if context.prompt_context:
                messages.append(ModelMessage(role="system", content=f"分层记忆上下文:\n{context.prompt_context}"))
            messages.append(ModelMessage(role="user", content=payload.message))
            async for token in provider.stream(messages):
                answer_parts.append(token)
                yield _sse("token", {"token": token, "trace_id": trace_id})
        else:
            result = await agent.handle(
                _message_with_context(payload.message, context.prompt_context),
                session_id=payload.session_id,
                trace_id=trace_id,
                provider=payload.provider,
            )
            answer_parts.append(result.answer)
            yield _sse(
                "token",
                {
                    "token": result.answer,
                    "trace_id": trace_id,
                    "sources": [source.model_dump() for source in result.sources],
                    "tool_calls": [call.model_dump() for call in result.tool_calls],
                    "warnings": result.warnings,
                },
            )
        answer = "".join(answer_parts)
        await store.append(payload.session_id, "user", payload.message, user_id=user_id)
        await store.append(payload.session_id, "assistant", answer, user_id=user_id)
        await memory.compressor.compress_if_needed(user_id=user_id, session_id=payload.session_id, store=store)
        yield _sse("done", {"trace_id": trace_id, "session_id": payload.session_id, "latency_ms": _latency(started)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _message_with_context(message: str, prompt_context: str) -> str:
    """说明：_message_with_context 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    if not prompt_context:
        return message
    return f"{message}\n\n分层记忆上下文:\n{prompt_context}"


def _sse(event: str, payload: dict) -> str:
    """说明：_sse 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _latency(started: float) -> int:
    """说明：_latency 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return int((time.perf_counter() - started) * 1000)
