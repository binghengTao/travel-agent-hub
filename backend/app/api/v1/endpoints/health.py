"""
旅行助手 源码组件。


"""

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.core.response import success

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict:
    """说明：health 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    redis_ok = False
    if getattr(request.app.state, "sessions", None):
        try:
            redis_ok = request.app.state.sessions._redis is not None
        except Exception:
            redis_ok = False
    return success(
        {
            "status": "ok",
            "app": settings.app_name,
            "dataset_exists": settings.dataset_dir.exists(),
            "dataset_files": len(list(settings.dataset_dir.glob("*.pdf"))) if settings.dataset_dir.exists() else 0,
            "redis": redis_ok,
            "chroma_dir": str(settings.chroma_dir),
        }
    )
