"""
旅行助手 源码组件。


"""

from __future__ import annotations

import html
import re
import time
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.supervisor import SupervisorAgent
from app.api.deps import context_builder, current_user, sessions, supervisor
from app.core.response import success
from app.schemas.trips import TripPlanRequest
from app.services.auth_service import AuthenticatedUser
from app.services.context_memory import ContextBuilder
from app.services.model_provider import ModelMessage
from app.services.session_store import SessionStore
from app.tools.travel_tools import to_tool_call

router = APIRouter()


class PlanOptimizeRequest(BaseModel):
    """PlanOptimizeRequest"""
    departure: str = ""
    destination: str = Field(min_length=1)
    days: int = Field(default=1, ge=1, le=15)
    budget: str = ""
    people: str = "1"
    pace: str = "适中"
    must_visit: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    user_id: str | None = None
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    provider: str = "auto"


class BudgetRequest(BaseModel):
    """BudgetRequest"""
    days: int = Field(default=1, ge=1, le=60)
    people: int = Field(default=1, ge=1, le=50)
    hotel_per_night: float = 0
    food_per_person_day: float = 0
    transport_total: float = 0
    ticket_per_person: float = 0
    shopping_misc: float = 0
    buffer_rate: float = Field(default=0.1, ge=0, le=1)


class ExportPlanRequest(BaseModel):
    """ExportPlanRequest"""
    title: str = "旅行计划"
    content: str = Field(min_length=1)
    format: str = Field(default="markdown", pattern="^(markdown|html)$")


class RouteNodesRequest(BaseModel):
    """RouteNodesRequest"""
    destination: str = ""
    places: list[str] = Field(default_factory=list)
    plan_markdown: str = ""


class AlternativesRequest(BaseModel):
    """AlternativesRequest"""
    destination: str = Field(min_length=1)
    issue: str = "天气变化"
    original_plan: str = ""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    provider: str = "auto"


class WebEnhancedPlanRequest(TripPlanRequest):
    """WebEnhancedPlanRequest"""
    use_web_search: bool = True
    include_rag: bool = True
    include_weather: bool = True
    include_poi: bool = True
    search_query: str = ""


