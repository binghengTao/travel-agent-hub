"""
旅行助手 源码组件。


"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Form, UploadFile

from app.api.deps import current_user, user_kb_service
from app.core.response import success
from app.schemas.user_kb import UserKbQueryRequest, UserTextDocumentRequest
from app.services.auth_service import AuthenticatedUser
from app.services.kb_governance import parse_tags
from app.services.user_kb_service import UserKbService

router = APIRouter()


@router.get("/documents")
async def documents(
    service: UserKbService = Depends(user_kb_service),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：documents 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return success(service.list_documents(user.user_id))


@router.post("/upload")
async def upload_document(
    upload: UploadFile,
    city: str = Form(""),
    tags: str = Form(""),
    service: UserKbService = Depends(user_kb_service),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：upload_document 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    doc = await service.upload_document(user_id=user.user_id, upload=upload, city=city, tags=parse_tags(tags))
    return success({"doc": doc, "needs_reindex": True})


@router.post("/register-text")
async def register_text(
    payload: UserTextDocumentRequest,
    service: UserKbService = Depends(user_kb_service),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：register_text 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    doc = service.register_text(user_id=user.user_id, payload=payload)
    return success({"doc": doc, "needs_reindex": True})


@router.post("/reindex")
async def reindex(
    service: UserKbService = Depends(user_kb_service),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：reindex 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return success(await service.rebuild(user.user_id))


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    service: UserKbService = Depends(user_kb_service),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：delete_document 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return success(service.delete_document(user_id=user.user_id, doc_id=doc_id))


@router.post("/query")
async def query(
    payload: UserKbQueryRequest,
    service: UserKbService = Depends(user_kb_service),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：query 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    result = await service.query(
        payload.question,
        user_id=user.user_id,
        session_id=payload.session_id,
        trace_id=trace_id,
        provider_name=payload.provider,
        city_hint=payload.city_hint,
    )
    data = result.model_dump()
    data["user_id"] = user.user_id
    data["scope"] = "personal"
    return success(data)
