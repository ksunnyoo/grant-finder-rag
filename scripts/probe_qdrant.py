from qdrant_client import QdrantClient, models

client = QdrantClient(":memory:")
client.create_collection(
    collection_name="t",
    vectors_config={"dense": models.VectorParams(size=4, distance=models.Distance.COSINE)},
    sparse_vectors_config={"sparse": models.SparseVectorParams()},
)
points = [
    (1, [1, 0, 0, 0], {"indices": [1, 2], "values": [1.0, 1.0]}, {"region": ["서울"]}),
    (2, [0, 1, 0, 0], {"indices": [2, 3], "values": [1.0, 1.0]}, {"region": ["전국"]}),
    (3, [0, 0, 1, 0], {"indices": [3, 4], "values": [1.0, 1.0]}, {"region": ["부산"]}),
    (4, [0, 0, 0, 1], {"indices": [1, 4], "values": [1.0, 1.0]}, {"region": ["서울"]}),
]
client.upsert(
    "t",
    [
        models.PointStruct(
            id=i,
            vector={"dense": d, "sparse": models.SparseVector(**s)},
            payload=p,
        )
        for i, d, s, p in points
    ],
)
flt = models.Filter(
    must=[models.FieldCondition(key="region", match=models.MatchAny(any=["서울", "전국"]))]
)
res = client.query_points(
    "t",
    prefetch=[
        models.Prefetch(query=[1, 0, 0, 0], using="dense", limit=4, filter=flt),
        models.Prefetch(
            query=models.SparseVector(indices=[1, 2], values=[1.0, 1.0]),
            using="sparse",
            limit=4,
            filter=flt,
        ),
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF),
    limit=3,
)
for p in res.points:
    print(p.id, round(p.score, 4), p.payload)
