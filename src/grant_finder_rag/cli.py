"""명령줄 진입점. 구현체를 여기서 연결한다."""
import argparse
import os
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from grant_finder_rag.embedding.bm25_sparse import Bm25SparseEncoder
from grant_finder_rag.embedding.ollama_embedder import OllamaEmbedder
from grant_finder_rag.generation.answer import AnswerGenerator
from grant_finder_rag.generation.fallback_llm import FallbackLLM
from grant_finder_rag.llm.factory import build_providers, parse_order
from grant_finder_rag.retrieval.pipeline import Retriever
from grant_finder_rag.retrieval.query_analyzer import analyze_query
from grant_finder_rag.service import AskService
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


def build_llm(order_text: str | None = None) -> FallbackLLM:
    order = parse_order(order_text or os.getenv("LLM_PROVIDER_ORDER", "ollama"))
    return FallbackLLM(build_providers(order, os.environ))


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


def cmd_llm_test(args: argparse.Namespace) -> None:
    load_dotenv()
    llm = build_llm(args.providers)
    started = time.perf_counter()
    result = llm.generate("당신은 한국어로 간결하게 답하는 도우미입니다.", args.prompt)
    elapsed = round((time.perf_counter() - started) * 1000)
    print(f"공급자: {result.provider} ({elapsed}ms)")
    print(result.text)


def _d_day_label(d_day: int | None) -> str:
    if d_day is None:
        return "마감일 미기재"
    if d_day > 0:
        return f"D-{d_day}"
    return "D-day" if d_day == 0 else "마감"


def cmd_ask(args: argparse.Namespace) -> None:
    load_dotenv()
    as_of = date.fromisoformat(args.as_of or os.getenv("AS_OF_DATE") or date.today().isoformat())
    retriever, store = build_retriever(with_reranker=True)
    generator = AnswerGenerator(
        build_llm(args.providers), refuse_threshold=float(os.getenv("REFUSE_THRESHOLD", "0"))
    )
    service = AskService(retriever, generator, as_of)
    try:
        result = service.ask(args.query)
    finally:
        store.close()

    if result.refused:
        print(f"[답변 거절] 사유: {result.refuse_reason}")
    else:
        print(result.answer)
    for s in result.sources:
        flags = f" ({', '.join(s.flags)})" if s.flags else ""
        print(f"- [{s.id}] {s.title} | {s.region} | {s.end_date} {_d_day_label(s.d_day)}{flags}")
        print(f"  {s.url}")
    print("적용된 필터:", result.applied_filters)
    print(f"공급자: {result.llm_provider} | 단계별 시간(ms): {result.stages} | 총 {result.latency_ms}ms")


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

    llm_test = sub.add_parser("llm-test", help="LLM 공급자 동작 확인")
    llm_test.add_argument("prompt")
    llm_test.add_argument("--providers", help="예: ollama 또는 gemini,groq (기본은 .env)")
    llm_test.set_defaults(func=cmd_llm_test)

    ask = sub.add_parser("ask", help="질문에 답변 (검색 + 생성 + 출처)")
    ask.add_argument("query")
    ask.add_argument("--providers", help="예: gemini 또는 ollama,gemini (기본은 .env)")
    ask.add_argument("--as-of", help="기준일 (YYYY-MM-DD). 기본은 .env의 AS_OF_DATE")
    ask.set_defaults(func=cmd_ask)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
