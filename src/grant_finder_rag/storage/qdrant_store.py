"""Qdrant 로컬(파일) 저장소."""
from datetime import date

from qdrant_client import QdrantClient, models

from grant_finder_rag.contracts.models import Candidate, SearchFilters, SparseVec

REGION_EXPANSION = {"전남": ["전남", "전남광주"], "광주": ["광주", "전남광주"]}


def _date_int(value: date) -> int:
    return int(value.strftime("%Y%m%d"))


def _match_or_empty(key: str, condition: models.Condition) -> models.Filter:
    """조건에 맞거나, 공고에 값이 없는(미기재) 경우 통과."""
    return models.Filter(
        should=[
            condition,
            models.IsEmptyCondition(is_empty=models.PayloadField(key=key)),
        ]
    )


def build_filter(f: SearchFilters | None) -> models.Filter | None:
    """SDD 5.2절의 필터 의미를 Qdrant 조건으로 바꾼다."""
    if f is None:
        return None
    must: list[models.Condition] = []
    if f.region:
        regions = {"전국"}
        for region in f.region:
            regions.update(REGION_EXPANSION.get(region, [region]))
        must.append(
            models.FieldCondition(key="region", match=models.MatchAny(any=sorted(regions)))
        )
    if f.target:
        must.append(
            _match_or_empty(
                "target", models.FieldCondition(key="target", match=models.MatchAny(any=f.target))
            )
        )
    if f.biz_age:
        must.append(
            _match_or_empty(
                "biz_age",
                models.FieldCondition(key="biz_age", match=models.MatchAny(any=f.biz_age)),
            )
        )
    if f.age is not None:
        must.append(
            _match_or_empty(
                "ages", models.FieldCondition(key="ages", match=models.MatchValue(value=f.age))
            )
        )
    if f.category:
        must.append(
            models.FieldCondition(key="category", match=models.MatchAny(any=f.category))
        )

    lower = f.end_from
    if not f.include_closed:
        lower = max(lower, f.as_of_date) if lower else f.as_of_date
    if lower or f.end_to:
        must.append(
            models.FieldCondition(
                key="end_date_int",
                range=models.Range(
                    gte=_date_int(lower) if lower else None,
                    lte=_date_int(f.end_to) if f.end_to else None,
                ),
            )
        )
    return models.Filter(must=must) if must else None


class QdrantStore:
    def __init__(self, path: str = "qdrant_data", collection: str = "notices") -> None:
        self.client = QdrantClient(path=path)
        self.collection = collection

    def recreate(self, dense_size: int = 1024) -> None:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config={
                "dense": models.VectorParams(size=dense_size, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={"sparse": models.SparseVectorParams()},
        )

    def upsert(
        self,
        ids: list[int],
        dense: list[list[float]],
        sparse: list[SparseVec],
        payloads: list[dict],
    ) -> None:
        points = [
            models.PointStruct(
                id=point_id,
                vector={
                    "dense": d,
                    "sparse": models.SparseVector(indices=s.indices, values=s.values),
                },
                payload=payload,
            )
            for point_id, d, s, payload in zip(ids, dense, sparse, payloads, strict=True)
        ]
        self.client.upsert(self.collection, points)

    def search(
        self,
        dense: list[float],
        sparse: SparseVec,
        mode: str,
        limit: int,
        filters: SearchFilters | None = None,
        prefetch_limit: int = 50,
    ) -> list[Candidate]:
        """dense / sparse / hybrid(RRF) 검색. 질문에 BM25 단어가 없으면 hybrid는 dense로 대체한다."""
        query_filter = build_filter(filters)
        sparse_query = models.SparseVector(indices=sparse.indices, values=sparse.values)
        if mode == "sparse":
            if not sparse.indices:
                return []
            response = self.client.query_points(
                self.collection,
                query=sparse_query,
                using="sparse",
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
        elif mode == "hybrid" and sparse.indices:
            response = self.client.query_points(
                self.collection,
                prefetch=[
                    models.Prefetch(
                        query=dense, using="dense", filter=query_filter, limit=prefetch_limit
                    ),
                    models.Prefetch(
                        query=sparse_query,
                        using="sparse",
                        filter=query_filter,
                        limit=prefetch_limit,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=limit,
                with_payload=True,
            )
        else:
            response = self.client.query_points(
                self.collection,
                query=dense,
                using="dense",
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
        return [
            Candidate(
                notice_id=str(point.payload["notice_id"]),
                score=point.score,
                payload=point.payload,
            )
            for point in response.points
        ]

    def count(self) -> int:
        return self.client.count(self.collection).count

    def close(self) -> None:
        self.client.close()
