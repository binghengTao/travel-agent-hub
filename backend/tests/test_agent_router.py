"""
旅行助手 源码组件。


"""

from app.agents.supervisor import SupervisorAgent


def test_router_detects_mixed_travel_request():
    """说明：test_router_detects_mixed_travel_request 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    agent = SupervisorAgent.__new__(SupervisorAgent)
    agent._cities = ["杭州"]

    decision = agent.analyze_intent("明天杭州适合去西湖吗？顺便帮我安排一天路线。")

    assert decision.intent == "mixed"
    assert decision.destination == "杭州"
    assert decision.need_weather
    assert decision.need_rag
    assert decision.need_plan

