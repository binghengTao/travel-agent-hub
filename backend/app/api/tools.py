"""
旅行助手 源码组件。


"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import tools
from app.tools.travel_tools import TravelTools

router = APIRouter()


class WeatherRequest(BaseModel):
    """WeatherRequest"""
    city: str
    days: int = 3


class NearbyRequest(BaseModel):
    """NearbyRequest"""
    location: str
    city: str = ""
    keyword: str = "food"


class SearchRequest(BaseModel):
    """SearchRequest"""
    query: str
    max_results: int = 5


@router.post("/weather")
async def weather(payload: WeatherRequest, service: TravelTools = Depends(tools)) -> dict:
    """说明：weather 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    result = await service.weather(payload.city, payload.days)
    return {"name": result.name, "result": result.content}


@router.post("/nearby")
async def nearby(payload: NearbyRequest, service: TravelTools = Depends(tools)) -> dict:
    """说明：nearby 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    result = await service.nearby(payload.location, payload.city, payload.keyword)
    return {"name": result.name, "result": result.content}


@router.post("/web-search")
async def web_search(payload: SearchRequest, service: TravelTools = Depends(tools)) -> dict:
    """说明：web_search 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    result = await service.web_search(payload.query, max_results=payload.max_results)
    raw = result.raw if isinstance(result.raw, dict) else {}
    return {"name": result.name, "result": result.content, "web_sources": raw.get("results", [])}
