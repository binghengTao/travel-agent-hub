"""
旅行助手 源码组件。


"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

from app.core.config import Settings, get_settings
from app.rag.documents import Chunk, make_chunk_id
from app.services.model_provider import ProviderRegistry


class RagIndexer:
    """RagIndexer"""
    def __init__(self, settings: Settings | None = None, providers: ProviderRegistry | None = None):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings or get_settings()
        self.providers = providers or ProviderRegistry(self.settings)
        self.chunks_path = self.settings.bm25_dir / "chunks.jsonl"
        self.bm25_path = self.settings.bm25_dir / "bm25.pkl"

    async def rebuild(self) -> dict:
        """说明：rebuild 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings.ensure_directories()
        chunks: list[Chunk] = []
        guide_files = _iter_guide_files(self.settings.dataset_dir)
        for guide in guide_files:
            if guide.suffix.lower() == ".pdf":
                chunks.extend(self._read_pdf_chunks(guide))
            else:
                chunks.extend(self._read_text_chunks(guide))

        self._write_chunks(chunks)
        self._write_bm25(chunks)
        chroma_enabled = await self._write_chroma(chunks)
        return {
            "files": len(guide_files),
            "chunks": len(chunks),
            "chroma_enabled": chroma_enabled,
            "bm25_path": str(self.bm25_path),
        }

    def _read_pdf_chunks(self, pdf: Path) -> list[Chunk]:
        """说明：_read_pdf_chunks 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        pages = _extract_pdf_pages(pdf)
        city = _city_from_name(pdf.stem)
        chunks: list[Chunk] = []
        for page_number, page_text in pages:
            for text in split_text(page_text, self.settings.chunk_size, self.settings.chunk_overlap):
                if len(text.strip()) < 40:
                    continue
                chunks.append(
                    Chunk(
                        chunk_id=make_chunk_id(pdf.name, page_number, text),
                        text=text,
                        source=pdf.name,
                        city=city,
                        page=page_number,
                    )
                )
        return chunks

    def _read_text_chunks(self, path: Path) -> list[Chunk]:
        """说明：_read_text_chunks 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        text = path.read_text(encoding="utf-8", errors="ignore")
        city = _city_from_name(path.stem)
        chunks: list[Chunk] = []
        for index, chunk_text in enumerate(split_text(text, self.settings.chunk_size, self.settings.chunk_overlap), start=1):
            if len(chunk_text.strip()) < 40:
                continue
            chunks.append(
                Chunk(
                    chunk_id=make_chunk_id(path.name, index, chunk_text),
                    text=chunk_text,
                    source=path.name,
                    city=city,
                    page=index,
                )
            )
        return chunks

    def _write_chunks(self, chunks: list[Chunk]) -> None:
        """说明：_write_chunks 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings.bm25_dir.mkdir(parents=True, exist_ok=True)
        with self.chunks_path.open("w", encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")

    def _write_bm25(self, chunks: list[Chunk]) -> None:
        """说明：_write_bm25 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        try:
            from rank_bm25 import BM25Okapi

            tokenized = [_tokenize_for_bm25(chunk.text) for chunk in chunks]
            bm25 = BM25Okapi(tokenized)
            with self.bm25_path.open("wb") as handle:
                pickle.dump({"bm25": bm25, "chunk_ids": [chunk.chunk_id for chunk in chunks]}, handle)
        except Exception:
            with self.bm25_path.open("wb") as handle:
                pickle.dump({"bm25": None, "chunk_ids": [chunk.chunk_id for chunk in chunks]}, handle)

    async def _write_chroma(self, chunks: list[Chunk]) -> bool:
        """说明：_write_chroma 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        try:
            import chromadb
        except Exception:
            return False

        client = chromadb.PersistentClient(path=str(self.settings.chroma_dir))
        collection = client.get_or_create_collection("travel_assistant_guides")
        existing = collection.count()
        if existing:
            ids = collection.get(include=[])["ids"]
            if ids:
                collection.delete(ids=ids)

        provider = self.providers.resolve("auto")
        batch_size = 32
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            embeddings = await provider.embed([chunk.text for chunk in batch])
            collection.add(
                ids=[chunk.chunk_id for chunk in batch],
                documents=[chunk.text for chunk in batch],
                embeddings=embeddings,
                metadatas=[
                    {"source": chunk.source, "city": chunk.city, "page": chunk.page}
                    for chunk in batch
                ],
            )
        return True

    def load_chunks(self) -> list[Chunk]:
        """说明：load_chunks 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if not self.chunks_path.exists():
            return []
        chunks = []
        with self.chunks_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    chunks.append(Chunk(**json.loads(line)))
        return chunks


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """说明：split_text 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    cleaned = " ".join(text.replace("\x00", " ").split())
    if not cleaned:
        return []
    chunks = []
    start = 0
    while start < len(cleaned):
        chunks.append(cleaned[start : start + chunk_size])
        if start + chunk_size >= len(cleaned):
            break
        start += max(chunk_size - overlap, 1)
    return chunks


def _extract_pdf_pages(pdf: Path) -> list[tuple[int, str]]:
    """说明：_extract_pdf_pages 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    try:
        import fitz

        with fitz.open(pdf) as document:
            return [(index + 1, page.get_text()) for index, page in enumerate(document)]
    except Exception:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf))
            return [(index + 1, page.extract_text() or "") for index, page in enumerate(reader.pages)]
        except Exception:
            return []


def _tokenize_for_bm25(text: str) -> list[str]:
    """说明：_tokenize_for_bm25 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    try:
        import jieba

        return [token for token in jieba.cut(text) if token.strip()]
    except Exception:
        return [token for token in text.lower().split() if token.strip()]


def _city_from_name(name: str) -> str:
    """说明：_city_from_name 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return name.replace("\u65c5\u6e38\u653b\u7565", "").replace("\u653b\u7565", "").strip()


def _iter_guide_files(dataset_dir: Path) -> list[Path]:
    """说明：_iter_guide_files 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    files: list[Path] = []
    for pattern in ("*.pdf", "*.md", "*.txt"):
        files.extend(dataset_dir.glob(pattern))
    return sorted(files, key=lambda path: path.name)
