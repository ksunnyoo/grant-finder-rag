"""외부 서비스 접점(Port) 정의. 구현은 embedding, storage 등에 둔다."""
from typing import Protocol

from grant_finder_rag.contracts.models import Candidate, SearchFilters, SparseVec


class EmbedderPort(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SparseEncoderPort(Protocol):
    def encode_documents(self, texts: list[str]) -> list[SparseVec]: ...

    def encode_query(self, text: str) -> SparseVec: ...


class SearchPort(Protocol):
    def search(
        self,
        dense: list[float],
        sparse: SparseVec,
        mode: str,
        limit: int,
        filters: SearchFilters | None = None,
    ) -> list[Candidate]:
        """mode: 'dense' | 'sparse' | 'hybrid'"""
        ...


class RerankerPort(Protocol):
    def rerank(self, query: str, texts: list[str]) -> list[float]: ...


class LLMPort(Protocol):
    name: str

    def generate(self, system: str, prompt: str) -> str: ...


class RetrieverPort(Protocol):
    def retrieve(
        self,
        query: str,
        mode: str = "hybrid",
        candidates: int = 20,
        top_k: int = 5,
        rerank: bool = True,
        filters: SearchFilters | None = None,
    ) -> tuple[list[Candidate], dict[str, int]]: ...
