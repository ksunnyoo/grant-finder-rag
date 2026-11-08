from datetime import date

from grant_finder_rag.contracts.models import Notice
from grant_finder_rag.ingestion.compose import age_text, compose_search_text
from grant_finder_rag.ingestion.link_business import attach_business
from grant_finder_rag.ingestion.normalize import match_key


def test_attach_business_linked():
    n = Notice(id="1", title="t", is_integrated=True, integrated_name="⌈서울⌋ 창업 사업")
    intros = {match_key("서울 창업사업"): "소개: x"}
    m = attach_business(n, intros)
    assert m.linked_business is True
    assert m.business_intro == "소개: x"


def test_attach_business_not_linked():
    n = Notice(id="1", title="t", is_integrated=False, integrated_name="서울 창업사업")
    m = attach_business(n, {match_key("서울 창업사업"): "소개: x"})
    assert m.linked_business is False
    assert m.business_intro is None


def test_age_text():
    assert age_text([]) is None
    assert age_text([(0, 19), (20, 39), (40, 120)]) is None
    assert age_text([(20, 39)]) == "만 20~39세"
    assert age_text([(0, 19), (40, 120)]) == "만 20세 미만, 만 40세 이상"
    assert age_text([(20, 39), (40, 120)]) == "만 20세 이상"
    assert age_text([(0, 19), (20, 39)]) == "만 40세 미만"


def test_compose_search_text():
    n = Notice(
        id="1",
        title="창업 지원",
        category="사업화",
        region="서울",
        target=["일반인"],
        age_ranges=[(0, 19), (20, 39), (40, 120)],
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 30),
        business_intro="소개: x",
    )
    text = compose_search_text(n)
    assert "[제목] 창업 지원" in text
    assert "[분야] 사업화  [지역] 서울" in text
    assert "[접수] 2026-11-01 ~ 2026-11-30" in text
    assert "[연령]" not in text
    assert "[사업 소개] 소개: x" in text
    assert "[내용]" not in text
