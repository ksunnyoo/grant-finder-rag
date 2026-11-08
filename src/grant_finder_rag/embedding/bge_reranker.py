"""bge-reranker-v2-m3 리랭커 (sentence-transformers)."""


class BgeReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", max_length: int = 512) -> None:
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name, max_length=max_length)

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        """(질문, 문서) 쌍마다 0~1 점수를 반환한다."""
        scores = self.model.predict([(query, text) for text in texts])
        return [float(score) for score in scores]
