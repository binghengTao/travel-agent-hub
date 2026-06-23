"""
旅行助手 源码组件。


"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import current_user, rag_service, user_kb_service
from app.core.response import success
from app.rag.retriever import RagService
from app.schemas.rag import RagQueryRequest, RagQueryResponse
from app.services.auth_service import AuthenticatedUser
from app.services.model_provider import ModelMessage
from app.services.user_kb_service import UserKbService

router = APIRouter()


class RagEvaluateRequest(BaseModel):
    """RagEvaluateRequest"""
    question: str = Field(min_length=1)
    expected_source_keyword: str = ""
    city_hint: str | None = None
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    provider: str = "auto"


@router.post("/ask")
async def ask(
    payload: RagQueryRequest,
    rag: RagService = Depends(rag_service),
    user_kb: UserKbService = Depends(user_kb_service),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：ask 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    if payload.scope == "personal":
        result = await user_kb.query(
            payload.question,
            user_id=user.user_id,
            session_id=payload.session_id,
            trace_id=trace_id,
            provider_name=payload.provider,
            city_hint=payload.city_hint,
        )
        data = result.model_dump()
    elif payload.scope == "global":
        result = await rag.query(
            payload.question,
            session_id=payload.session_id,
            trace_id=trace_id,
            provider_name=payload.provider,
            city_hint=payload.city_hint,
        )
        data = result.model_dump()
    else:
        personal = await user_kb.query(
            payload.question,
            user_id=user.user_id,
            session_id=payload.session_id,
            trace_id=trace_id,
            provider_name=payload.provider,
            city_hint=payload.city_hint,
        )
        global_result = await rag.query(
            payload.question,
            session_id=payload.session_id,
            trace_id=trace_id,
            provider_name=payload.provider,
            city_hint=payload.city_hint,
        )
        result = await _compose_hybrid_answer(payload, personal, global_result, rag)
        data = result.model_dump()
    data["user_id"] = user.user_id
    data["scope"] = payload.scope
    return success(data)


@router.post("/evaluate")
async def evaluate(
    payload: RagEvaluateRequest,
    rag: RagService = Depends(rag_service),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：evaluate 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    result = await rag.query(
        payload.question,
        session_id=payload.session_id,
        trace_id=trace_id,
        provider_name=payload.provider,
        city_hint=payload.city_hint,
    )
    sources = [source.model_dump() for source in result.sources]
    matched_expected = True
    if payload.expected_source_keyword:
        matched_expected = any(
            payload.expected_source_keyword in source["source"] or payload.expected_source_keyword in source["preview"]
            for source in sources
        )
    lower_answer = result.answer.lower()
    return success(
        {
            "trace_id": trace_id,
            "user_id": user.user_id,
            "question": payload.question,
            "answer": result.answer,
            "metrics": {
                "latency_ms": result.latency_ms,
                "source_count": len(sources),
                "has_sources": bool(sources),
                "has_citation_text": any(marker in lower_answer for marker in ["source", "citation", "reference", "pdf", "来源", "引用"]),
                "matched_expected_source": matched_expected,
                "avg_rerank_score": sum(result.rerank_scores) / len(result.rerank_scores) if result.rerank_scores else 0,
            },
            "sources": sources,
            "rerank_scores": result.rerank_scores,
        }
    )


async def _compose_hybrid_answer(
    payload: RagQueryRequest,
    personal: RagQueryResponse,
    global_result: RagQueryResponse,
    rag: RagService,
) -> RagQueryResponse:
    """说明：_compose_hybrid_answer 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    provider = rag.providers.resolve(payload.provider)
    personal_sources = "\n".join(f"- {source.source}: {source.preview}" for source in personal.sources) or "无个人文件证据"
    global_sources = "\n".join(f"- {source.source}: {source.preview}" for source in global_result.sources) or "无公共知识库证据"
    prompt = (
        "你是 旅行助手 的混合 RAG AnswerAgent。请优先使用用户个人文件，其次使用公共知识库。"
        "如果两类证据冲突，请说明冲突，并优先采用更新、更可信、更贴近用户问题的证据。"
        "回答必须使用中文，并在结尾按“个人文件来源”和“公共知识库来源”分别列出引用。\n\n"
        f"问题:{payload.question}\n\n"
        f"个人文件初步回答:\n{personal.answer}\n\n个人文件证据:\n{personal_sources}\n\n"
        f"公共知识库初步回答:\n{global_result.answer}\n\n公共知识库证据:\n{global_sources}"
    )
    answer = await provider.chat([ModelMessage(role="user", content=prompt)], model=rag.providers.settings.qwen_chat_model, temperature=0.2)
    return RagQueryResponse(
        answer=answer,
        trace_id=global_result.trace_id,
        session_id=payload.session_id,
        latency_ms=personal.latency_ms + global_result.latency_ms,
        sources=[*personal.sources, *global_result.sources],
        rerank_scores=[*personal.rerank_scores, *global_result.rerank_scores],
    )
