"""
旅行助手 源码组件。


"""

import asyncio

from app.core.config import Settings
from app.tools.travel_tools import TravelTools


def test_weather_tool_cache_marks_second_call():
    """说明：test_weather_tool_cache_marks_second_call 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    async def run():
        """说明：run 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        tools = TravelTools(Settings(QWEATHER_KEY=None, OPENWEATHER_API_KEY=None))
        first = await tools.weather("\u676d\u5dde", 1)
        second = await tools.weather("\u676d\u5dde", 1)

        assert not first.cached
        assert second.cached

    asyncio.run(run())


def test_web_search_without_key_returns_structured_empty_sources():
    """说明：test_web_search_without_key_returns_structured_empty_sources 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    async def run():
        """说明：run 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        tools = TravelTools(Settings(TAVILY_API_KEY=None))
        result = await tools.web_search("\u897f\u5b89\u5175\u9a6c\u4fd1 \u6700\u65b0\u95e8\u7968")

        assert "TAVILY_API_KEY" in result.content
        assert isinstance(result.raw, dict)
        assert result.raw["results"] == []

    asyncio.run(run())
