"""
旅行助手 源码组件。


"""

from __future__ import annotations

import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.graph import TravelAgentGraph
from app.agents.supervisor import SupervisorAgent
from app.api.deps import agent_graph, context_builder, current_user, sessions, supervisor
from app.core.response import success
from app.services.auth_service import AuthenticatedUser
from app.services.context_memory import ContextBuilder
from app.services.session_store import SessionStore

router = APIRouter()


class AgentChatRequest(BaseModel):
    """AgentChatRequest"""
    message: str = Field(min_length=1)
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str | None = None
    provider: str = "auto"


@router.post("/chat")
async def agent_chat(
    payload: AgentChatRequest,
    agent: SupervisorAgent = Depends(supervisor),
    graph: TravelAgentGraph = Depends(agent_graph),
    store: SessionStore = Depends(sessions),
    memory: ContextBuilder = Depends(context_builder),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：agent_chat 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    run_id = f"run_{trace_id[:12]}"
    started = time.perf_counter()
    user_id = user.user_id
    profile = await store.get_profile(user_id)
    context = await memory.build(
        user_id=user_id,
        session_id=payload.session_id,
        store=store,
        current_message=payload.message,
        profile=profile,
    )
    result = await graph.run(
        _message_with_context(payload.message, context.prompt_context),
        session_id=payload.session_id,
        trace_id=trace_id,
        run_id=run_id,
        provider=payload.provider,
        profile=profile,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    intent = result.metadata.get("intent", {"intent": result.route})
    data = {
        "run_id": run_id,
        "trace_id": trace_id,
        "session_id": payload.session_id,
        "user_id": user_id,
        "answer": result.answer,
        "intent": intent.get("intent", result.route) if isinstance(intent, dict) else result.route,
        "destination": intent.get("destination") if isinstance(intent, dict) else None,
        "tool_calls": [call.model_dump() for call in result.tool_calls],
        "sources": [source.model_dump() for source in result.sources],
        "plan": result.metadata.get("plan"),
        "steps": result.steps,
        "profile": profile,
        "memory": {
            "summary_exists": bool(context.summary),
            "fact_count": len(context.facts),
            "recent_message_count": len(context.recent_messages),
            "token_estimate": context.token_estimate,
            "max_context_tokens": memory.settings.max_context_tokens,
        },
        "verified": result.verified,
        "warnings": result.warnings,
        "latency_ms": latency_ms,
        "graph_engine": result.metadata.get("graph_engine", "langgraph_stategraph"),
        "retry_count": result.metadata.get("retry_count", 0),
    }
    await store.append(payload.session_id, "user", payload.message, user_id=user_id)
    await store.append(payload.session_id, "assistant", result.answer, user_id=user_id)
    await memory.compressor.compress_if_needed(user_id=user_id, session_id=payload.session_id, store=store)
    await store.save_run(run_id, data)
    return success(data)


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    store: SessionStore = Depends(sessions),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：get_run 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    data = await store.get_run(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Agent run not found.")
    if data.get("user_id") != user.user_id:
        raise HTTPException(status_code=403, detail="This run belongs to another user.")
    return success(data)


def _message_with_context(message: str, prompt_context: str) -> str:
    """说明：_message_with_context 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    if not prompt_context:
        return message
    return (
        f"{message}\n\n"
        "以下是系统为本轮 Agent 调度准备的分层记忆上下文。请优先尊重用户明确偏好，"
        "不要编造未被 RAG、网页搜索或工具结果支持的实时信息。\n"
        f"{prompt_context}"
    )
