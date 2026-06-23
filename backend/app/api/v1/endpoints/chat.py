"""
旅行助手 源码组件。


"""

from __future__ import annotations

import time
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.agents.supervisor import SupervisorAgent
from app.api.deps import context_builder, current_user, sessions, supervisor
from app.core.response import success
from app.schemas.chat import ChatRequest
from app.services.auth_service import AuthenticatedUser
from app.services.context_memory import ContextBuilder
from app.services.model_provider import ModelMessage
from app.services.session_store import SessionStore

router = APIRouter()


@router.post("")
async def chat(
    payload: ChatRequest,
    agent: SupervisorAgent = Depends(supervisor),
    store: SessionStore = Depends(sessions),
    memory: ContextBuilder = Depends(context_builder),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：chat 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
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
        sources = [source.model_dump() for source in result.sources]
        tool_calls = [call.model_dump() for call in result.tool_calls]
    elif payload.mode == "rag":
        rag_response = await agent.rag.query(
            payload.message,
            session_id=payload.session_id,
            trace_id=trace_id,
            provider_name=payload.provider,
        )
        answer = rag_response.answer
        sources = [source.model_dump() for source in rag_response.sources]
        tool_calls = []
    else:
        provider = agent.providers.resolve(payload.provider)
        messages = [
            ModelMessage(
                role="system",
                content=(
                    "你是 旅行助手 的中文旅游助手。默认使用中文回答。"
                    "如果上下文中有用户偏好、事实记忆或会话摘要，请在不泄露内部字段的前提下合理使用。"
                ),
            )
        ]
        if context.prompt_context:
            messages.append(ModelMessage(role="system", content=f"分层记忆上下文:\n{context.prompt_context}"))
        messages.append(ModelMessage(role="user", content=payload.message))
        answer = await provider.chat(messages)
        sources = []
        tool_calls = []

    await store.append(payload.session_id, "user", payload.message, user_id=user_id)
    await store.append(payload.session_id, "assistant", answer, user_id=user_id)
    await memory.compressor.compress_if_needed(user_id=user_id, session_id=payload.session_id, store=store)
    return success(
        {
            "trace_id": trace_id,
            "session_id": payload.session_id,
            "user_id": user_id,
            "answer": answer,
            "sources": sources,
            "tool_calls": tool_calls,
            "memory": {
                "summary_exists": bool(context.summary),
                "fact_count": len(context.facts),
                "token_estimate": context.token_estimate,
            },
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    )


def _message_with_context(message: str, prompt_context: str) -> str:
    """说明：_message_with_context 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    if not prompt_context:
        return message
    return f"{message}\n\n分层记忆上下文:\n{prompt_context}"
