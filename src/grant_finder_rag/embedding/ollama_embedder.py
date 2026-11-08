"""Ollama bge-m3 임베딩 (dense)."""
import httpx


class OllamaEmbedder:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "bge-m3",
        batch_size: int = 16,
        timeout: float = 300.0,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.batch_size = batch_size
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts[i : i + self.batch_size]},
                timeout=self.timeout,
            )
            response.raise_for_status()
            vectors.extend(response.json()["embeddings"])
        return vectors
