"""
旅行助手 源码组件。


"""

from app.core.response import success


def test_success_envelope_shape():
    """说明：test_success_envelope_shape 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    payload = success({"answer": "ok"})
    assert payload == {"code": 0, "message": "success", "data": {"answer": "ok"}}
