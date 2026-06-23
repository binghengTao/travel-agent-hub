"""
旅行助手 源码组件。


"""

from fastapi import APIRouter, Depends

from app.api.deps import providers
from app.services.model_provider import ProviderRegistry

router = APIRouter()


@router.get("")
async def model_catalog(registry: ProviderRegistry = Depends(providers)) -> dict:
    """说明：model_catalog 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return registry.model_catalog()
