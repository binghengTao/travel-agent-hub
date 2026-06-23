"""
旅行助手 源码组件。


"""

from fastapi import APIRouter

from app.api.v1.endpoints import agent, auth, chat, copywriting, health, history, kb, models, plan, preferences, rag, tools, user_kb


v1_router = APIRouter()
v1_router.include_router(health.router, tags=["v1-health"])
v1_router.include_router(auth.router, prefix="/auth", tags=["v1-auth"])
v1_router.include_router(models.router, prefix="/models", tags=["v1-models"])
v1_router.include_router(chat.router, prefix="/chat", tags=["v1-chat"])
v1_router.include_router(rag.router, prefix="/rag", tags=["v1-rag"])
v1_router.include_router(agent.router, prefix="/agent", tags=["v1-agent"])
v1_router.include_router(plan.router, prefix="/plan", tags=["v1-plan"])
v1_router.include_router(copywriting.router, prefix="/copywriting", tags=["v1-copywriting"])
v1_router.include_router(history.router, prefix="/history", tags=["v1-history"])
v1_router.include_router(preferences.router, prefix="/preferences", tags=["v1-preferences"])
v1_router.include_router(kb.router, prefix="/kb", tags=["v1-kb"])
v1_router.include_router(user_kb.router, prefix="/user-kb", tags=["v1-user-kb"])
v1_router.include_router(tools.router, prefix="/tools", tags=["v1-tools"])
