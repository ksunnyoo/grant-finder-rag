"""Qdrant 로컬(파일) 저장소."""
from qdrant_client import QdrantClient, models

from grant_finder_rag.contracts.models import SparseVec


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

    def count(self) -> int:
        return self.client.count(self.collection).count

    def close(self) -> None:
        self.client.close()
