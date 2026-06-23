"""
旅行助手 源码组件。


"""

import logging
import sys


def configure_logging() -> None:
    """说明：configure_logging 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


class TraceAdapter(logging.LoggerAdapter):
    """TraceAdapter"""
    def process(self, msg, kwargs):
        """说明：process 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("trace_id", "-")
        return msg, kwargs


def get_logger(name: str) -> TraceAdapter:
    """说明：get_logger 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return TraceAdapter(logging.getLogger(name), {})
