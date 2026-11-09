"""명령줄 진입점. 구현체를 여기서 연결한다."""
import argparse
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from grant_finder_rag.embedding.bm25_sparse import Bm25SparseEncoder
from grant_finder_rag.embedding.ollama_embedder import OllamaEmbedder
from grant_finder_rag.retrieval.pipeline import Retriever
from grant_finder_rag.retrieval.query_analyzer import analyze_query
from grant_finder_rag.storage.qdrant_store import QdrantStore


def build_retriever(with_reranker: bool) -> tuple[Retriever, QdrantStore]:
    reranker = None
    if with_reranker:
        from grant_finder_rag.embedding.bge_reranker import BgeReranker

        reranker = BgeReranker()
    embedder = OllamaEmbedder(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_EMBED_MODEL", "bge-m3"),
    )
    sparse_encoder = Bm25SparseEncoder.load(Path("data/index/bm25.json"))
    store = QdrantStore()
    return Retriever(embedder, sparse_encoder, store, reranker), store


def cmd_search(args: argparse.Namespace) -> None:
    load_dotenv()
    as_of = date.fromisoformat(args.as_of or os.getenv("AS_OF_DATE") or date.today().isoformat())
    filters = None if args.no_filter else analyze_query(args.query, as_of)
    if filters is not None and args.include_closed:
        filters.include_closed = True

    use_rerank = not args.no_rerank
    retriever, store = build_retriever(with_reranker=use_rerank)
    try:
        results, stages = retriever.retrieve(
            args.query, mode=args.mode, top_k=args.k, rerank=use_rerank, filters=filters
        )
    finally:
        store.close()

    applied = filters.model_dump(mode="json", exclude_defaults=True) if filters else "없음"
    print("적용된 필터:", applied)
    for rank, c in enumerate(results, 1):
        p = c.payload
        rerank = f" rerank={c.rerank_score:.3f}" if c.rerank_score is not None else ""
        print(f"{rank}. [{c.score:.4f}{rerank}] {p['title']}")
        print(f"   {p['region']} | {p['category']} | 마감 {p['end_date']} | {p['url']}")
    print("단계별 시간(ms):", stages)


def main() -> None:
    parser = argparse.ArgumentParser(prog="grant-rag")
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search", help="검색 결과만 출력")
    search.add_argument("query")
    search.add_argument("--mode", choices=["dense", "sparse", "hybrid"], default="hybrid")
    search.add_argument("--no-rerank", action="store_true")
    search.add_argument("--no-filter", action="store_true", help="질문에서 조건을 추출하지 않음")
    search.add_argument("--include-closed", action="store_true", help="마감된 공고 포함")
    search.add_argument("--as-of", help="기준일 (YYYY-MM-DD). 기본은 .env의 AS_OF_DATE")
    search.add_argument("-k", type=int, default=5)
    search.set_defaults(func=cmd_search)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
