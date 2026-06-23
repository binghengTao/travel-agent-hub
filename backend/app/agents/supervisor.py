"""
旅行助手 源码组件。


"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

from app.agents.verifier import Verifier
from app.rag.retriever import RagService
from app.schemas.common import ToolCall
from app.schemas.trips import TripPlanRequest
from app.services.model_provider import ModelMessage, ProviderRegistry
from app.tools.travel_tools import TravelTools, to_tool_call


RouteName = Literal["planner", "rag", "copywriter", "realtime", "mixed", "general"]


@dataclass
class IntentDecision:
    """IntentDecision"""
    intent: RouteName
    destination: str | None = None
    days: int | None = None
    need_rag: bool = False
    need_weather: bool = False
    need_map: bool = False
    need_search: bool = False
    need_plan: bool = False
    need_copywriting: bool = False

    def model_dump(self) -> dict[str, Any]:
        """说明：model_dump 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return {
            "intent": self.intent,
            "destination": self.destination,
            "days": self.days,
            "need_rag": self.need_rag,
            "need_weather": self.need_weather,
            "need_map": self.need_map,
            "need_search": self.need_search,
            "need_plan": self.need_plan,
            "need_copywriting": self.need_copywriting,
        }


@dataclass
class AgentResult:
    """AgentResult"""
    answer: str
    route: RouteName
    sources: list = None
    tool_calls: list[ToolCall] = None
    verified: bool = True
    warnings: list[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    steps: list[dict[str, Any]] = None

    def __post_init__(self):
        """说明：__post_init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.sources = self.sources or []
        self.tool_calls = self.tool_calls or []
        self.warnings = self.warnings or []
        self.steps = self.steps or []


class SupervisorAgent:
    """Controlled multi-agent coordinator.

    The project intentionally uses router-led orchestration instead of free-form
    agent-to-agent chatting. This keeps the execution path visible, testable, and
    suitable for a course-design style demo.
    """

    def __init__(self, providers: ProviderRegistry, rag: RagService, tools: TravelTools):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.providers = providers
        self.rag = rag
        self.tools = tools
        self.verifier = Verifier()
        self._cities: list[str] | None = None

    async def route(self, message: str) -> RouteName:
        """说明：route 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return self.analyze_intent(message).intent

    def analyze_intent(self, message: str) -> IntentDecision:
        """说明：analyze_intent 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        text = message.lower()
        destination = self._extract_destination(message)
        days = self._extract_days(message)

        need_copywriting = any(word in message for word in ["文案", "小红书", "朋友圈", "微博", "抖音", "种草"])
        need_weather = any(word in message for word in ["天气", "下雨", "气温", "适合", "明天", "今天", "后天"])
        need_map = any(word in message for word in ["附近", "路线", "距离", "怎么去", "交通", "餐厅", "酒店", "景点"])
        need_search = any(word in message for word in ["最新", "开放时间", "门票", "政策", "预约", "限流"])
        need_plan = any(word in message for word in ["规划", "行程", "安排", "路线", "一日", "两日", "几天", "预算", "出发"])
        need_rag = any(word in message for word in ["攻略", "景点", "注意事项", "推荐", "知识库", "怎么玩", "游", "路线"])

        if "trip" in text or "travel" in text:
            need_plan = True

        flags = [need_rag, need_weather or need_map or need_search, need_plan, need_copywriting]
        if sum(1 for flag in flags if flag) >= 2:
            intent: RouteName = "mixed"
        elif need_copywriting:
            intent = "copywriter"
        elif need_plan:
            intent = "planner"
        elif need_weather or need_map or need_search:
            intent = "realtime"
        elif need_rag:
            intent = "rag"
        else:
            intent = "general"

        return IntentDecision(
            intent=intent,
            destination=destination,
            days=days,
            need_rag=need_rag,
            need_weather=need_weather,
            need_map=need_map,
            need_search=need_search,
            need_plan=need_plan,
            need_copywriting=need_copywriting,
        )

    async def handle(self, message: str, *, session_id: str, trace_id: str, provider: str = "auto") -> AgentResult:
        """说明：handle 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        decision = self.analyze_intent(message)
        router_step = _step("RouterAgent", "success", f"intent={decision.intent}, destination={decision.destination or '-'}")
        if decision.intent == "mixed":
            return await self._mixed(message, decision, session_id=session_id, trace_id=trace_id, provider=provider)
        if decision.intent == "rag":
            rag_response = await self.rag.query(message, session_id=session_id, trace_id=trace_id, provider_name=provider, city_hint=decision.destination)
            verified, warnings = self.verifier.verify_rag_answer(rag_response.answer, len(rag_response.sources))
            steps = [
                router_step,
                _step("RAGAgent", "success", f"retrieved {len(rag_response.sources)} sources", rag_response.latency_ms),
                _step("CriticAgent", "success" if verified else "warning", "; ".join(warnings) or "references checked"),
            ]
            return AgentResult(rag_response.answer, "rag", rag_response.sources, verified=verified, warnings=warnings, metadata={"intent": decision.model_dump()}, steps=steps)
        if decision.intent == "realtime":
            result = await self._realtime(message, provider, decision=decision)
            result.steps.insert(0, router_step)
            return result
        if decision.intent == "copywriter":
            result = await self._copywriter(message, provider, decision=decision)
            result.steps.insert(0, router_step)
            return result
        if decision.intent == "planner":
            result = await self._plan_from_text(message, decision, provider)
            result.steps.insert(0, router_step)
            return result
        result = await self._general(message, provider, decision.intent, decision=decision)
        result.steps.insert(0, router_step)
        return result

    async def plan_trip(self, request: TripPlanRequest, *, trace_id: str) -> AgentResult:
        """说明：plan_trip 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        provider = self.providers.resolve(request.provider)
        prompt = self._trip_prompt(
            departure=request.departure,
            destination=request.destination,
            days=request.days,
            style=request.style,
            budget=request.budget,
            people=request.people,
            preferences=request.preferences,
        )
        answer = await provider.chat([ModelMessage(role="user", content=prompt)], model=self.providers.settings.qwen_chat_model)
        verified, warnings = self.verifier.verify_trip_plan(answer, request.days)
        steps = [
            _step("PlannerAgent", "success", f"generated {request.days} day plan for {request.destination}"),
            _step("CriticAgent", "success" if verified else "warning", "; ".join(warnings) or "plan structure checked"),
        ]
        return AgentResult(answer, "planner", verified=verified, warnings=warnings, metadata={"destination": request.destination, "days": request.days}, steps=steps)

    async def stream_trip(self, request: TripPlanRequest):
        """说明：stream_trip 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        provider = self.providers.resolve(request.provider)
        prompt = self._trip_prompt(
            departure=request.departure,
            destination=request.destination,
            days=request.days,
            style=request.style,
            budget=request.budget,
            people=request.people,
            preferences=request.preferences,
        )
        async for token in provider.stream([ModelMessage(role="user", content=prompt)], model=self.providers.settings.qwen_chat_model):
            yield token

    async def _mixed(self, message: str, decision: IntentDecision, *, session_id: str, trace_id: str, provider: str) -> AgentResult:
        """说明：_mixed 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        sources = []
        tool_calls: list[ToolCall] = []
        evidence_blocks: list[str] = []
        steps: list[dict[str, Any]] = [_step("RouterAgent", "success", f"intent=mixed, destination={decision.destination or '-'}")]

        if decision.need_weather:
            city = decision.destination or "北京"
            started = _now()
            weather = await self.tools.weather(city, days=1)
            call = to_tool_call(weather, {"city": city, "days": 1})
            tool_calls.append(call)
            evidence_blocks.append(f"天气工具结果: {weather.content}")
            steps.append(_step("ToolAgent.weather_tool", "success" if not call.error else "warning", str(weather.content)[:120], _elapsed(started)))

        if decision.need_map:
            city = decision.destination or ""
            started = _now()
            poi = await self.tools.nearby(location=decision.destination or message, city=city, keyword="景点")
            call = to_tool_call(poi, {"location": decision.destination or message, "city": city, "keyword": "景点"})
            tool_calls.append(call)
            evidence_blocks.append(f"地图/POI 工具结果: {poi.content}")
            steps.append(_step("ToolAgent.amap_poi_tool", "success" if not call.error else "warning", str(poi.content)[:120], _elapsed(started)))

        if decision.need_search:
            started = _now()
            search = await self.tools.web_search(message)
            call = to_tool_call(search, {"query": message})
            tool_calls.append(call)
            evidence_blocks.append(f"联网搜索结果: {search.content}")
            steps.append(_step("ToolAgent.web_search_tool", "success" if not call.error else "warning", str(search.content)[:120], _elapsed(started)))

        if decision.need_rag:
            started = _now()
            rag_response = await self.rag.query(message, session_id=session_id, trace_id=trace_id, provider_name=provider, city_hint=decision.destination)
            sources = rag_response.sources
            evidence_blocks.append("RAG 证据:\n" + "\n".join(f"- {source.source} 第{source.page or '-'}页: {source.preview[:160]}" for source in sources))
            steps.append(_step("RAGAgent", "success", f"retrieved {len(sources)} sources", _elapsed(started)))

        llm = self.providers.resolve(provider)
        prompt = (
            "你是 旅行助手 的 AnswerAgent。请基于 Router、RAG、Tool 和 Planner 的结果，给出一个可执行的旅游回答。\n"
            "要求: 先回答是否适合，再给路线/行程建议；如果有引用来源，必须在文末列出；如果工具不可用，要说明这是配置缺失而不是业务失败。\n\n"
            f"Router 结果: {decision.model_dump()}\n"
            f"用户问题: {message}\n\n"
            f"{chr(10).join(evidence_blocks)}\n\n"
            "如果需要旅行计划，请生成清晰的时间线。"
        )
        answer = await llm.chat([ModelMessage(role="user", content=prompt)], model=self.providers.settings.qwen_chat_model)
        steps.append(_step("AnswerAgent", "success", "composed final response"))

        warnings: list[str] = []
        verified = True
        if decision.need_rag:
            verified, warnings = self.verifier.verify_rag_answer(answer, len(sources))
        steps.append(_step("CriticAgent", "success" if verified else "warning", "; ".join(warnings) or "answer checked"))

        return AgentResult(
            answer,
            "mixed",
            sources=sources,
            tool_calls=tool_calls,
            verified=verified,
            warnings=warnings,
            metadata={"intent": decision.model_dump(), "plan": {"markdown": answer} if decision.need_plan else None},
            steps=steps,
        )

    async def _plan_from_text(self, message: str, decision: IntentDecision, provider_name: str) -> AgentResult:
        """说明：_plan_from_text 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        llm = self.providers.resolve(provider_name)
        prompt = self._trip_prompt(
            departure="",
            destination=decision.destination or "目的地",
            days=decision.days or 1,
            style="适中",
            budget="",
            people="1",
            preferences=message,
        )
        answer = await llm.chat([ModelMessage(role="user", content=prompt)], model=self.providers.settings.qwen_chat_model)
        verified, warnings = self.verifier.verify_trip_plan(answer, decision.days or 1)
        steps = [
            _step("PlannerAgent", "success", f"generated {decision.days or 1} day plan"),
            _step("CriticAgent", "success" if verified else "warning", "; ".join(warnings) or "plan checked"),
        ]
        return AgentResult(answer, "planner", verified=verified, warnings=warnings, metadata={"intent": decision.model_dump(), "plan": {"markdown": answer}}, steps=steps)

    async def _realtime(self, message: str, provider: str, decision: IntentDecision | None = None) -> AgentResult:
        """说明：_realtime 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        decision = decision or self.analyze_intent(message)
        tool_calls: list[ToolCall] = []
        if decision.need_weather or "天气" in message:
            city = decision.destination or message.replace("天气", "").strip(" ，。?？") or "北京"
            result = await self.tools.weather(city)
            tool_calls.append(to_tool_call(result, {"city": city}))
            return AgentResult(result.content, "realtime", tool_calls=tool_calls, metadata={"intent": decision.model_dump()}, steps=[_step("ToolAgent.weather_tool", "success", str(result.content)[:120])])
        if decision.need_map or "附近" in message:
            result = await self.tools.nearby(location=decision.destination or message, city=decision.destination or "", keyword="美食")
            tool_calls.append(to_tool_call(result, {"location": decision.destination or message, "keyword": "美食"}))
            return AgentResult(result.content, "realtime", tool_calls=tool_calls, metadata={"intent": decision.model_dump()}, steps=[_step("ToolAgent.amap_poi_tool", "success", str(result.content)[:120])])
        result = await self.tools.web_search(message)
        tool_calls.append(to_tool_call(result, {"query": message}))
        return AgentResult(result.content, "realtime", tool_calls=tool_calls, metadata={"intent": decision.model_dump()}, steps=[_step("ToolAgent.web_search_tool", "success", str(result.content)[:120])])

    async def _copywriter(self, message: str, provider: str, decision: IntentDecision | None = None) -> AgentResult:
        """说明：_copywriter 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        llm = self.providers.resolve(provider)
        answer = await llm.chat(
            [
                ModelMessage(role="system", content="你是旅行新媒体文案专家，输出自然、有画面感、适合发布。"),
                ModelMessage(role="user", content=message),
            ],
            model=self.providers.settings.qwen_fast_model,
        )
        return AgentResult(answer, "copywriter", metadata={"intent": (decision or self.analyze_intent(message)).model_dump()}, steps=[_step("CopywritingAgent", "success", "copy generated")])

    async def _general(self, message: str, provider: str, route: RouteName, decision: IntentDecision | None = None) -> AgentResult:
        """说明：_general 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        llm = self.providers.resolve(provider)
        answer = await llm.chat([ModelMessage(role="user", content=message)])
        return AgentResult(answer, route, metadata={"intent": (decision or self.analyze_intent(message)).model_dump()}, steps=[_step("ChatService", "success", "general answer generated")])

    def _trip_prompt(self, *, departure: str, destination: str, days: int, style: str, budget: str, people: str, preferences: str) -> str:
        """说明：_trip_prompt 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return (
            "你是专业旅行规划师。请生成 Markdown 表格，表头必须包含: 日期、地点、行程计划、交通方式、餐饮安排、住宿安排、费用估算、备注。\n"
            f"出发地:{departure or '未指定'}\n目的地:{destination}\n天数:{days}\n"
            f"风格:{style}\n预算:{budget or '未指定'}\n人数:{people}\n偏好:{preferences}\n"
            "要求: 每一天都要有安排，交通和预算要合理，最后给出总费用估算和注意事项。"
        )

    def _extract_destination(self, message: str) -> str | None:
        """说明：_extract_destination 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        for city in self._known_cities():
            if city and city in message:
                return city
        return None

    def _extract_days(self, message: str) -> int | None:
        """说明：_extract_days 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        digit_map = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7}
        for word, value in digit_map.items():
            if f"{word}天" in message or f"{word}日" in message:
                return value
        for value in range(1, 31):
            if f"{value}天" in message or f"{value}日" in message:
                return value
        return None

    def _known_cities(self) -> list[str]:
        """说明：_known_cities 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if self._cities is not None:
            return self._cities
        cities = {"北京", "上海", "杭州", "西安", "成都", "重庆", "广州", "深圳", "南京", "厦门", "三亚", "西藏", "云南", "新疆", "青海"}
        try:
            for chunk in self.rag.indexer.load_chunks():
                if chunk.city:
                    cities.add(chunk.city)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Failed to load cities from RAG indexer chunks: %s", exc)
        self._cities = sorted(cities, key=len, reverse=True)
        return self._cities


def _now() -> float:
    """说明：_now 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return time.perf_counter()


def _elapsed(started: float) -> int:
    """说明：_elapsed 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return int((time.perf_counter() - started) * 1000)


def _step(name: str, status: str, summary: str, latency_ms: int | None = None) -> dict[str, Any]:
    """说明：_step 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    payload: dict[str, Any] = {"name": name, "status": status, "summary": summary}
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    return payload
