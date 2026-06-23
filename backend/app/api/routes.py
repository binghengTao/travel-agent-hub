"""
旅行助手 源码组件。


"""

from fastapi import APIRouter

from app.api import chat, health, ingest, media, models, rag, tools, trips
from app.api.v1.router import v1_router


api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(trips.router, prefix="/trips", tags=["trips"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(v1_router, prefix="/v1")
