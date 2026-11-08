from datetime import date

from grant_finder_rag.contracts.models import Notice, SparseVec
from grant_finder_rag.embedding.bm25_sparse import Bm25SparseEncoder, tokenize
from grant_finder_rag.ingestion.index import select_for_index, to_payload


def _dot(a: SparseVec, b: SparseVec) -> float:
    weights = dict(zip(b.indices, b.values, strict=True))
    return sum(v * weights.get(i, 0.0) for i, v in zip(a.indices, a.values, strict=True))


def test_tokenize_keeps_nouns():
    tokens = tokenize("서울 창업 지원사업")
    assert "서울" in tokens
    assert "창업" in tokens


def test_bm25_ranks_matching_doc_higher():
    encoder = Bm25SparseEncoder()
    docs = encoder.fit_transform(["서울 창업 지원", "부산 투자 유치", "서울 투자"])
    query = encoder.encode_query("서울 창업")
    assert len(query.indices) == 2
    assert _dot(query, docs[0]) > _dot(query, docs[2]) > 0
    assert _dot(query, docs[1]) == 0


def test_bm25_unknown_query_is_empty():
    encoder = Bm25SparseEncoder()
    encoder.fit_transform(["서울 창업 지원"])
    assert encoder.encode_query("zzzzqq").indices == []


def test_bm25_save_and_load(tmp_path):
    encoder = Bm25SparseEncoder()
    encoder.fit_transform(["서울 창업 지원", "부산 투자 유치"])
    encoder.save(tmp_path / "bm25.json")
    loaded = Bm25SparseEncoder.load(tmp_path / "bm25.json")
    assert loaded.encode_query("서울 창업") == encoder.encode_query("서울 창업")


def test_select_for_index():
    notices = [
        Notice(id="1", title="a", start_date=date(2025, 3, 1)),
        Notice(id="2", title="b", start_date=date(2024, 12, 31)),
        Notice(id="3", title="c", end_date=date(2025, 5, 1)),
        Notice(id="4", title="d"),
    ]
    selected = select_for_index(notices, date(2025, 1, 1))
    assert [n.id for n in selected] == ["1", "3"]


def test_to_payload_ages_and_dates():
    n = Notice(
        id="9",
        title="t",
        age_ranges=[(0, 2), (5, 6)],
        start_date=date(2026, 11, 2),
    )
    payload = to_payload(n, "본문")
    assert payload["ages"] == [0, 1, 2, 5, 6]
    assert payload["start_date_int"] == 20261102
    assert payload["end_date_int"] is None
    assert payload["text"] == "본문"
