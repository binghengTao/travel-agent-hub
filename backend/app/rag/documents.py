"""
旅行助手 源码组件。


"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass


@dataclass
class Chunk:
    """Chunk"""
    chunk_id: str
    text: str
    source: str
    city: str
    page: int

    def to_dict(self) -> dict:
        """说明：to_dict 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return asdict(self)


def make_chunk_id(source: str, page: int, text: str) -> str:
    """说明：make_chunk_id 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    digest = hashlib.sha256(f"{source}:{page}:{text}".encode("utf-8")).hexdigest()[:16]
    return f"{source}:{page}:{digest}"
