from datetime import date

from grant_finder_rag.contracts.models import Candidate, LLMResult
from grant_finder_rag.generation.answer import AnswerGenerator, extract_citations
from grant_finder_rag.service import AskService, make_snippet

AS_OF = date(2026, 11, 6)


class SeqLLM:
    def __init__(self, texts):
        self.texts = list(texts)
        self.calls = 0

    def generate(self, system, prompt):
        text = self.texts[min(self.calls, len(self.texts) - 1)]
        self.calls += 1
        return LLMResult(text=text, provider="fake")


def _cand(i, rerank=None):
    return Candidate(
        notice_id=str(i),
        score=0.5,
        rerank_score=rerank,
        payload={
            "notice_id": str(i),
            "title": f"공고{i}",
            "agency": "기관",
            "region": "서울",
            "category": "사업화",
            "target": [],
            "biz_age": [],
            "ages": [],
            "end_date": "2026-11-10",
            "url": f"https://example.com/{i}",
            "text": f"[제목] 공고{i}\n[내용] 본문입니다\n[사업 소개] 소개",
        },
    )


class FakeRetriever:
    def __init__(self, candidates):
        self.candidates = candidates
        self.filters = None

    def retrieve(self, query, mode="hybrid", candidates=20, top_k=5, rerank=True, filters=None):
        self.filters = filters
        return self.candidates, {"search": 1, "rerank": 2}


def test_extract_citations_removes_invalid():
    text, cited = extract_citations("가 [1] 나 [999] 다 [공고 2] 라 [1]", {"1", "2"})
    assert cited == ["1", "2"]
    assert "999" not in text
    assert "[공고" not in text


def test_generate_with_valid_citation():
    generator = AnswerGenerator(SeqLLM(["모집합니다 [1]."]))
    draft = generator.generate("q", [_cand(1)], AS_OF)
    assert draft.refused is False
    assert draft.cited_ids == ["1"]
    assert draft.provider == "fake"


def test_generate_llm_says_no_evidence():
    generator = AnswerGenerator(SeqLLM(["[근거 없음]"]))
    draft = generator.generate("q", [_cand(1)], AS_OF)
    assert draft.refused is True
    assert draft.refuse_reason == "LOW_RELEVANCE"


def test_generate_retries_once_for_missing_citation():
    llm = SeqLLM(["인용 없는 답", "모집합니다 [1]"])
    draft = AnswerGenerator(llm).generate("q", [_cand(1)], AS_OF)
    assert draft.refused is False
    assert llm.calls == 2


def test_generate_no_citation_after_retry():
    llm = SeqLLM(["인용 없음", "[999] 없는 번호"])
    draft = AnswerGenerator(llm).generate("q", [_cand(1)], AS_OF)
    assert draft.refused is True
    assert draft.refuse_reason == "NO_CITATION"
    assert llm.calls == 2


def test_screen():
    generator = AnswerGenerator(SeqLLM(["x"]), refuse_threshold=0.1)
    assert generator.screen([], False) == "NO_MATCH"
    low = [_cand(1, rerank=0.01)]
    assert generator.screen(low, False) == "LOW_RELEVANCE"
    assert generator.screen(low, True) is None
    assert generator.screen([_cand(1, rerank=0.5)], False) is None
    assert AnswerGenerator(SeqLLM(["x"])).screen(low, False) is None


def test_make_snippet():
    text = "[제목] t\n[내용] 첫째 줄\n둘째 줄\n[사업 소개] 소개"
    assert make_snippet(text) == "첫째 줄 둘째 줄"


def test_service_answer_with_sources_and_flags():
    retriever = FakeRetriever([_cand(1), _cand(2)])
    generator = AnswerGenerator(SeqLLM(["대학생 대상 모집 [2]."]))
    result = AskService(retriever, generator, AS_OF).ask("서울 대학생 지원사업")
    assert result.refused is False
    assert [s.id for s in result.sources] == ["2"]
    source = result.sources[0]
    assert source.d_day == 4
    assert source.snippet == "본문입니다"
    assert "대상 미기재" in source.flags
    assert result.applied_filters["region"] == ["서울"]
    assert set(result.stages) == {"analyze", "search", "rerank", "generate"}
    assert retriever.filters.target == ["대학생"]


def test_service_refuses_when_no_candidates():
    result = AskService(FakeRetriever([]), AnswerGenerator(SeqLLM(["x"])), AS_OF).ask("질문")
    assert result.refused is True
    assert result.refuse_reason == "NO_MATCH"
    assert result.sources == []
