from grant_finder_rag.contracts.models import Candidate, SparseVec
from grant_finder_rag.retrieval.pipeline import Retriever
from grant_finder_rag.storage.qdrant_store import QdrantStore


class FakeEmbedder:
    def embed(self, texts):
        return [[0.1, 0.2] for _ in texts]


class FakeSparse:
    def encode_query(self, text):
        return SparseVec(indices=[1], values=[1.0])


class FakeSearch:
    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = []

    def search(self, dense, sparse, mode, limit, filters=None):
        self.calls.append((mode, limit))
        return self.candidates[:limit]


class FakeReranker:
    def rerank(self, query, texts):
        return [float(i) for i in range(len(texts))]


def _candidates():
    return [
        Candidate(notice_id=str(i), score=1.0 - i * 0.1, payload={"text": f"문서{i}"})
        for i in range(1, 4)
    ]


def test_retriever_reorders_with_reranker():
    search = FakeSearch(_candidates())
    retriever = Retriever(FakeEmbedder(), FakeSparse(), search, FakeReranker())
    results, stages = retriever.retrieve("q", candidates=3, top_k=2, rerank=True)
    assert [c.notice_id for c in results] == ["3", "2"]
    assert results[0].rerank_score == 2.0
    assert search.calls == [("hybrid", 3)]
    assert set(stages) == {"search", "rerank"}


def test_retriever_without_rerank_uses_top_k():
    search = FakeSearch(_candidates())
    retriever = Retriever(FakeEmbedder(), FakeSparse(), search, FakeReranker())
    results, stages = retriever.retrieve("q", candidates=3, top_k=2, rerank=False)
    assert [c.notice_id for c in results] == ["1", "2"]
    assert search.calls == [("hybrid", 2)]
    assert set(stages) == {"search"}


def test_qdrant_store_search_modes(tmp_path):
    store = QdrantStore(path=str(tmp_path / "q"), collection="t")
    store.recreate(dense_size=2)
    store.upsert(
        ids=[1, 2, 3],
        dense=[[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]],
        sparse=[
            SparseVec(indices=[1], values=[1.0]),
            SparseVec(indices=[2], values=[1.0]),
            SparseVec(indices=[1, 2], values=[1.0, 1.0]),
        ],
        payloads=[
            {"notice_id": "1", "text": "a"},
            {"notice_id": "2", "text": "b"},
            {"notice_id": "3", "text": "c"},
        ],
    )
    empty = SparseVec(indices=[], values=[])
    assert store.search([1.0, 0.0], empty, "dense", 3)[0].notice_id == "1"
    assert store.search([1.0, 0.0], empty, "sparse", 3) == []
    sparse_hits = store.search([1.0, 0.0], SparseVec(indices=[2], values=[1.0]), "sparse", 3)
    assert sparse_hits[0].notice_id in {"2", "3"}
    hybrid = store.search([1.0, 0.0], SparseVec(indices=[1], values=[1.0]), "hybrid", 3)
    assert hybrid[0].notice_id == "1"
    store.close()
