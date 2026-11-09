import os
from datetime import date

from dotenv import load_dotenv

from grant_finder_rag.cli import build_retriever
from grant_finder_rag.retrieval.query_analyzer import analyze_query

load_dotenv()
AS_OF = date.fromisoformat(os.getenv("AS_OF_DATE", "2026-11-06"))

ANSWERABLE = [
    "아산 투자유치 프로그램 신청 방법이 뭐야?",
    "스타트업 IR 피칭 데모데이 참가 기업 모집",
    "법인 설립 세무 회계 컨설팅 지원",
    "제조 스타트업 시제품 제작 지원",
    "청년 푸드테크 창업자 입주 공간",
    "AI 스타트업 클라우드 크레딧 지원",
    "기후테크 기업 멘토링",
    "대학생 창업동아리 지원",
]
UNANSWERABLE = [
    "해외 VC 직접 투자 받는 방법 알려줘",
    "내일 서울 날씨 어때?",
    "비트코인 시세 알려줘",
    "주택 담보대출 금리 비교해줘",
    "국민연금 수령 나이는 몇 살이야?",
    "맛있는 김치찌개 레시피 알려줘",
    "미국 법인 설립 절차를 단계별로 설명해줘",
    "대학원 입학 전형 일정 알려줘",
]

retriever, store = build_retriever(with_reranker=True)
rows = []
try:
    for label, questions in (("답변가능", ANSWERABLE), ("답변불가", UNANSWERABLE)):
        for q in questions:
            filters = analyze_query(q, AS_OF)
            found, _ = retriever.retrieve(q, filters=filters)
            top = max((c.rerank_score for c in found if c.rerank_score is not None), default=None)
            title = found[0].payload["title"][:28] if found else "-"
            rows.append((label, top, filters.has_conditions(), q, title))
            top_text = "-" if top is None else f"{top:.3f}"
            print(f"{label} 최고점={top_text} 조건={filters.has_conditions()} | {q} -> {title}")
finally:
    store.close()

scores_a = [r[1] for r in rows if r[0] == "답변가능" and r[1] is not None]
scores_u = [r[1] for r in rows if r[0] == "답변불가" and r[1] is not None]
print("\n답변가능 최저점:", round(min(scores_a), 3), "/ 답변불가 최고점:", round(max(scores_u), 3))
