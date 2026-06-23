"""
旅行助手 源码组件。


"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.rag.indexer import RagIndexer


async def main() -> None:
    """说明：main 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    result = await RagIndexer().rebuild()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
