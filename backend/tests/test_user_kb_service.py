"""
旅行助手 源码组件。


"""

import asyncio
import shutil
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings
from app.schemas.user_kb import UserTextDocumentRequest
from app.services.user_kb_service import UserKbService


def _test_root() -> Path:
    """说明：_test_root 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    root = Path(__file__).resolve().parents[1] / "test_runtime" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_user_kb_register_reindex_query_and_isolation():
    """说明：test_user_kb_register_reindex_query_and_isolation 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    async def run():
        """说明：run 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        root = _test_root()
        try:
            settings = Settings(
                storage_dir=root / "storage",
                chroma_dir=root / "storage" / "chroma",
                bm25_dir=root / "storage" / "bm25",
                dataset_dir=root / "dataset",
            )
            service = UserKbService(settings, providers=None)
            service.register_text(
                user_id="u1",
                payload=UserTextDocumentRequest(
                    title="杭州西湖雨天攻略",
                    city="杭州",
                    tags=["西湖", "雨天"],
                    content="杭州西湖雨天适合安排博物馆、茶馆和湖滨商圈，傍晚雨小后再去白堤散步。",
                ),
            )

            assert service.list_documents("u1")["count"] == 1
            assert service.list_documents("u2")["count"] == 0

            rebuild = await service.rebuild("u1")
            assert rebuild["files"] == 1
            assert rebuild["chunks"] >= 1

            result = await service.query(
                "杭州下雨天怎么安排？",
                user_id="u1",
                session_id="s1",
                trace_id="t1",
            )
            assert result.sources
            assert result.sources[0].scope == "personal"
            assert result.sources[0].owner_id == "u1"
        finally:
            shutil.rmtree(root, ignore_errors=True)

    asyncio.run(run())
