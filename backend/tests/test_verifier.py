"""
旅行助手 源码组件。


"""

from app.agents.verifier import Verifier


def test_trip_verifier_accepts_required_headers():
    """说明：test_trip_verifier_accepts_required_headers 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    answer = "| 日期 | 地点 | 行程计划 | 交通方式 | 餐饮安排 | 住宿安排 | 费用估算 | 备注 |\n| Day1 | 北京 | 游览 | 地铁 | 小吃 | 酒店 | 500 | 防晒 |"
    ok, warnings = Verifier().verify_trip_plan(answer, days=1)
    assert ok
    assert warnings == []
