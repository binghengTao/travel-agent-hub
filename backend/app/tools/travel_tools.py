"""
旅行助手 源码组件。


"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import Settings, get_settings
from app.schemas.common import ToolCall


@dataclass
class ToolResult:
    """ToolResult"""
    name: str
    content: str
    raw: dict[str, Any] | list[Any] | None = None
    cached: bool = False


class TravelTools:
    """TravelTools"""
    def __init__(self, settings: Settings | None = None):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings or get_settings()
        self._cache: dict[str, tuple[float, ToolResult]] = {}

    async def weather(self, city: str, days: int = 3) -> ToolResult:
        """说明：weather 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        key = f"weather:{city}:{days}"
        cached = self._get_cache(key)
        if cached:
            return cached
        if self.settings.qweather_key:
            return self._set_cache(key, await self._qweather(city, days))
        if self.settings.openweather_api_key:
            return self._set_cache(key, await self._openweather(city, days))
        return self._set_cache(key, ToolResult("weather", f"天气工具未配置 API key，无法查询 {city} 的实时天气。"))

    async def nearby(self, location: str, city: str, keyword: str) -> ToolResult:
        """说明：nearby 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        key = f"nearby:{location}:{city}:{keyword}"
        cached = self._get_cache(key)
        if cached:
            return cached
        if not self.settings.amap_key:
            return self._set_cache(key, ToolResult("nearby", "附近 POI 工具未配置 AMAP_KEY。"))

        async with httpx.AsyncClient(timeout=20) as client:
            geo = await client.get(
                "https://restapi.amap.com/v5/place/text",
                params={"key": self.settings.amap_key, "keywords": location, "region": city},
            )
            geo.raise_for_status()
            data = geo.json()
            pois = data.get("pois") or []
            if not pois:
                return self._set_cache(key, ToolResult("nearby", f"未找到 {city} 的 {location} 坐标。", data))
            lng, lat = pois[0]["location"].split(",")
            nearby = await client.get(
                "https://restapi.amap.com/v5/place/around",
                params={"key": self.settings.amap_key, "keywords": keyword, "location": f"{lng},{lat}"},
            )
            nearby.raise_for_status()
            nearby_data = nearby.json()

        lines = []
        for poi in (nearby_data.get("pois") or [])[:5]:
            lines.append(f"{poi.get('name')} | {poi.get('address')} | 距离 {poi.get('distance')} 米")
        return self._set_cache(key, ToolResult("nearby", "\n".join(lines) or "未找到相关 POI。", nearby_data))

    async def web_search(self, query: str, max_results: int = 5) -> ToolResult:
        """说明：web_search 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        key = f"web_search:{query}:{max_results}"
        cached = self._get_cache(key)
        if cached:
            return cached
        if not self.settings.tavily_api_key:
            return self._set_cache(
                key,
                ToolResult(
                    "web_search",
                    "联网搜索工具未配置 TAVILY_API_KEY。请在 .env 中填写后再进行真实网页搜索。",
                    {"configured": False, "results": []},
                ),
            )
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults

            tool = TavilySearchResults(max_results=max_results, tavily_api_key=self.settings.tavily_api_key)
            raw_results = await tool.ainvoke({"query": query})
            results = _normalize_web_results(raw_results)
            return self._set_cache(key, ToolResult("web_search", _format_web_results(results), {"configured": True, "results": results}))
        except Exception as exc:
            return self._set_cache(key, ToolResult("web_search", f"联网搜索失败: {exc}", {"configured": True, "results": [], "error": str(exc)}))

    async def _qweather(self, city: str, days: int) -> ToolResult:
        """说明：_qweather 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        async with httpx.AsyncClient(timeout=20) as client:
            geo = await client.get(
                "https://geoapi.qweather.com/v2/city/lookup",
                params={"location": city, "key": self.settings.qweather_key},
            )
            geo.raise_for_status()
            geo_data = geo.json()
            location_id = (geo_data.get("location") or [{}])[0].get("id")
            if not location_id:
                return ToolResult("weather", f"无法识别城市: {city}", geo_data)
            weather = await client.get(
                "https://devapi.qweather.com/v7/weather/7d",
                params={"location": location_id, "key": self.settings.qweather_key},
            )
            weather.raise_for_status()
            data = weather.json()
        lines = []
        for day in (data.get("daily") or [])[:days]:
            lines.append(f"{day.get('fxDate')}: {day.get('textDay')}/{day.get('textNight')} {day.get('tempMin')}-{day.get('tempMax')} C")
        return ToolResult("weather", "\n".join(lines), data)

    async def _openweather(self, city: str, days: int) -> ToolResult:
        """说明：_openweather 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params={
                    "q": city,
                    "appid": self.settings.openweather_api_key,
                    "units": "metric",
                    "lang": "zh_cn",
                },
            )
            response.raise_for_status()
            data = response.json()
        lines = []
        for item in (data.get("list") or [])[: days * 8]:
            weather = (item.get("weather") or [{}])[0].get("description", "")
            lines.append(f"{item.get('dt_txt')}: {item.get('main', {}).get('temp')} C {weather}")
        return ToolResult("weather", "\n".join(lines), data)

    def _get_cache(self, key: str) -> ToolResult | None:
        """说明：_get_cache 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        item = self._cache.get(key)
        if not item:
            return None
        expires_at, result = item
        if expires_at < time.time():
            self._cache.pop(key, None)
            return None
        return ToolResult(result.name, result.content, result.raw, cached=True)

    def _set_cache(self, key: str, result: ToolResult) -> ToolResult:
        """说明：_set_cache 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self._cache[key] = (time.time() + self.settings.tool_cache_ttl_seconds, result)
        return result


def to_tool_call(result: ToolResult, args: dict) -> ToolCall:
    """说明：to_tool_call 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return ToolCall(name=result.name, arguments={**args, "cached": result.cached}, result=result.content)


def _normalize_web_results(raw_results: Any) -> list[dict[str, Any]]:
    """说明：_normalize_web_results 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    if isinstance(raw_results, dict):
        items = raw_results.get("results") or raw_results.get("data") or []
    else:
        items = raw_results or []

    results: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("link") or "")
        snippet = str(item.get("content") or item.get("snippet") or item.get("raw_content") or "")
        title = str(item.get("title") or item.get("name") or url or f"Web result {index + 1}")
        published_at = item.get("published_date") or item.get("published_at") or item.get("date")
        score = item.get("score")
        results.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet[:500],
                "source": _domain(url),
                "published_at": str(published_at) if published_at else "",
                "score": float(score) if isinstance(score, int | float) else None,
            }
        )
    return results


def _format_web_results(results: list[dict[str, Any]]) -> str:
    """说明：_format_web_results 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    if not results:
        return "未搜索到可用网页结果。"
    lines = []
    for index, item in enumerate(results, start=1):
        lines.append(
            "\n".join(
                [
                    f"{index}. {item.get('title')}",
                    f"来源: {item.get('source') or '-'}",
                    f"摘要: {item.get('snippet') or '-'}",
                    f"URL: {item.get('url') or '-'}",
                ]
            )
        )
    return "\n\n".join(lines)


def _domain(url: str) -> str:
    """说明：_domain 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    try:
        return urlparse(url).netloc
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Tool geo lookup failed: %s", exc)
        return ""
