"""
旅行助手 FastAPI 应用入口，组装路由、中间件和生命周期。
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.agents.supervisor import SupervisorAgent
from app.agents.graph import build_travel_graph
from app.api.routes import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.rag.retriever import RagService
from app.services.auth_service import AuthService
from app.services.context_memory import ContextBuilder
from app.services.file_service import FileService
from app.services.model_provider import ProviderRegistry
from app.services.session_store import SessionStore
from app.services.user_kb_service import UserKbService
from app.tools.travel_tools import TravelTools


@asynccontextmanager
async def lifespan(app: FastAPI):
    """说明：lifespan 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    configure_logging()
    settings = get_settings()
    # 应用启动时集中创建长生命周期对象，避免每个请求重复初始化模型、RAG、Redis 等重资源。
    providers = ProviderRegistry(settings)
    rag = RagService(settings, providers)
    tools = TravelTools(settings)
    sessions = SessionStore(settings)
    auth = AuthService(settings)
    context_builder = ContextBuilder(settings, providers)
    user_kb = UserKbService(settings, providers)
    auth.init_db()
    await sessions.connect()
    # app.state 作为轻量依赖容器，接口层通过 Depends 取出这些共享实例。
    app.state.settings = settings
    app.state.providers = providers
    app.state.rag = rag
    app.state.tools = tools
    app.state.sessions = sessions
    app.state.auth = auth
    app.state.context_builder = context_builder
    app.state.user_kb = user_kb
    app.state.files = FileService(settings)
    # Supervisor 和 LangGraph 使用同一批 provider/rag/tools，保证 Agent 轨迹和普通服务行为一致。
    app.state.supervisor = SupervisorAgent(providers, rag, tools)
    app.state.agent_graph = build_travel_graph(app.state.supervisor)
    yield
    # 关闭阶段只释放外部连接；本地文件、SQLite 和 Chroma 持久化目录由各自组件维护。
    await sessions.close()


def create_app() -> FastAPI:
    """说明：create_app 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    # CORS 只读取配置，不在代码中写死域名，便于本地和服务器部署切换。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # 中间件顺序保持清晰：先补 trace/latency，再做基础限流，最后进入业务路由。
    app.middleware("http")(trace_middleware)
    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(security_headers_middleware)
    app.include_router(api_router, prefix=settings.api_prefix)
    # 输出目录通过受控静态接口暴露，避免前端直接访问任意服务器路径。
    app.mount("/outputs", StaticFiles(directory=str(settings.output_dir)), name="outputs")
    return app


async def trace_middleware(request: Request, call_next):
    """说明：trace_middleware 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    # trace_id 既可以由前端传入，也可以后端生成；排查 Agent/RAG 链路时依赖它串联日志。
    trace_id = request.headers.get("x-trace-id", uuid4().hex)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        return JSONResponse(
            status_code=500,
            content={
                "trace_id": trace_id,
                "detail": "Internal server error",
                "latency_ms": int((time.perf_counter() - started) * 1000),
            },
        )
    response.headers["x-trace-id"] = trace_id
    response.headers["x-latency-ms"] = str(int((time.perf_counter() - started) * 1000))
    return response


_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


async def rate_limit_middleware(request: Request, call_next):
    """说明：rate_limit_middleware 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    client = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _rate_buckets[client]
    # 使用内存滑动窗口实现轻量限流；生产环境可替换为 Redis 限流。
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute and request.url.path.startswith(settings.api_prefix):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})
    bucket.append(now)
    return await call_next(request)


async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app = create_app()
