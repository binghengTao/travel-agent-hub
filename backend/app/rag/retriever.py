"""
旅行助手 源码组件。


"""

from __future__ import annotations

import pickle
import time

from app.core.config import Settings, get_settings
from app.rag.documents import Chunk
from app.rag.indexer import RagIndexer, _tokenize_for_bm25
from app.schemas.common import Source
from app.schemas.rag import RagQueryResponse
from app.services.model_provider import ProviderRegistry, cosine


class RagService:
    """RagService"""
    def __init__(self, settings: Settings | None = None, providers: ProviderRegistry | None = None):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings or get_settings()
        self.providers = providers or ProviderRegistry(self.settings)
        self.indexer = RagIndexer(self.settings, self.providers)

    async def query(
        self,
        question: str,
        *,
        session_id: str,
        trace_id: str,
        provider_name: str = "auto",
        city_hint: str | None = None,
    ) -> RagQueryResponse:
        """说明：query 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        started = time.perf_counter()
        chunks = self.indexer.load_chunks()
        if not chunks:
            # 在线查询发现索引缺失时自动尝试重建，降低首次启动的演示门槛。
            await self.indexer.rebuild()
            chunks = self.indexer.load_chunks()
            if not chunks:
                return RagQueryResponse(
                    answer="公共知识库索引尚未建立，且当前未能从资料中读取到有效文本。",
                    trace_id=trace_id,
                    session_id=session_id,
                    latency_ms=_latency(started),
                    sources=[],
                    rerank_scores=[],
                )

        # 混合检索：dense 负责语义召回，BM25 负责景点名、城市名等关键词精确召回。
        dense = await self._dense_search(question, chunks)
        sparse = self._bm25_search(question)
        # RRF 合并两路召回结果，避免单一路径的排序偏差。
        merged_ids = _rrf_merge([dense, sparse], limit=max(self.settings.rerank_top_k, self.settings.final_top_k))
        candidate_chunks = [chunk for chunk in chunks if chunk.chunk_id in merged_ids]
        if city_hint:
            # RouterAgent 提取到目的地时，优先保留城市匹配证据；没有命中则不强行过滤。
            hinted = [chunk for chunk in candidate_chunks if city_hint in chunk.city or city_hint in chunk.source]
            candidate_chunks = hinted or candidate_chunks

        provider = self.providers.resolve(provider_name)
        # rerank 只作用于候选块，控制成本，同时提升最终引用来源的相关性。
        reranked = await provider.rerank(question, [chunk.text for chunk in candidate_chunks], self.settings.final_top_k)
        selected = [(candidate_chunks[index], score) for index, score in reranked if index < len(candidate_chunks)]
        context = "\n\n".join(
            f"[{idx + 1}] 来源:{chunk.source} 第{chunk.page}页\n{chunk.text}"
            for idx, (chunk, _) in enumerate(selected)
        )
        answer = await provider.chat(
            [
                {
                    "role": "system",
                    "content": "你是专业旅行知识库问答助手。必须只基于给定资料回答，并在结尾列出引用来源。",
                },
                {"role": "user", "content": f"资料:\n{context}\n\n问题:{question}"},
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
                    scope="global",
                    source_type="curated",
                    trust_level="high",
                )
                for chunk, score in selected
            ],
            rerank_scores=[score for _, score in selected],
        )

    async def _dense_search(self, question: str, chunks: list[Chunk]) -> list[str]:
        """说明：_dense_search 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        try:
            import chromadb

            # 优先读取持久化 Chroma，避免每次请求重新计算全量向量。
            client = chromadb.PersistentClient(path=str(self.settings.chroma_dir))
            collection = client.get_or_create_collection("travel_assistant_guides")
            if collection.count():
                provider = self.providers.resolve("auto")
                query_embedding = (await provider.embed([question]))[0]
                result = collection.query(query_embeddings=[query_embedding], n_results=self.settings.dense_top_k)
                return result.get("ids", [[]])[0]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("ChromaDB dense search failed, falling back to full embedding search: %s", exc)

        # Chroma 不可用时走小规模内存向量检索，保证本地演示不会因为向量库缺失直接失败。
        provider = self.providers.resolve("auto")
        query_embedding = (await provider.embed([question]))[0]
        sample = chunks[: min(len(chunks), 3000)]
        embeddings = await provider.embed([chunk.text for chunk in sample])
        scored = sorted(zip(sample, embeddings), key=lambda item: cosine(query_embedding, item[1]), reverse=True)
        return [chunk.chunk_id for chunk, _ in scored[: self.settings.dense_top_k]]

    def _bm25_search(self, question: str) -> list[str]:
        """说明：_bm25_search 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if not self.indexer.bm25_path.exists():
            return []
        try:
            with self.indexer.bm25_path.open("rb") as handle:
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


def _rrf_merge(rankings: list[list[str]], *, limit: int, k: int = 60) -> list[str]:
    """说明：_rrf_merge 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    scores: dict[str, float] = {}
    # Reciprocal Rank Fusion 只依赖名次，不依赖不同检索器的原始分数尺度。
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    return [chunk_id for chunk_id, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]]


def _latency(started: float) -> int:
    """说明：_latency 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return int((time.perf_counter() - started) * 1000)
