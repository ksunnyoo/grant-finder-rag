"""Qdrant 로컬(파일) 저장소."""
from qdrant_client import QdrantClient, models

from grant_finder_rag.contracts.models import Candidate, SparseVec


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
        prefetch_limit: int = 50,
    ) -> list[Candidate]:
        """dense / sparse / hybrid(RRF) 검색. 질문에 BM25 단어가 없으면 hybrid는 dense로 대체한다."""
        sparse_query = models.SparseVector(indices=sparse.indices, values=sparse.values)
        if mode == "sparse":
            if not sparse.indices:
                return []
            response = self.client.query_points(
                self.collection, query=sparse_query, using="sparse", limit=limit, with_payload=True
            )
        elif mode == "hybrid" and sparse.indices:
            response = self.client.query_points(
                self.collection,
                prefetch=[
                    models.Prefetch(query=dense, using="dense", limit=prefetch_limit),
                    models.Prefetch(query=sparse_query, using="sparse", limit=prefetch_limit),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=limit,
                with_payload=True,
            )
        else:
            response = self.client.query_points(
                self.collection, query=dense, using="dense", limit=limit, with_payload=True
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
