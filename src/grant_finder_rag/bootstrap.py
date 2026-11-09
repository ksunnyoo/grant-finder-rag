"""구현체를 환경 설정에 따라 조립하는 곳. 무거운 모듈은 함수 안에서 불러와 import가 가볍게 유지된다."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grant_finder_rag.generation.fallback_llm import FallbackLLM
    from grant_finder_rag.retrieval.pipeline import Retriever
    from grant_finder_rag.storage.qdrant_store import QdrantStore

DEFAULT_REFUSE_THRESHOLD = 0.05


def refuse_threshold() -> float:
    """답변 거절 기준 점수. 환경 변수가 없으면 기본값(0.05)을 쓴다."""
    return float(os.getenv("REFUSE_THRESHOLD", str(DEFAULT_REFUSE_THRESHOLD)))


def build_retriever(with_reranker: bool) -> tuple[Retriever, QdrantStore]:
    from grant_finder_rag.embedding import bm25_sparse, ollama_embedder
    from grant_finder_rag.retrieval import pipeline
    from grant_finder_rag.storage import qdrant_store

    reranker = None
    if with_reranker:
        from grant_finder_rag.embedding.bge_reranker import BgeReranker

        reranker = BgeReranker()
    embedder = ollama_embedder.OllamaEmbedder(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_EMBED_MODEL", "bge-m3"),
    )
    sparse_encoder = bm25_sparse.Bm25SparseEncoder.load(Path("data/index/bm25.json"))
    store = qdrant_store.QdrantStore()
    return pipeline.Retriever(embedder, sparse_encoder, store, reranker), store


def build_llm(order_text: str | None = None) -> FallbackLLM:
    from grant_finder_rag.generation import fallback_llm
    from grant_finder_rag.llm import factory

    order = factory.parse_order(order_text or os.getenv("LLM_PROVIDER_ORDER", "ollama"))
    return fallback_llm.FallbackLLM(factory.build_providers(order, os.environ))
