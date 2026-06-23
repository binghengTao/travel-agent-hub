"""
旅行助手 源码组件。


"""

from uuid import uuid4

from fastapi import APIRouter, Depends

from app.api.deps import rag_service
from app.core.security import require_admin
from app.rag.retriever import RagService
from app.schemas.rag import IngestResponse

router = APIRouter()


@router.post("/rebuild", dependencies=[Depends(require_admin)])
async def rebuild(rag: RagService = Depends(rag_service)) -> IngestResponse:
    """说明：rebuild 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    result = await rag.indexer.rebuild()
    return IngestResponse(trace_id=trace_id, **result)
