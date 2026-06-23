"""
旅行助手 源码组件。


"""

from fastapi import APIRouter, Depends

from app.api.deps import current_user, sessions
from app.core.response import success
from app.services.auth_service import AuthenticatedUser
from app.services.session_store import SessionStore

router = APIRouter()


@router.get("/{session_id}")
async def get_history(
    session_id: str,
    limit: int = 50,
    store: SessionStore = Depends(sessions),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：get_history 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    messages = await store.history(session_id, limit=limit, user_id=user.user_id)
    return success({"session_id": session_id, "user_id": user.user_id, "messages": messages})


@router.delete("/{session_id}")
async def delete_history(
    session_id: str,
    store: SessionStore = Depends(sessions),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：delete_history 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    await store.delete_history(session_id, user_id=user.user_id)
    return success({"session_id": session_id, "user_id": user.user_id, "deleted": True})
