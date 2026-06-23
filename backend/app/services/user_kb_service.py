"""
旅行助手 源码组件。


"""

from __future__ import annotations

import json
import pickle
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import Settings, get_settings
from app.rag.documents import Chunk, make_chunk_id
from app.rag.indexer import _extract_pdf_pages, _tokenize_for_bm25, split_text
from app.schemas.common import Source
from app.schemas.rag import RagQueryResponse
from app.schemas.user_kb import UserTextDocumentRequest
from app.services.model_provider import ModelMessage, ProviderRegistry, cosine


USER_KB_EXTENSIONS = {".pdf", ".md", ".txt"}
USER_KB_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/octet-stream",
}


class UserKbService:
    """Per-user knowledge base.

    Public curated guides remain in `data/dataset`. User uploads are isolated
    under `storage/user_kb/{user_id}` and are never written into the global RAG
    index unless an admin promotes them through the governance workflow.
    """

    def __init__(self, settings: Settings | None = None, providers: ProviderRegistry | None = None):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings or get_settings()
        self.providers = providers or ProviderRegistry(self.settings)

    async def upload_document(self, *, user_id: str, upload: UploadFile, city: str = "", tags: list[str] | None = None) -> dict:
        """说明：upload_document 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        # 文件名只取 basename，防止客户端通过路径穿越把文件写到用户目录外。
        original_name = Path(upload.filename or "document").name
        suffix = Path(original_name).suffix.lower()
        if suffix not in USER_KB_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF, Markdown and TXT files are supported.")
        if upload.content_type and upload.content_type not in USER_KB_CONTENT_TYPES:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Unsupported file type: {upload.content_type}")

        document_dir = self._documents_dir(user_id)
        document_dir.mkdir(parents=True, exist_ok=True)
        doc_id = f"{_safe_stem(Path(original_name).stem)}_{uuid4().hex[:8]}{suffix}"
        target = document_dir / doc_id
        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        size = 0
        with target.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    # 超过限制时立即删除半成品，避免 storage 中留下不可索引的残缺文件。
                    target.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="Uploaded file is too large.")
                handle.write(chunk)

        # manifest 是用户私有知识库的轻量目录，索引重建时会读取这里的城市、标签和可信度。
        manifest = self._load_manifest(user_id)
        record = {
            "doc_id": doc_id,
            "name": doc_id,
            "original_name": original_name,
            "city": city,
            "tags": tags or [],
            "source_type": "user_upload",
            "trust_level": "user_provided",
            "size": target.stat().st_size,
            "created_at": _now(),
        }
        manifest["documents"] = [item for item in manifest["documents"] if item.get("doc_id") != doc_id] + [record]
        self._save_manifest(user_id, manifest)
        return record

    def register_text(self, *, user_id: str, payload: UserTextDocumentRequest) -> dict:
        """说明：register_text 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        document_dir = self._documents_dir(user_id)
        document_dir.mkdir(parents=True, exist_ok=True)
        doc_id = f"{_safe_stem(payload.title)}_{uuid4().hex[:8]}.md"
        target = document_dir / doc_id
        target.write_text(_format_user_text_document(payload), encoding="utf-8")

        manifest = self._load_manifest(user_id)
        record = {
            "doc_id": doc_id,
            "name": doc_id,
            "original_name": payload.title,
            "city": payload.city,
            "tags": payload.tags,
            "source_note": payload.source_note,
            "source_type": "user_note",
            "trust_level": payload.trust_level,
            "size": target.stat().st_size,
            "created_at": _now(),
        }
        manifest["documents"] = [item for item in manifest["documents"] if item.get("doc_id") != doc_id] + [record]
        self._save_manifest(user_id, manifest)
        return record

    def list_documents(self, user_id: str) -> dict:
        """说明：list_documents 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        manifest = self._load_manifest(user_id)
        docs = []
        for item in manifest["documents"]:
            path = self._documents_dir(user_id) / Path(item.get("doc_id", "")).name
            if not path.exists():
                continue
            docs.append({**item, "size": path.stat().st_size})
        return {"documents": sorted(docs, key=lambda item: item.get("created_at", ""), reverse=True), "count": len(docs)}

    def delete_document(self, *, user_id: str, doc_id: str) -> dict:
        """说明：delete_document 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        safe_doc_id = Path(doc_id).name
        path = self._documents_dir(user_id) / safe_doc_id
        if not path.exists() or path.suffix.lower() not in USER_KB_EXTENSIONS:
            raise HTTPException(status_code=404, detail="Document not found.")
        path.unlink()
        manifest = self._load_manifest(user_id)
        manifest["documents"] = [item for item in manifest["documents"] if item.get("doc_id") != safe_doc_id]
        self._save_manifest(user_id, manifest)
        return {"doc_id": safe_doc_id, "deleted": True, "needs_reindex": True}

    async def rebuild(self, user_id: str) -> dict:
        """说明：rebuild 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        # 每个用户独立索引目录，避免个人上传内容污染公共 Chroma/BM25。
        self._base_dir(user_id).mkdir(parents=True, exist_ok=True)
        self._index_dir(user_id).mkdir(parents=True, exist_ok=True)
        chunks: list[Chunk] = []
        docs = self.list_documents(user_id)["documents"]
        metadata_by_doc_id = {item["doc_id"]: item for item in docs}
        for doc in docs:
            path = self._documents_dir(user_id) / doc["doc_id"]
            if path.suffix.lower() == ".pdf":
                # PDF 走页级解析，metadata 中保留 page，方便回答时展示引用来源。
                chunks.extend(self._read_pdf_chunks(user_id, path, metadata_by_doc_id.get(doc["doc_id"], {})))
            else:
                chunks.extend(self._read_text_chunks(user_id, path, metadata_by_doc_id.get(doc["doc_id"], {})))

        # 私有库也同时写 dense 与 sparse 索引，查询逻辑和公共库保持一致。
        self._write_chunks(user_id, chunks)
        self._write_bm25(user_id, chunks)
        chroma_enabled = await self._write_chroma(user_id, chunks)
        return {
            "scope": "personal",
            "user_id": user_id,
            "files": len(docs),
            "chunks": len(chunks),
            "chroma_enabled": chroma_enabled,
            "bm25_path": str(self._bm25_path(user_id)),
        }

    async def query(
        self,
        question: str,
        *,
        user_id: str,
        session_id: str,
        trace_id: str,
        provider_name: str = "auto",
        city_hint: str | None = None,
    ) -> RagQueryResponse:
        """说明：query 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        started = time.perf_counter()
        chunks = self.load_chunks(user_id)
        if not chunks:
            # 查询时发现用户忘记重建索引，自动补一次，降低“上传后不能问”的使用成本。
            await self.rebuild(user_id)
            chunks = self.load_chunks(user_id)
        if not chunks:
            return RagQueryResponse(
                answer="你的个人知识库还没有可用内容。可以先在“我的文件”上传 PDF、Markdown 或 TXT，然后重建个人索引。",
                trace_id=trace_id,
                session_id=session_id,
                latency_ms=_latency(started),
                sources=[],
                rerank_scores=[],
            )

        # personal RAG 同样使用 dense + BM25 + RRF + rerank，保证个人文件问答质量。
        dense = await self._dense_search(question, user_id, chunks)
        sparse = self._bm25_search(question, user_id)
        merged_ids = _rrf_merge([dense, sparse], limit=max(self.settings.rerank_top_k, self.settings.final_top_k))
        candidate_chunks = [chunk for chunk in chunks if chunk.chunk_id in merged_ids]
        if city_hint:
            hinted = [chunk for chunk in candidate_chunks if city_hint in chunk.city or city_hint in chunk.source]
            candidate_chunks = hinted or candidate_chunks

        provider = self.providers.resolve(provider_name)
        reranked = await provider.rerank(question, [chunk.text for chunk in candidate_chunks], self.settings.final_top_k)
        selected = [(candidate_chunks[index], score) for index, score in reranked if index < len(candidate_chunks)]
        context = "\n\n".join(f"[{idx + 1}] 来源:{chunk.source} 第{chunk.page}段\n{chunk.text}" for idx, (chunk, _) in enumerate(selected))
        answer = await provider.chat(
            [
                {
                    "role": "system",
                    "content": "你是用户私有知识库问答助手。只能基于用户个人文件和笔记回答，并在结尾列出引用来源。不要把用户文件内容写入公共知识库。",
                },
                {"role": "user", "content": f"用户个人资料:\n{context}\n\n问题:{question}"},
            ],
            temperature=0.2,
        )
        return RagQueryResponse(
            answer=answer,
            trace_id=trace_id,
            session_id=session_id,
            latency_ms=_latency(started),
            sources=[
                Source(
                    source=chunk.source,
                    city=chunk.city,
                    page=chunk.page,
                    chunk_id=chunk.chunk_id,
                    score=score,
                    preview=chunk.text[:180],
                    scope="personal",
                    owner_id=user_id,
                    source_type="user_upload",
                    trust_level="user_provided",
                )
                for chunk, score in selected
            ],
            rerank_scores=[score for _, score in selected],
        )

    def load_chunks(self, user_id: str) -> list[Chunk]:
        """说明：load_chunks 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        path = self._chunks_path(user_id)
        if not path.exists():
            return []
        chunks = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    chunks.append(Chunk(**json.loads(line)))
        return chunks

    def _read_pdf_chunks(self, user_id: str, pdf: Path, metadata: dict[str, Any]) -> list[Chunk]:
        """说明：_read_pdf_chunks 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        pages = _extract_pdf_pages(pdf)
        city = metadata.get("city") or _city_from_name(pdf.stem)
        chunks: list[Chunk] = []
        for page_number, page_text in pages:
            for text in split_text(page_text, self.settings.chunk_size, self.settings.chunk_overlap):
                if len(text.strip()) < 40:
                    continue
                chunks.append(
                    Chunk(
                        chunk_id=f"user:{user_id}:{make_chunk_id(pdf.name, page_number, text)}",
                        text=text,
                        source=pdf.name,
                        city=city,
                        page=page_number,
                    )
                )
        return chunks

    def _read_text_chunks(self, user_id: str, path: Path, metadata: dict[str, Any]) -> list[Chunk]:
        """说明：_read_text_chunks 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        text = path.read_text(encoding="utf-8", errors="ignore")
        city = metadata.get("city") or _city_from_name(path.stem)
        chunks: list[Chunk] = []
        for index, chunk_text in enumerate(split_text(text, self.settings.chunk_size, self.settings.chunk_overlap), start=1):
            if len(chunk_text.strip()) < 40:
                continue
            chunks.append(
                Chunk(
                    chunk_id=f"user:{user_id}:{make_chunk_id(path.name, index, chunk_text)}",
                    text=chunk_text,
                    source=path.name,
                    city=city,
                    page=index,
                )
            )
        return chunks

    def _write_chunks(self, user_id: str, chunks: list[Chunk]) -> None:
        """说明：_write_chunks 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        path = self._chunks_path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")

    def _write_bm25(self, user_id: str, chunks: list[Chunk]) -> None:
        """说明：_write_bm25 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        path = self._bm25_path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            from rank_bm25 import BM25Okapi

            tokenized = [_tokenize_for_bm25(chunk.text) for chunk in chunks]
            bm25 = BM25Okapi(tokenized) if tokenized else None
            with path.open("wb") as handle:
                pickle.dump({"bm25": bm25, "chunk_ids": [chunk.chunk_id for chunk in chunks]}, handle)
        except Exception:
            with path.open("wb") as handle:
                pickle.dump({"bm25": None, "chunk_ids": [chunk.chunk_id for chunk in chunks]}, handle)

    async def _write_chroma(self, user_id: str, chunks: list[Chunk]) -> bool:
        """说明：_write_chroma 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        try:
            import chromadb
        except Exception:
            return False

        client = chromadb.PersistentClient(path=str(self._chroma_dir(user_id)))
        collection = client.get_or_create_collection("travel_assistant_user_guides")
        existing = collection.count()
        if existing:
            ids = collection.get(include=[])["ids"]
            if ids:
                collection.delete(ids=ids)
        if not chunks:
            return True

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
                    {"source": chunk.source, "city": chunk.city, "page": chunk.page, "scope": "personal", "owner_id": user_id}
                    for chunk in batch
                ],
            )
        return True

    async def _dense_search(self, question: str, user_id: str, chunks: list[Chunk]) -> list[str]:
        """说明：_dense_search 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(self._chroma_dir(user_id)))
            collection = client.get_or_create_collection("travel_assistant_user_guides")
            if collection.count():
                provider = self.providers.resolve("auto")
                query_embedding = (await provider.embed([question]))[0]
                result = collection.query(query_embeddings=[query_embedding], n_results=self.settings.dense_top_k)
                return result.get("ids", [[]])[0]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("ChromaDB dense search failed for user %s, falling back to full embedding search: %s", user_id, exc)

        provider = self.providers.resolve("auto")
        query_embedding = (await provider.embed([question]))[0]
        embeddings = await provider.embed([chunk.text for chunk in chunks])
        scored = sorted(zip(chunks, embeddings), key=lambda item: cosine(query_embedding, item[1]), reverse=True)
        return [chunk.chunk_id for chunk, _ in scored[: self.settings.dense_top_k]]

    def _bm25_search(self, question: str, user_id: str) -> list[str]:
        """说明：_bm25_search 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        path = self._bm25_path(user_id)
        if not path.exists():
            return []
        try:
            with path.open("rb") as handle:
                payload = pickle.load(handle)
            bm25 = payload.get("bm25")
            chunk_ids = payload.get("chunk_ids", [])
            if bm25 is None:
                return []
            scores = bm25.get_scores(_tokenize_for_bm25(question))
            order = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
            return [chunk_ids[index] for index in order[: self.settings.bm25_top_k]]
        except Exception:
            return []

    def _base_dir(self, user_id: str) -> Path:
        """说明：_base_dir 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return self.settings.storage_dir / "user_kb" / _safe_user_id(user_id)

    def _documents_dir(self, user_id: str) -> Path:
        """说明：_documents_dir 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return self._base_dir(user_id) / "documents"

    def _index_dir(self, user_id: str) -> Path:
        """说明：_index_dir 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return self._base_dir(user_id) / "index"

    def _chroma_dir(self, user_id: str) -> Path:
        """说明：_chroma_dir 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return self._base_dir(user_id) / "chroma"

    def _manifest_path(self, user_id: str) -> Path:
        """说明：_manifest_path 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return self._base_dir(user_id) / "manifest.json"

    def _chunks_path(self, user_id: str) -> Path:
        """说明：_chunks_path 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return self._index_dir(user_id) / "chunks.jsonl"

    def _bm25_path(self, user_id: str) -> Path:
        """说明：_bm25_path 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return self._index_dir(user_id) / "bm25.pkl"

    def _load_manifest(self, user_id: str) -> dict:
        """说明：_load_manifest 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        path = self._manifest_path(user_id)
        if not path.exists():
            return {"documents": []}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"documents": []}
        data.setdefault("documents", [])
        return data

    def _save_manifest(self, user_id: str, manifest: dict) -> None:
        """说明：_save_manifest 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        path = self._manifest_path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _format_user_text_document(payload: UserTextDocumentRequest) -> str:
    """说明：_format_user_text_document 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return "\n".join(
        [
            f"# {payload.title}",
            "",
            f"- city: {payload.city}",
            f"- tags: {', '.join(payload.tags)}",
            f"- source_note: {payload.source_note}",
            f"- trust_level: {payload.trust_level}",
            "",
            payload.content.strip(),
            "",
        ]
    )


def _safe_stem(value: str) -> str:
    """说明：_safe_stem 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    stem = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", value, flags=re.UNICODE).strip("_")
    return stem[:48] or "document"


def _safe_user_id(user_id: str) -> str:
    """说明：_safe_user_id 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", user_id)[:80] or "user"


def _city_from_name(name: str) -> str:
    """说明：_city_from_name 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return name.replace("旅游攻略", "").replace("攻略", "").strip()


def _rrf_merge(rankings: list[list[str]], *, limit: int, k: int = 60) -> list[str]:
    """说明：_rrf_merge 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    return [chunk_id for chunk_id, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]]


def _latency(started: float) -> int:
    """说明：_latency 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return int((time.perf_counter() - started) * 1000)


def _now() -> str:
    """说明：_now 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return datetime.now(timezone.utc).isoformat()
