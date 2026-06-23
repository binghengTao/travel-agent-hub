"""
旅行助手 源码组件。


"""

from app.agents.graph import TravelAgentGraph


def test_langgraph_workflow_compiles():
    """说明：test_langgraph_workflow_compiles 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    graph = TravelAgentGraph(supervisor=object())  # type: ignore[arg-type]
    assert graph.available
