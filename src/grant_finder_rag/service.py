"""질문 하나를 처리하는 전체 흐름: 조건 추출 -> 검색 -> 거절 판단 -> 생성 -> 출처 검증."""
import time
from datetime import date

from grant_finder_rag.contracts.models import AskResult, Candidate, SearchFilters, Source
from grant_finder_rag.contracts.ports import RetrieverPort
from grant_finder_rag.generation.answer import AnswerGenerator
from grant_finder_rag.retrieval.query_analyzer import analyze_query, merge_filters


def _ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def make_snippet(text: str, limit: int = 160) -> str:
    """검색 문서에서 내용(없으면 대상) 구간의 앞부분을 근거 문장으로 쓴다."""
    for marker in ("[내용] ", "[대상] "):
        if marker in text:
            body = text.split(marker, 1)[1].split("\n[", 1)[0]
            return " ".join(body.split())[:limit]
    return text.split("\n", 1)[0][:limit]


def to_source(c: Candidate, filters: SearchFilters, as_of: date) -> Source:
    p = c.payload
    end = p.get("end_date")
    flags = []
    if filters.target and not p.get("target"):
        flags.append("대상 미기재")
    if filters.biz_age and not p.get("biz_age"):
        flags.append("업력 미기재")
    if filters.age is not None and not p.get("ages"):
        flags.append("연령 미기재")
    return Source(
        id=c.notice_id,
        title=p.get("title", ""),
        agency=p.get("agency"),
        category=p.get("category"),
        region=p.get("region"),
        end_date=end,
        d_day=(date.fromisoformat(end) - as_of).days if end else None,
        snippet=make_snippet(p.get("text", "")),
        url=p.get("url"),
        flags=flags,
    )


class AskService:
    def __init__(
        self,
        retriever: RetrieverPort,
        generator: AnswerGenerator,
        as_of_date: date,
        mode: str = "hybrid",
        candidates: int = 20,
        top_k: int = 5,
        rerank: bool = True,
    ) -> None:
        self.retriever = retriever
        self.generator = generator
        self.as_of_date = as_of_date
        self.mode = mode
        self.candidates = candidates
        self.top_k = top_k
        self.rerank = rerank

    def ask(self, question: str, explicit_filters: SearchFilters | None = None) -> AskResult:
        started = time.perf_counter()
        stages: dict[str, int] = {}

        step = time.perf_counter()
        filters = merge_filters(explicit_filters, analyze_query(question, self.as_of_date))
        stages["analyze"] = _ms(step)

        found, retrieval_stages = self.retriever.retrieve(
            question,
            mode=self.mode,
            candidates=self.candidates,
            top_k=self.top_k,
            rerank=self.rerank,
            filters=filters,
        )
        stages.update(retrieval_stages)

        applied = filters.model_dump(mode="json", exclude_defaults=True)
        as_of = self.as_of_date.isoformat()
        reason = self.generator.screen(found, filters.has_conditions())
        if reason:
            return AskResult(
                answer=None,
                refused=True,
                refuse_reason=reason,
                applied_filters=applied,
                as_of_date=as_of,
                stages=stages,
                latency_ms=_ms(started),
            )

        step = time.perf_counter()
        draft = self.generator.generate(question, found, self.as_of_date)
        stages["generate"] = _ms(step)
        by_id = {c.notice_id: c for c in found}
        return AskResult(
            answer=draft.answer,
            refused=draft.refused,
            refuse_reason=draft.refuse_reason,
            sources=[to_source(by_id[i], filters, self.as_of_date) for i in draft.cited_ids],
            applied_filters=applied,
            llm_provider=draft.provider,
            as_of_date=as_of,
            stages=stages,
            latency_ms=_ms(started),
        )
