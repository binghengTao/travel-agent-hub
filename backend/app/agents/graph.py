"""
旅行助手 源码组件。


"""

from __future__ import annotations

import time
from typing import Any, Literal, TypedDict

from app.agents.supervisor import AgentResult, SupervisorAgent
from app.schemas.common import Source, ToolCall
from app.services.model_provider import ModelMessage
from app.tools.travel_tools import to_tool_call


GraphRoute = Literal["planner", "rag", "copywriter", "realtime", "mixed", "general"]


class TravelGraphState(TypedDict, total=False):
    """TravelGraphState"""
    # StateGraph 的所有节点都读写这个状态字典；字段保持扁平，前端展示执行轨迹更容易。
    run_id: str
    trace_id: str
    session_id: str
    user_query: str
    provider: str
    profile: dict[str, Any]
    intent: dict[str, Any]
    route: GraphRoute
    evidence: list[str]
    sources: list[Source]
    tool_calls: list[ToolCall]
    plan_markdown: str
    draft_answer: str
    final_answer: str
    verified: bool
    warnings: list[str]
    steps: list[dict[str, Any]]
    retry_count: int
    max_retries: int
    graph_engine: str


class TravelAgentGraph:
    """LangGraph-native travel agent workflow.

    Nodes:
    router -> tool -> rag -> planner -> answer -> critic
                                      ^          |
                                      | retry    |
                                      +-- revise-+

    The graph is intentionally controlled: agents exchange state through
    TravelGraphState instead of chatting freely with each other.
    """

    def __init__(self, supervisor: SupervisorAgent):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.supervisor = supervisor
        self._compiled = self._compile()

    @property
    def available(self) -> bool:
        """说明：available 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return self._compiled is not None

    async def run(
        self,
        message: str,
        *,
        session_id: str,
        trace_id: str,
        run_id: str,
        provider: str = "auto",
        profile: dict[str, Any] | None = None,
    ) -> AgentResult:
        """说明：run 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if self._compiled is None:
            # 兜底路径保持和 LangGraph 返回结构一致，前端不用关心底层执行引擎是否可用。
            result = await self.supervisor.handle(message, session_id=session_id, trace_id=trace_id, provider=provider)
            result.metadata["graph_engine"] = "supervisor_fallback"
            return result

        # 初始状态只放请求级上下文，后续证据、工具调用和告警都由节点逐步补充。
        initial: TravelGraphState = {
            "run_id": run_id,
            "trace_id": trace_id,
            "session_id": session_id,
            "user_query": message,
            "provider": provider,
            "profile": profile or {},
            "evidence": [],
            "sources": [],
            "tool_calls": [],
            "warnings": [],
            "steps": [],
            "retry_count": 0,
            "max_retries": 2,
            "graph_engine": "langgraph_stategraph",
        }
        final_state = await self._compiled.ainvoke(
            initial,
            config={"configurable": {"thread_id": run_id}},
        )
        intent = final_state.get("intent", {})
        route = final_state.get("route", "general")
        return AgentResult(
            answer=final_state.get("final_answer") or final_state.get("draft_answer") or "",
            route=route,  # type: ignore[arg-type]
            sources=final_state.get("sources", []),
            tool_calls=final_state.get("tool_calls", []),
            verified=final_state.get("verified", True),
            warnings=final_state.get("warnings", []),
            metadata={
                "intent": intent,
                "plan": {"markdown": final_state.get("plan_markdown") or final_state.get("final_answer", "")}
                if intent.get("need_plan")
                else None,
                "graph_engine": final_state.get("graph_engine"),
                "retry_count": final_state.get("retry_count", 0),
            },
            steps=final_state.get("steps", []),
        )

    def _compile(self):
        """说明：_compile 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        try:
            from langgraph.checkpoint.memory import MemorySaver
            from langgraph.graph import END, StateGraph
        except Exception:
            # LangGraph 是增强能力，不是启动硬依赖；缺失时退回 Supervisor 规则调度。
            return None

        graph = StateGraph(TravelGraphState)
        # 节点顺序体现“先路由、再收集证据、最后生成和校验”的可控 Agent 思路。
        graph.add_node("router", self._router_node)
        graph.add_node("tool", self._tool_node)
        graph.add_node("rag", self._rag_node)
        graph.add_node("planner", self._planner_node)
        graph.add_node("answer", self._answer_node)
        graph.add_node("critic", self._critic_node)
        graph.add_node("revise", self._revise_node)

        graph.set_entry_point("router")
        graph.add_edge("router", "tool")
        graph.add_edge("tool", "rag")
        graph.add_edge("rag", "planner")
        graph.add_edge("planner", "answer")
        graph.add_edge("answer", "critic")
        # Critic 不直接重跑完整图，只在需要时进入 revise，避免多 Agent 自由循环。
        graph.add_conditional_edges("critic", self._critic_route, {"revise": "revise", "end": END})
        graph.add_edge("revise", "critic")
        return graph.compile(checkpointer=MemorySaver(), name="travel_assistant_graph")

    async def _router_node(self, state: TravelGraphState) -> TravelGraphState:
        """说明：_router_node 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        decision = self.supervisor.analyze_intent(state["user_query"])
        update: TravelGraphState = {
            "intent": decision.model_dump(),
            "route": decision.intent,
            "steps": _with_step(
                state,
                "RouterAgent",
                "success",
                f"intent={decision.intent}, destination={decision.destination or '-'}",
            ),
        }
        return update

    async def _tool_node(self, state: TravelGraphState) -> TravelGraphState:
        """说明：_tool_node 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        intent = state.get("intent", {})
        tool_calls = list(state.get("tool_calls", []))
        evidence = list(state.get("evidence", []))
        steps = list(state.get("steps", []))

        if intent.get("need_weather"):
            city = intent.get("destination") or "北京"
            started = time.perf_counter()
            # ToolAgent 只调用工具并沉淀 evidence，不直接写最终答案。
            result = await self.supervisor.tools.weather(city, days=1)
            tool_calls.append(to_tool_call(result, {"city": city, "days": 1}))
            evidence.append(f"天气工具结果: {result.content}")
            steps.append(_step("ToolAgent.weather_tool", "success", str(result.content)[:140], _elapsed(started)))

        if intent.get("need_map"):
            city = intent.get("destination") or ""
            started = time.perf_counter()
            result = await self.supervisor.tools.nearby(intent.get("destination") or state["user_query"], city, "景点")
            tool_calls.append(to_tool_call(result, {"location": intent.get("destination") or state["user_query"], "city": city, "keyword": "景点"}))
            evidence.append(f"地图/POI 工具结果: {result.content}")
            steps.append(_step("ToolAgent.amap_poi_tool", "success", str(result.content)[:140], _elapsed(started)))

        if intent.get("need_search"):
            started = time.perf_counter()
            result = await self.supervisor.tools.web_search(state["user_query"])
            tool_calls.append(to_tool_call(result, {"query": state["user_query"]}))
            evidence.append(f"联网搜索结果: {result.content}")
            steps.append(_step("ToolAgent.web_search_tool", "success", str(result.content)[:140], _elapsed(started)))

        if not any([intent.get("need_weather"), intent.get("need_map"), intent.get("need_search")]):
            steps.append(_step("ToolAgent", "skipped", "no external tool required"))

        return {"tool_calls": tool_calls, "evidence": evidence, "steps": steps}

    async def _rag_node(self, state: TravelGraphState) -> TravelGraphState:
        """说明：_rag_node 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        intent = state.get("intent", {})
        if not intent.get("need_rag"):
            return {"steps": _with_step(state, "RAGAgent", "skipped", "no retrieval required")}

        started = time.perf_counter()
        # RAGAgent 只返回来源和证据块，最终表达交给 AnswerComposer 统一整理。
        response = await self.supervisor.rag.query(
            state["user_query"],
            session_id=state["session_id"],
            trace_id=state["trace_id"],
            provider_name=state.get("provider", "auto"),
            city_hint=intent.get("destination"),
        )
        evidence = list(state.get("evidence", []))
        evidence.append(
            "RAG 证据:\n"
            + "\n".join(f"- {source.source} 第{source.page or '-'}页: {source.preview[:180]}" for source in response.sources)
        )
        steps = list(state.get("steps", []))
        steps.append(_step("RAGAgent", "success", f"retrieved {len(response.sources)} sources", _elapsed(started)))
        return {"sources": response.sources, "evidence": evidence, "steps": steps}

    async def _planner_node(self, state: TravelGraphState) -> TravelGraphState:
        """说明：_planner_node 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        intent = state.get("intent", {})
        if not intent.get("need_plan"):
            return {"steps": _with_step(state, "PlannerAgent", "skipped", "no plan required")}

        provider = self.supervisor.providers.resolve(state.get("provider", "auto"))
        destination = intent.get("destination") or "目的地"
        days = intent.get("days") or 1
        profile = state.get("profile") or {}
        # PlannerAgent 接收用户画像、工具结果和 RAG 证据，生成结构化行程草稿。
        prompt = (
            "你是 PlannerAgent。请基于用户问题、用户画像、工具结果和 RAG 证据生成结构化旅行计划。\n"
            "要求包含每日时间线、交通建议、预算提醒、替代方案和风险提示。\n\n"
            f"用户问题:{state['user_query']}\n目的地:{destination}\n天数:{days}\n用户画像:{profile}\n\n"
            f"{chr(10).join(state.get('evidence', []))}"
        )
        started = time.perf_counter()
        plan = await provider.chat([ModelMessage(role="user", content=prompt)], model=self.supervisor.providers.settings.qwen_chat_model)
        return {
            "plan_markdown": plan,
            "draft_answer": plan,
            "steps": _with_step(state, "PlannerAgent", "success", f"generated {days} day plan", _elapsed(started)),
        }

    async def _answer_node(self, state: TravelGraphState) -> TravelGraphState:
        """说明：_answer_node 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        intent = state.get("intent", {})
        provider = self.supervisor.providers.resolve(state.get("provider", "auto"))

        # AnswerComposer 根据路由结果选择表达风格，避免每个 Agent 都直接面向用户输出。
        if intent.get("need_copywriting"):
            system = "你是 CopywritingAgent，负责生成自然、有画面感、适合发布的旅行文案。"
        elif state.get("plan_markdown"):
            system = "你是 AnswerComposer，负责把 PlannerAgent 的计划和证据整理成最终答案。"
        elif intent.get("need_rag") or state.get("evidence"):
            system = "你是 AnswerComposer，必须基于 RAG 和工具证据回答，并在末尾列出引用来源。"
        else:
            system = "你是 旅行助手 的通用旅行助手。"

        prompt = (
            f"用户问题:{state['user_query']}\n"
            f"Router结果:{intent}\n"
            f"用户画像:{state.get('profile') or {}}\n"
            f"计划草稿:{state.get('plan_markdown', '')}\n"
            f"证据:\n{chr(10).join(state.get('evidence', []))}\n\n"
            "请生成最终回答。"
        )
        started = time.perf_counter()
        answer = await provider.chat(
            [ModelMessage(role="system", content=system), ModelMessage(role="user", content=prompt)],
            model=self.supervisor.providers.settings.qwen_chat_model,
        )
        return {"final_answer": answer, "steps": _with_step(state, "AnswerComposer", "success", "final answer composed", _elapsed(started))}

    async def _critic_node(self, state: TravelGraphState) -> TravelGraphState:
        """说明：_critic_node 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        intent = state.get("intent", {})
        answer = state.get("final_answer") or state.get("draft_answer") or ""
        verified = True
        warnings: list[str] = []

        # CriticAgent 用规则先做硬约束检查：天数、引用和实时信息证据都在这里兜底。
        if intent.get("need_plan"):
            verified, warnings = self.supervisor.verifier.verify_trip_plan(answer, int(intent.get("days") or 1))
        elif intent.get("need_rag"):
            verified, warnings = self.supervisor.verifier.verify_rag_answer(answer, len(state.get("sources", [])))

        status = "success" if verified else "warning"
        summary = "quality gates passed" if verified else "; ".join(warnings)
        return {"verified": verified, "warnings": warnings, "steps": _with_step(state, "CriticAgent", status, summary)}

    async def _revise_node(self, state: TravelGraphState) -> TravelGraphState:
        """说明：_revise_node 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        provider = self.supervisor.providers.resolve(state.get("provider", "auto"))
        retry_count = int(state.get("retry_count", 0)) + 1
        prompt = (
            "CriticAgent 发现上一版答案存在问题，请根据反馈重写答案。\n"
            f"用户问题:{state['user_query']}\n"
            f"反馈:{state.get('warnings', [])}\n"
            f"上一版答案:{state.get('final_answer', '')}\n"
            f"证据:{chr(10).join(state.get('evidence', []))}"
        )
        started = time.perf_counter()
        revised = await provider.chat([ModelMessage(role="user", content=prompt)], model=self.supervisor.providers.settings.qwen_chat_model)
        return {
            "retry_count": retry_count,
            "final_answer": revised,
            "steps": _with_step(state, "ReviseAgent", "success", f"revision attempt {retry_count}", _elapsed(started)),
        }

    def _critic_route(self, state: TravelGraphState) -> Literal["revise", "end"]:
        """说明：_critic_route 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if state.get("verified", True):
            return "end"
        if int(state.get("retry_count", 0)) >= int(state.get("max_retries", 2)):
            return "end"
        # 只允许有限次修订，避免工作流因为模型输出不稳定而无限循环。
        return "revise"


def _step(name: str, status: str, summary: str, latency_ms: int | None = None) -> dict[str, Any]:
    """说明：_step 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    payload: dict[str, Any] = {"name": name, "status": status, "summary": summary}
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    return payload


def _with_step(state: TravelGraphState, name: str, status: str, summary: str, latency_ms: int | None = None) -> list[dict[str, Any]]:
    """说明：_with_step 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return list(state.get("steps", [])) + [_step(name, status, summary, latency_ms)]


def _elapsed(started: float) -> int:
    """说明：_elapsed 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return int((time.perf_counter() - started) * 1000)


def build_travel_graph(supervisor: SupervisorAgent) -> TravelAgentGraph:
    """说明：build_travel_graph 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return TravelAgentGraph(supervisor)
