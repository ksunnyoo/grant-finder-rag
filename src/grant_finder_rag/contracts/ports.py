"""외부 서비스 접점(Port) 정의. 구현은 embedding, storage 등에 둔다."""
from typing import Protocol

from grant_finder_rag.contracts.models import Candidate, SparseVec


class EmbedderPort(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SparseEncoderPort(Protocol):
    def encode_documents(self, texts: list[str]) -> list[SparseVec]: ...

    def encode_query(self, text: str) -> SparseVec: ...


class SearchPort(Protocol):
    def search(
        self, dense: list[float], sparse: SparseVec, mode: str, limit: int
    ) -> list[Candidate]:
        """mode: 'dense' | 'sparse' | 'hybrid'"""
        ...


class RerankerPort(Protocol):
    def rerank(self, query: str, texts: list[str]) -> list[float]: ...
