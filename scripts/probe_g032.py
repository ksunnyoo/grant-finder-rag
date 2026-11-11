"""G032·G015가 왜 거절됐는지 확인: 검색 질문(원문/어미 제거)별 상위 공고와 LLM 3회 결과."""
import os
import time
from datetime import date

from dotenv import load_dotenv

load_dotenv(".env")
as_of = date.fromisoformat(os.getenv("AS_OF_DATE", "2026-11-06"))

from grant_finder_rag.bootstrap import build_llm, build_retriever, refuse_threshold
from grant_finder_rag.generation.answer import AnswerGenerator
from grant_finder_rag.retrieval.query_analyzer import analyze_query, search_query

retriever, store = build_retriever(with_reranker=True)
generator = AnswerGenerator(build_llm(None), refuse_threshold=refuse_threshold())

for question in ["다음 달 마감되는 사업 알려줘", "전문분야 창업멘토링 11월 지원 내용이 뭐야?"]:
    filters = analyze_query(question, as_of)
    print(f"\n질문: {question}")
    print(f"  검색용 질문: {search_query(question)}")
    for label, q in [("원문", question), ("검색용", search_query(question))]:
        found, _ = retriever.retrieve(q, filters=filters)
        print(f"  [{label}] 조건 있음={filters.has_conditions()} 최고점={found[0].rerank_score:.3f}")
        for c in found[:5]:
            print(f"     {c.rerank_score:.3f} {c.payload['title'][:40]}")
        for n in range(3):
            try:
                d = generator.generate(question, found, as_of)
                print(f"     LLM {n+1}회: {'거절 ' + str(d.refuse_reason) if d.refused else '답변'}")
            except Exception as e:  # noqa: BLE001
                print(f"     LLM {n+1}회: 오류 {type(e).__name__}")
            time.sleep(2)
