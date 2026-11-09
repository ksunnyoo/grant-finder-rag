from datetime import date

from grant_finder_rag.retrieval.query_analyzer import analyze_query

AS_OF = date(2026, 11, 6)


def test_category_not_extracted_by_default():
    f = analyze_query("글로벌 진출 초기 챙겨야 할 GEO 전략 지원 내용이 뭐야?", AS_OF)
    assert not f.category


def test_category_extracted_when_enabled():
    f = analyze_query("글로벌 진출 지원 알려줘", AS_OF, extract_category=True)
    assert "글로벌" in f.category
