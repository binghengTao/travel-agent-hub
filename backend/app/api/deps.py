"""
旅行助手 源码组件。


"""

from fastapi import Header, HTTPException, Request, status

from app.agents.supervisor import SupervisorAgent
from app.agents.graph import TravelAgentGraph
from app.core.security import decode_access_token
from app.rag.retriever import RagService
from app.services.file_service import FileService
from app.services.auth_service import AuthService, AuthenticatedUser
from app.services.context_memory import ContextBuilder
from app.services.model_provider import ProviderRegistry
from app.services.session_store import SessionStore
from app.services.user_kb_service import UserKbService
from app.tools.travel_tools import TravelTools


def providers(request: Request) -> ProviderRegistry:
    """说明：providers 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return request.app.state.providers


def rag_service(request: Request) -> RagService:
    """说明：rag_service 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return request.app.state.rag


def supervisor(request: Request) -> SupervisorAgent:
    """说明：supervisor 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return request.app.state.supervisor


def agent_graph(request: Request) -> TravelAgentGraph:
    """说明：agent_graph 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return request.app.state.agent_graph


def tools(request: Request) -> TravelTools:
    """说明：tools 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return request.app.state.tools


def sessions(request: Request) -> SessionStore:
    """说明：sessions 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return request.app.state.sessions


def files(request: Request) -> FileService:
    """说明：files 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return request.app.state.files


def auth_service(request: Request) -> AuthService:
    """说明：auth_service 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return request.app.state.auth


def context_builder(request: Request) -> ContextBuilder:
    """说明：context_builder 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return request.app.state.context_builder


def user_kb_service(request: Request) -> UserKbService:
    """说明：user_kb_service 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return request.app.state.user_kb


async def current_user(request: Request, authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    """说明：current_user 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    user = request.app.state.auth.get_user(payload.get("sub", ""))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user
