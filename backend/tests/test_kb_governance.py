"""
旅行助手 源码组件。


"""

import shutil
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings
from app.rag.indexer import RagIndexer
from app.services.kb_governance import KnowledgeGovernanceService, parse_tags


def _test_root() -> Path:
    """说明：_test_root 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    root = Path(__file__).resolve().parents[1] / "test_runtime" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def _settings(root: Path):
    """说明：_settings 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    storage = root / "storage"
    return Settings(
        dataset_dir=root / "dataset",
        storage_dir=storage,
        chroma_dir=storage / "chroma",
        bm25_dir=storage / "bm25",
        upload_dir=storage / "uploads",
        output_dir=storage / "outputs",
    )


def test_governance_analyzes_registers_and_plans_merge():
    """说明：test_governance_analyzes_registers_and_plans_merge 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    root = _test_root()
    try:
        settings = _settings(root)
        settings.dataset_dir.mkdir(parents=True)
        existing = settings.dataset_dir / "\u676d\u5dde\u65c5\u6e38\u653b\u7565.pdf"
        existing.write_bytes(b"%PDF-1.4")

        service = KnowledgeGovernanceService(settings)
        analysis = service.analyze_candidate(
            title="\u676d\u5dde\u897f\u6e56\u4e00\u65e5\u6e38\u653b\u7565",
            city="\u676d\u5dde",
            theme="\u897f\u6e56",
            tags=["\u897f\u6e56", "\u8def\u7ebf"],
            summary="\u65b0\u589e\u897f\u6e56\u96e8\u5929\u5907\u9009\u8def\u7ebf",
        )

        assert analysis["similar_docs"]
        assert analysis["similar_docs"][0]["name"] == existing.name
        assert analysis["recommendation"] in {"supplement", "merge", "replace_or_merge"}

        record = service.register_document(
            doc_id="westlake.md",
            name="westlake.md",
            city="\u676d\u5dde",
            theme="\u897f\u6e56",
            tags=["\u897f\u6e56"],
            source_note="manual",
            trust_level="high",
            action=analysis["recommendation"],
            analysis=analysis,
        )
        records = service.list_records()
        assert records["records"][0]["record_id"] == record["record_id"]

        plan = service.create_merge_plan(source_doc_ids=[existing.name, "westlake.md"], target_title="\u676d\u5dde\u897f\u6e56\u653b\u7565", strategy="merge")
        assert plan["source_docs"]
        assert "rebuild_chroma_and_bm25" in plan["next_steps"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_parse_tags_and_text_guide_chunking():
    """说明：test_parse_tags_and_text_guide_chunking 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    assert parse_tags("\u897f\u6e56,\u8def\u7ebf\u3001\u907f\u5751") == ["\u897f\u6e56", "\u8def\u7ebf", "\u907f\u5751"]

    root = _test_root()
    try:
        settings = _settings(root)
        settings.dataset_dir.mkdir(parents=True)
        guide = settings.dataset_dir / "\u676d\u5dde\u897f\u6e56.md"
        guide.write_text("# title\n" + "\u897f\u6e56\u4e00\u65e5\u6e38\u8def\u7ebf\u548c\u907f\u5751\u63d0\u793a" * 12, encoding="utf-8")

        indexer = RagIndexer(settings)
        chunks = indexer._read_text_chunks(guide)

        assert chunks
        assert chunks[0].source == guide.name
        assert chunks[0].city == "\u676d\u5dde\u897f\u6e56"
    finally:
        shutil.rmtree(root, ignore_errors=True)
