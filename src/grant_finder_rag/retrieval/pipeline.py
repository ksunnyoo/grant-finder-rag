"""질문 -> 검색 -> (리랭크) -> 상위 N건. Port만 사용한다."""
import time

from grant_finder_rag.contracts.models import Candidate
from grant_finder_rag.contracts.ports import (
    EmbedderPort,
    RerankerPort,
    SearchPort,
    SparseEncoderPort,
)


def _ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


class Retriever:
    def __init__(
        self,
        embedder: EmbedderPort,
        sparse_encoder: SparseEncoderPort,
        search: SearchPort,
        reranker: RerankerPort | None = None,
    ) -> None:
        self.embedder = embedder
        self.sparse_encoder = sparse_encoder
        self.search = search
        self.reranker = reranker

    def retrieve(
        self,
        query: str,
        mode: str = "hybrid",
        candidates: int = 20,
        top_k: int = 5,
        rerank: bool = True,
    ) -> tuple[list[Candidate], dict[str, int]]:
        """리랭크를 쓰면 후보 candidates건을 찾아 재정렬하고, 아니면 top_k건만 찾는다."""
        use_rerank = rerank and self.reranker is not None
        stages: dict[str, int] = {}

        started = time.perf_counter()
        dense = self.embedder.embed([query])[0]
        sparse = self.sparse_encoder.encode_query(query)
        found = self.search.search(dense, sparse, mode, candidates if use_rerank else top_k)
        stages["search"] = _ms(started)

        if use_rerank and found:
            started = time.perf_counter()
            scores = self.reranker.rerank(query, [c.payload["text"] for c in found])
            found = sorted(
                (c.model_copy(update={"rerank_score": s}) for c, s in zip(found, scores, strict=True)),
                key=lambda c: c.rerank_score,
                reverse=True,
            )
            stages["rerank"] = _ms(started)
        return found[:top_k], stages
