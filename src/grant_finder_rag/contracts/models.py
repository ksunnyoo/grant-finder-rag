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
