"""
旅行助手 源码组件。


"""

from __future__ import annotations

from typing import Any


def success(data: Any = None, message: str = "success") -> dict[str, Any]:
    """说明：success 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return {"code": 0, "message": message, "data": data if data is not None else {}}


def failure(code: int, message: str, data: Any = None) -> dict[str, Any]:
    """说明：failure 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return {"code": code, "message": message, "data": data if data is not None else {}}
