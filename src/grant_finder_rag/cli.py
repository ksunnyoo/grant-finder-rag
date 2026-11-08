"""명령줄 진입점. 구현체를 여기서 연결한다."""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from grant_finder_rag.embedding.bm25_sparse import Bm25SparseEncoder
from grant_finder_rag.embedding.ollama_embedder import OllamaEmbedder
from grant_finder_rag.retrieval.pipeline import Retriever
from grant_finder_rag.storage.qdrant_store import QdrantStore


def build_retriever(with_reranker: bool) -> tuple[Retriever, QdrantStore]:
    load_dotenv()
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
    use_rerank = not args.no_rerank
    retriever, store = build_retriever(with_reranker=use_rerank)
    try:
        results, stages = retriever.retrieve(
            args.query, mode=args.mode, top_k=args.k, rerank=use_rerank
        )
    finally:
        store.close()
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
    search.add_argument("-k", type=int, default=5)
    search.set_defaults(func=cmd_search)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
