"""
旅行助手 源码组件。


"""

from pydantic import BaseModel, Field


class AuthRegisterRequest(BaseModel):
    """AuthRegisterRequest"""
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: str | None = None


class AuthLoginRequest(BaseModel):
    """AuthLoginRequest"""
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


