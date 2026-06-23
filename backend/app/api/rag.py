"""
旅行助手 源码组件。


"""

from uuid import uuid4

from fastapi import APIRouter, Depends

from app.api.deps import rag_service
from app.rag.retriever import RagService
from app.schemas.rag import RagQueryRequest, RagQueryResponse

router = APIRouter()


@router.post("/query")
async def query_rag(payload: RagQueryRequest, rag: RagService = Depends(rag_service)) -> RagQueryResponse:
    """说明：query_rag 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    return await rag.query(
        payload.question,
        session_id=payload.session_id,
        trace_id=trace_id,
        provider_name=payload.provider,
        city_hint=payload.city_hint,
    )
