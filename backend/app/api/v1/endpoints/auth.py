"""
旅行助手 源码组件。


"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import auth_service, current_user
from app.core.response import success
from app.core.security import create_access_token
from app.schemas.auth import AuthLoginRequest, AuthRegisterRequest
from app.services.auth_service import AuthService, AuthenticatedUser

router = APIRouter()


@router.post("/register")
async def register(payload: AuthRegisterRequest, service: AuthService = Depends(auth_service)) -> dict:
    """说明：register 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    try:
        user = service.register(username=payload.username, password=payload.password, email=payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    token, expires_in = create_access_token(user.user_id, username=user.username)
    return success({"access_token": token, "token_type": "bearer", "expires_in": expires_in, "user": user.to_dict()})


@router.post("/login")
async def login(payload: AuthLoginRequest, service: AuthService = Depends(auth_service)) -> dict:
    """说明：login 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    user = service.authenticate(username=payload.username, password=payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    token, expires_in = create_access_token(user.user_id, username=user.username)
    return success({"access_token": token, "token_type": "bearer", "expires_in": expires_in, "user": user.to_dict()})


@router.get("/me")
async def me(user: AuthenticatedUser = Depends(current_user)) -> dict:
    """说明：me 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return success({"user": user.to_dict()})


@router.post("/logout")
async def logout(user: AuthenticatedUser = Depends(current_user)) -> dict:
    """说明：logout 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return success({"logged_out": True, "user_id": user.user_id})