@router.post("/generate")
async def generate_plan(
    payload: TripPlanRequest,
    agent: SupervisorAgent = Depends(supervisor),
    store: SessionStore = Depends(sessions),
    memory: ContextBuilder = Depends(context_builder),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：generate_plan 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    started = time.perf_counter()
    user_id = user.user_id
    context = await memory.build(
        user_id=user_id,
        session_id=payload.session_id,
        store=store,
        current_message=f"{payload.destination} {payload.days} 天游行程规划",
    )
    enriched_payload = payload.model_copy(
        update={"preferences": _append_context_to_preferences(payload.preferences, context.prompt_context)}
    )
    result = await agent.plan_trip(enriched_payload, trace_id=trace_id)
    await store.append(payload.session_id, "user", _plan_user_message(payload), user_id=user_id)
    await store.append(payload.session_id, "assistant", result.answer, user_id=user_id)
    await memory.compressor.compress_if_needed(user_id=user_id, session_id=payload.session_id, store=store)
    return success(
        {
            "trace_id": trace_id,
            "session_id": payload.session_id,
            "user_id": user_id,
            "answer": result.answer,
            "plan": result.metadata.get("plan", {"markdown": result.answer}),
            "verified": result.verified,
            "warnings": result.warnings,
            "memory": {
                "summary_exists": bool(context.summary),
                "fact_count": len(context.facts),
                "token_estimate": context.token_estimate,
            },
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    )


@router.post("/web-enhanced")
async def web_enhanced_plan(
    payload: WebEnhancedPlanRequest,
    agent: SupervisorAgent = Depends(supervisor),
    store: SessionStore = Depends(sessions),
    memory: ContextBuilder = Depends(context_builder),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：web_enhanced_plan 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    started = time.perf_counter()
    user_id = user.user_id
    steps: list[dict] = []
    tool_calls: list[dict] = []
    web_sources: list[dict] = []
    rag_sources: list[dict] = []
    evidence_blocks: list[str] = []

    if payload.include_weather:
        weather = await agent.tools.weather(payload.destination, days=min(payload.days, 7))
        weather_call = to_tool_call(weather, {"city": payload.destination, "days": min(payload.days, 7)})
        tool_calls.append(weather_call.model_dump())
        evidence_blocks.append(f"天气结果:\n{weather.content}")
        steps.append(
            {
                "name": "ToolAgent.weather_tool",
                "status": "success" if not weather_call.error else "warning",
                "summary": str(weather.content)[:160],
            }
        )

    if payload.include_poi:
        poi = await agent.tools.nearby(payload.destination, payload.destination, "景点")
        poi_call = to_tool_call(poi, {"location": payload.destination, "city": payload.destination, "keyword": "景点"})
        tool_calls.append(poi_call.model_dump())
        evidence_blocks.append(f"POI 结果:\n{poi.content}")
        steps.append(
            {
                "name": "ToolAgent.amap_poi_tool",
                "status": "success" if not poi_call.error else "warning",
                "summary": str(poi.content)[:160],
            }
        )

    if payload.use_web_search:
        query = payload.search_query or _build_travel_search_query(payload)
        search = await agent.tools.web_search(query, max_results=6)
        search_call = to_tool_call(search, {"query": query, "max_results": 6})
        tool_calls.append(search_call.model_dump())
        raw = search.raw if isinstance(search.raw, dict) else {}
        web_sources = raw.get("results", [])
        evidence_blocks.append("网页搜索证据:\n" + _format_web_sources_for_prompt(web_sources, search.content))
        steps.append(
            {
                "name": "ToolAgent.web_search_tool",
                "status": "success" if web_sources else "warning",
                "summary": str(search.content)[:160],
            }
        )

    if payload.include_rag:
        rag = await agent.rag.query(
            f"{payload.destination} {payload.days}天 旅行规划 攻略 注意事项 {payload.preferences}",
            session_id=payload.session_id,
            trace_id=trace_id,
            provider_name=payload.provider,
            city_hint=payload.destination,
        )
        rag_sources = [source.model_dump() for source in rag.sources]
        evidence_blocks.append(
            "本地 RAG 证据:\n"
            + "\n".join(f"- {source.source} page {source.page or '-'}: {source.preview[:180]}" for source in rag.sources)
        )
        steps.append(
            {"name": "RAGAgent", "status": "success", "summary": f"retrieved {len(rag.sources)} sources", "latency_ms": rag.latency_ms}
        )

    context = await memory.build(
        user_id=user_id,
        session_id=payload.session_id,
        store=store,
        current_message=f"{payload.destination} {payload.days} 天游行程规划",
        rag_sources=rag_sources,
        web_sources=web_sources,
        tool_results=tool_calls,
    )
    prompt = (
        "你是 旅行助手 的联网增强 PlannerAgent。请默认使用中文回答。\n"
        "请综合网页搜索证据、本地 RAG 攻略、天气、POI 工具结果和用户分层记忆生成旅行计划。\n"
        "要求：\n"
        "1. 先给出是否适合出行和实时风险提醒。\n"
        "2. 生成按天、按时间段组织的结构化行程。\n"
        "3. 明确写出开放时间、门票、预约、限流等需要用户二次确认的信息。\n"
        "4. 如果网页搜索未配置或无结果，要如实说明，不要编造最新政策。\n"
        "5. 结尾列出网页来源和本地攻略来源。\n\n"
        f"出发地: {payload.departure}\n"
        f"目的地: {payload.destination}\n"
        f"天数: {payload.days}\n"
        f"风格: {payload.style}\n"
        f"预算: {payload.budget or '未指定'}\n"
        f"人数: {payload.people}\n"
        f"偏好: {payload.preferences or '无'}\n\n"
        f"分层记忆上下文:\n{context.prompt_context}\n\n"
        f"证据:\n{chr(10).join(evidence_blocks)}"
    )
    provider = agent.providers.resolve(payload.provider)
    answer = await provider.chat([ModelMessage(role="user", content=prompt)], model=agent.providers.settings.qwen_chat_model)
    verified, warnings = agent.verifier.verify_trip_plan(answer, payload.days)
    steps.append({"name": "PlannerAgent", "status": "success", "summary": f"generated web-enhanced {payload.days} day plan"})
    steps.append({"name": "CriticAgent", "status": "success" if verified else "warning", "summary": "; ".join(warnings) or "plan checked"})

    await store.append(payload.session_id, "user", _plan_user_message(payload), user_id=user_id)
    await store.append(payload.session_id, "assistant", answer, user_id=user_id)
    await memory.compressor.compress_if_needed(user_id=user_id, session_id=payload.session_id, store=store)
    return success(
        {
            "trace_id": trace_id,
            "session_id": payload.session_id,
            "user_id": user_id,
            "answer": answer,
            "plan": {"markdown": answer},
            "web_sources": web_sources,
            "sources": rag_sources,
            "tool_calls": tool_calls,
            "steps": steps,
            "verified": verified,
            "warnings": warnings,
            "memory": {
                "summary_exists": bool(context.summary),
                "fact_count": len(context.facts),
                "token_estimate": context.token_estimate,
            },
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    )


@router.post("/optimize")
async def optimize_plan(
    payload: PlanOptimizeRequest,
    agent: SupervisorAgent = Depends(supervisor),
    store: SessionStore = Depends(sessions),
    memory: ContextBuilder = Depends(context_builder),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：optimize_plan 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    started = time.perf_counter()
    user_id = user.user_id
    profile = await store.get_profile(user_id)
    steps = [{"name": "PreferenceMemory", "status": "success", "summary": "loaded profile" if profile else "no profile found"}]

    weather = await agent.tools.weather(payload.destination, days=min(payload.days, 7))
    weather_call = to_tool_call(weather, {"city": payload.destination, "days": min(payload.days, 7)})
    steps.append({"name": "ToolAgent.weather_tool", "status": "success" if not weather_call.error else "warning", "summary": str(weather.content)[:120]})

    poi = await agent.tools.nearby(payload.destination, payload.destination, "景点")
    poi_call = to_tool_call(poi, {"location": payload.destination, "city": payload.destination, "keyword": "景点"})
    steps.append({"name": "ToolAgent.amap_poi_tool", "status": "success" if not poi_call.error else "warning", "summary": str(poi.content)[:120]})

    rag = await agent.rag.query(
        f"{payload.destination} {payload.days}天 旅行路线 注意事项 推荐",
        session_id=payload.session_id,
        trace_id=trace_id,
        provider_name=payload.provider,
        city_hint=payload.destination,
    )
    steps.append({"name": "RAGAgent", "status": "success", "summary": f"retrieved {len(rag.sources)} sources", "latency_ms": rag.latency_ms})

    rag_sources = [source.model_dump() for source in rag.sources]
    tool_calls = [weather_call.model_dump(), poi_call.model_dump()]
    context = await memory.build(
        user_id=user_id,
        session_id=payload.session_id,
        store=store,
        current_message=f"{payload.destination} {payload.days} 天游行程优化",
        profile=profile,
        rag_sources=rag_sources,
        tool_results=tool_calls,
    )
    source_text = "\n".join(f"- {source.source} page {source.page or '-'}: {source.preview[:160]}" for source in rag.sources)
    prompt = (
        "你是旅行行程优化 Agent。请使用中文回答，并结合用户画像、分层记忆、天气、POI 数据和 RAG 证据创建结构化 Markdown 行程。\n"
        "必须包含：每日时间线、交通建议、预算拆分、备选方案、风险提醒，以及为什么这个顺序合理。\n\n"
        f"出发地: {payload.departure or '未指定'}\n"
        f"目的地: {payload.destination}\n"
        f"天数: {payload.days}\n"
        f"预算: {payload.budget or '未指定'}\n"
        f"人数: {payload.people}\n"
        f"节奏: {payload.pace}\n"
        f"必去: {payload.must_visit}\n"
        f"避开: {payload.avoid}\n"
        f"用户画像: {profile}\n\n"
        f"分层记忆上下文:\n{context.prompt_context}\n\n"
        f"天气结果: {weather.content}\n"
        f"POI 结果: {poi.content}\n"
        f"RAG 来源:\n{source_text}"
    )
    provider = agent.providers.resolve(payload.provider)
    answer = await provider.chat([ModelMessage(role="user", content=prompt)], model=agent.providers.settings.qwen_chat_model)
    verified, warnings = agent.verifier.verify_trip_plan(answer, payload.days)
    steps.append({"name": "PlannerAgent", "status": "success", "summary": f"optimized {payload.days} day itinerary"})
    steps.append({"name": "CriticAgent", "status": "success" if verified else "warning", "summary": "; ".join(warnings) or "plan checked"})

    await store.append(payload.session_id, "user", f"优化 {payload.destination} {payload.days} 天游行程", user_id=user_id)
    await store.append(payload.session_id, "assistant", answer, user_id=user_id)
    await memory.compressor.compress_if_needed(user_id=user_id, session_id=payload.session_id, store=store)
    data = {
        "trace_id": trace_id,
        "session_id": payload.session_id,
        "user_id": user_id,
        "answer": answer,
        "plan": {"markdown": answer},
        "profile": profile,
        "tool_calls": tool_calls,
        "sources": rag_sources,
        "steps": steps,
        "verified": verified,
        "warnings": warnings,
        "memory": {
            "summary_exists": bool(context.summary),
            "fact_count": len(context.facts),
            "token_estimate": context.token_estimate,
        },
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }
    return success(data)


@router.post("/budget")
async def calculate_budget(payload: BudgetRequest, user: AuthenticatedUser = Depends(current_user)) -> dict:
    """说明：calculate_budget 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    nights = max(payload.days - 1, 0)
    hotel = payload.hotel_per_night * nights
    food = payload.food_per_person_day * payload.people * payload.days
    tickets = payload.ticket_per_person * payload.people
    subtotal = hotel + food + payload.transport_total + tickets + payload.shopping_misc
    buffer = subtotal * payload.buffer_rate
    total = subtotal + buffer
    per_person = total / payload.people if payload.people else total
    return success(
        {
            "user_id": user.user_id,
            "days": payload.days,
            "people": payload.people,
            "items": {
                "hotel": round(hotel, 2),
                "food": round(food, 2),
                "transport": round(payload.transport_total, 2),
                "ticket": round(tickets, 2),
                "misc": round(payload.shopping_misc, 2),
                "buffer": round(buffer, 2),
            },
            "subtotal": round(subtotal, 2),
            "total": round(total, 2),
            "per_person": round(per_person, 2),
        }
    )


@router.post("/export")
async def export_plan(
    payload: ExportPlanRequest,
    agent: SupervisorAgent = Depends(supervisor),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：export_plan 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    suffix = ".html" if payload.format == "html" else ".md"
    path = agent.providers.settings.output_dir / f"plan_{trace_id[:10]}{suffix}"
    if payload.format == "html":
        content = (
            "<!doctype html><html><head><meta charset=\"utf-8\"><title>"
            + html.escape(payload.title)
            + "</title><style>body{font-family:Arial,sans-serif;line-height:1.7;max-width:980px;margin:40px auto;padding:0 20px}</style></head><body><h1>"
            + html.escape(payload.title)
            + "</h1><pre>"
            + html.escape(payload.content)
            + "</pre></body></html>"
        )
    else:
        content = f"# {payload.title}\n\n{payload.content}\n"
    path.write_text(content, encoding="utf-8")
    return success({"trace_id": trace_id, "user_id": user.user_id, "output_url": f"/outputs/{path.name}", "format": payload.format})


@router.post("/route-nodes")
async def route_nodes(payload: RouteNodesRequest, user: AuthenticatedUser = Depends(current_user)) -> dict:
    """说明：route_nodes 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    places = payload.places or _extract_places(payload.plan_markdown)
    nodes = [
        {
            "order": index + 1,
            "name": place,
            "city": payload.destination,
            "label": f"{index + 1}. {place}",
        }
        for index, place in enumerate(_dedupe(places))
    ]
    edges = [
        {"from": nodes[index]["name"], "to": nodes[index + 1]["name"], "mode": "步行/公共交通待确认"}
        for index in range(len(nodes) - 1)
    ]
    return success({"user_id": user.user_id, "destination": payload.destination, "nodes": nodes, "edges": edges})


@router.post("/alternatives")
async def alternatives(
    payload: AlternativesRequest,
    agent: SupervisorAgent = Depends(supervisor),
    store: SessionStore = Depends(sessions),
    memory: ContextBuilder = Depends(context_builder),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：alternatives 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    user_id = user.user_id
    rag = await agent.rag.query(
        f"{payload.destination} 替代方案 室内 下雨 小众景点",
        session_id=payload.session_id,
        trace_id=trace_id,
        provider_name=payload.provider,
        city_hint=payload.destination,
    )
    rag_sources = [source.model_dump() for source in rag.sources]
    context = await memory.build(
        user_id=user_id,
        session_id=payload.session_id,
        store=store,
        current_message=f"{payload.destination} 替代方案: {payload.issue}",
        rag_sources=rag_sources,
    )
    source_text = "\n".join(f"- {source.source} page {source.page or '-'}: {source.preview[:180]}" for source in rag.sources)
    prompt = (
        "你是旅行替代方案推荐 Agent。请使用中文回答。根据触发问题、原计划、分层记忆和 RAG 证据，提供 3-5 个替代方案。\n"
        "每个替代方案必须包含：替换地点、原因、适合场景、交通提醒和预算提醒。\n\n"
        f"目的地: {payload.destination}\n"
        f"触发问题: {payload.issue}\n"
        f"原计划: {payload.original_plan}\n"
        f"分层记忆上下文:\n{context.prompt_context}\n"
        f"RAG 证据:\n{source_text}"
    )
    provider = agent.providers.resolve(payload.provider)
    answer = await provider.chat([ModelMessage(role="user", content=prompt)], model=agent.providers.settings.qwen_chat_model)
    await store.append(payload.session_id, "user", f"{payload.destination} 替代方案：{payload.issue}", user_id=user_id)
    await store.append(payload.session_id, "assistant", answer, user_id=user_id)
    await memory.compressor.compress_if_needed(user_id=user_id, session_id=payload.session_id, store=store)
    return success(
        {
            "trace_id": trace_id,
            "user_id": user_id,
            "answer": answer,
            "sources": rag_sources,
            "latency_ms": rag.latency_ms,
        }
    )


def _append_context_to_preferences(preferences: str, prompt_context: str) -> str:
    """说明：_append_context_to_preferences 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    if not prompt_context:
        return preferences
    return (
        f"{preferences or '无'}\n\n"
        "分层记忆上下文如下，请尊重用户长期偏好和最近对话，但不要暴露内部字段名：\n"
        f"{prompt_context}"
    )


def _plan_user_message(payload: TripPlanRequest) -> str:
    """说明：_plan_user_message 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return f"请从 {payload.departure} 出发，安排 {payload.destination} {payload.days} 天游。预算：{payload.budget or '未指定'}。偏好：{payload.preferences or '无'}。"


def _extract_places(text: str) -> list[str]:
    """说明：_extract_places 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    candidates: list[str] = []
    stop_words = {"time", "place", "plan", "transport", "food", "hotel", "cost", "notes", "day", "时间", "地点"}
    for line in text.splitlines():
        parts = [part.strip(" *|-:：") for part in re.split(r"[|,;，；]", line)]
        for part in parts:
            clean = part.strip()
            if 2 <= len(clean) <= 40 and clean.lower() not in stop_words and not re.fullmatch(r"\d{1,2}:\d{2}", clean):
                candidates.append(clean)
    return candidates


def _dedupe(items: list[str]) -> list[str]:
    """说明：_dedupe 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    result: list[str] = []
    for item in items:
        clean = item.strip()
        if clean and clean not in result:
            result.append(clean)
    return result


def _build_travel_search_query(payload: WebEnhancedPlanRequest) -> str:
    """说明：_build_travel_search_query 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return " ".join(
        [
            payload.destination,
            f"{payload.days}天旅行",
            payload.preferences,
            "最新开放时间 门票 预约 限流 政策 活动",
        ]
    ).strip()


def _format_web_sources_for_prompt(web_sources: list[dict], fallback: str) -> str:
    """说明：_format_web_sources_for_prompt 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    if not web_sources:
        return fallback
    lines = []
    for index, item in enumerate(web_sources, start=1):
        lines.append(
            "\n".join(
                [
                    f"{index}. {item.get('title') or '-'}",
                    f"Source: {item.get('source') or '-'}",
                    f"URL: {item.get('url') or '-'}",
                    f"Snippet: {item.get('snippet') or '-'}",
                    f"Published: {item.get('published_at') or '-'}",
                ]
            )
        )
    return "\n\n".join(lines)
