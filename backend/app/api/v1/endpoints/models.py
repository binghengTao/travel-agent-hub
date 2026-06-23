"""
旅行助手 源码组件。


"""

from fastapi import APIRouter, Depends

from app.api.deps import current_user, providers
from app.core.response import success
from app.services.auth_service import AuthenticatedUser
from app.services.model_provider import ProviderRegistry

router = APIRouter()


@router.get("")
async def model_catalog(registry: ProviderRegistry = Depends(providers), user: AuthenticatedUser = Depends(current_user)) -> dict:
    """说明：model_catalog 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return success(registry.model_catalog())
