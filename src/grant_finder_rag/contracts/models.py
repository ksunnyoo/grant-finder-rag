"""정제된 공고 모델 (SDD 3.2절)."""
from datetime import date

from pydantic import BaseModel


class Notice(BaseModel):
    id: str
    title: str
    category: str | None = None
    region: str | None = None
    target: list[str] = []
    biz_age: list[str] = []
    age_ranges: list[tuple[int, int]] = []
    start_date: date | None = None
    end_date: date | None = None
    agency: str | None = None
    content: str | None = None
    target_text: str | None = None
    exclusion_text: str | None = None
    apply_method: str | None = None
    url: str | None = None
    is_integrated: bool = False
    integrated_name: str | None = None
    business_intro: str | None = None
    linked_business: bool = False


class SparseVec(BaseModel):
    """희소 벡터: 단어 번호와 가중치."""

    indices: list[int]
    values: list[float]


class Candidate(BaseModel):
    """검색 결과 1건. payload에는 색인 시 저장한 값이 들어 있다."""

    notice_id: str
    score: float
    rerank_score: float | None = None
    payload: dict = {}


class SearchFilters(BaseModel):
    """검색 조건. 비어 있는 항목은 조건 없음."""

    as_of_date: date
    region: list[str] = []
    target: list[str] = []
    biz_age: list[str] = []
    age: int | None = None
    category: list[str] = []
    include_closed: bool = False
    end_from: date | None = None
    end_to: date | None = None


class LLMResult(BaseModel):
    text: str
    provider: str
