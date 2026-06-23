"""
旅行助手 源码组件。


"""

from __future__ import annotations

import asyncio

from redis import Redis
from rq import Queue

from app.core.config import get_settings
from app.rag.indexer import RagIndexer


def get_queue() -> Queue:
    """说明：get_queue 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    return Queue("travelai", connection=Redis.from_url(settings.redis_url))


def enqueue_rebuild_index():
    """说明：enqueue_rebuild_index 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return get_queue().enqueue(rebuild_index_job)


def rebuild_index_job() -> dict:
    settings = get_settings()
    return asyncio.run(RagIndexer(settings).rebuild())
