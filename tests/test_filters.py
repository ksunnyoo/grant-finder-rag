from datetime import date

from grant_finder_rag.contracts.models import SearchFilters, SparseVec
from grant_finder_rag.retrieval.query_analyzer import analyze_query, merge_filters
from grant_finder_rag.storage.qdrant_store import QdrantStore

AS_OF = date(2026, 11, 6)


def test_analyze_region_and_pre_founder():
    f = analyze_query("서울 예비창업자가 신청할 수 있는 사업 알려줘", AS_OF)
    assert f.region == ["서울"]
    assert f.biz_age == ["예비창업자"]
    assert f.include_closed is False


def test_analyze_age_and_years():
    f = analyze_query("만 35세, 창업 2년차가 신청 가능한 사업은?", AS_OF)
    assert f.age == 35
    assert f.biz_age == ["2년미만"]
    assert analyze_query("창업 4년차", AS_OF).biz_age == ["5년미만"]
    assert analyze_query("업력 3년 미만", AS_OF).biz_age == ["3년미만"]


def test_analyze_month_and_category():
    f = analyze_query("이번 달 마감인 창업교육 공고는?", AS_OF)
    assert f.category == []
    f = analyze_query("이번 달 마감인 창업교육 공고는?", AS_OF, extract_category=True)
    assert f.category == ["창업교육"]
    assert f.end_from == date(2026, 11, 1)
    assert f.end_to == date(2026, 11, 30)
    g = analyze_query("다음 달 마감 사업", date(2026, 12, 10))
    assert g.end_from == date(2027, 1, 1)
    assert g.end_to == date(2027, 1, 31)


def test_analyze_target_and_closed():
    f = analyze_query("대구 대학생 대상, 마감된 것도 보여줘", AS_OF)
    assert f.region == ["대구"]
    assert f.target == ["대학생"]
    assert f.include_closed is True


def test_analyze_no_condition():
    f = analyze_query("해외 VC 직접 투자 받는 방법 알려줘", AS_OF)
    assert f.region == [] and f.target == [] and f.biz_age == []
    assert f.age is None and f.category == []


def test_merge_explicit_wins():
    extracted = analyze_query("서울 예비창업자", AS_OF)
    explicit = SearchFilters(as_of_date=AS_OF, region=["부산"])
    merged = merge_filters(explicit, extracted)
    assert merged.region == ["부산"]
    assert merged.biz_age == ["예비창업자"]


def _payload(i, region, target, biz_age, ages, category, end):
    return {
        "notice_id": str(i),
        "region": region,
        "target": target,
        "biz_age": biz_age,
        "ages": ages,
        "category": category,
        "end_date_int": end,
        "text": "t",
    }


def _store(tmp_path):
    store = QdrantStore(path=str(tmp_path / "q"), collection="t")
    store.recreate(dense_size=2)
    store.upsert(
        ids=[1, 2, 3, 4, 5],
        dense=[[1.0, 0.0], [0.9, 0.1], [0.8, 0.2], [0.7, 0.3], [0.6, 0.4]],
        sparse=[SparseVec(indices=[1], values=[1.0])] * 5,
        payloads=[
            _payload(1, "서울", ["대학생"], ["예비창업자"], [25, 26], "사업화", 20261201),
            _payload(2, "부산", ["대학생"], ["3년미만"], [40], "사업화", 20261201),
            _payload(3, "전국", [], [], [], "사업화", 20261201),
            _payload(4, "서울", ["일반기업"], ["예비창업자"], [30], "창업교육", 20250101),
            _payload(5, "서울", ["일반기업"], ["예비창업자"], [30], "창업교육", None),
        ],
    )
    return store


def _ids(store, filters, mode="dense"):
    hits = store.search([1.0, 0.0], SparseVec(indices=[1], values=[1.0]), mode, 10, filters)
    return {h.notice_id for h in hits}


def test_filter_region_includes_nationwide_and_excludes_closed(tmp_path):
    store = _store(tmp_path)
    assert _ids(store, SearchFilters(as_of_date=AS_OF, region=["서울"])) == {"1", "3"}
    closed = SearchFilters(as_of_date=AS_OF, region=["서울"], include_closed=True)
    assert _ids(store, closed) == {"1", "3", "4", "5"}
    store.close()


def test_filter_unknown_values_pass(tmp_path):
    store = _store(tmp_path)
    assert _ids(store, SearchFilters(as_of_date=AS_OF, target=["대학생"])) == {"1", "2", "3"}
    assert _ids(store, SearchFilters(as_of_date=AS_OF, age=25)) == {"1", "3"}
    assert _ids(store, SearchFilters(as_of_date=AS_OF, biz_age=["예비창업자"])) == {"1", "3"}
    store.close()


def test_filter_category_and_end_range(tmp_path):
    store = _store(tmp_path)
    assert _ids(store, SearchFilters(as_of_date=AS_OF, category=["사업화"])) == {"1", "2", "3"}
    in_range = SearchFilters(
        as_of_date=AS_OF, end_from=date(2026, 12, 1), end_to=date(2026, 12, 31)
    )
    assert _ids(store, in_range) == {"1", "2", "3"}
    store.close()


def test_filter_applies_to_hybrid(tmp_path):
    store = _store(tmp_path)
    assert _ids(store, SearchFilters(as_of_date=AS_OF, region=["부산"]), "hybrid") == {"2", "3"}
    store.close()
