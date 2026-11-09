"""질문에서 검색 조건을 규칙으로 추출한다 (SDD 5.1~5.2절)."""
import re
from datetime import date, timedelta

from grant_finder_rag.contracts.models import SearchFilters

REGIONS = {
    "서울": ["서울"],
    "경기": ["경기"],
    "인천": ["인천"],
    "부산": ["부산"],
    "대구": ["대구"],
    "대전": ["대전"],
    "광주": ["광주"],
    "울산": ["울산"],
    "세종": ["세종"],
    "강원": ["강원"],
    "충북": ["충북", "충청북도"],
    "충남": ["충남", "충청남도"],
    "전북": ["전북", "전라북도"],
    "전남": ["전남", "전라남도"],
    "경북": ["경북", "경상북도"],
    "경남": ["경남", "경상남도"],
    "제주": ["제주"],
}
TARGETS = {
    "청소년": ["청소년"],
    "대학생": ["대학생"],
    "일반인": ["일반인"],
    "연구기관": ["연구기관"],
    "일반기업": ["일반기업"],
    "1인 창조기업": ["1인 창조기업", "1인창조기업"],
}
CATEGORIES = {
    "창업교육": ["창업교육"],
    "멘토링·컨설팅·교육": ["멘토링", "컨설팅"],
    "사업화": ["사업화"],
    "판로·해외진출": ["판로", "해외진출"],
    "글로벌": ["글로벌"],
    "기술개발(R&D)": ["R&D", "기술개발"],
    "정책자금": ["정책자금"],
    "융자·보증": ["융자", "보증"],
    "인력": ["인력"],
    "행사·네트워크": ["행사", "네트워킹"],
    "시설·공간·보육": ["입주", "보육", "공간"],
}
BIZ_AGE_BUCKETS = [1, 2, 3, 5, 7, 10]
CLOSED_WORDS = ["마감 포함", "마감된", "지난 공고", "종료된"]


def _find(question: str, table: dict[str, list[str]]) -> list[str]:
    return [name for name, words in table.items() if any(w in question for w in words)]


def _biz_age(question: str) -> list[str]:
    result = []
    if re.search(r"예비\s*창업", question):
        result.append("예비창업자")
    match = re.search(r"(\d+)\s*년\s*(?:미만|이내)", question)
    if match and int(match.group(1)) in BIZ_AGE_BUCKETS:
        result.append(f"{int(match.group(1))}년미만")
        return result
    match = re.search(r"(\d+)\s*년\s*차", question)
    if match:
        bucket = next((b for b in BIZ_AGE_BUCKETS if b >= int(match.group(1))), None)
        if bucket:
            result.append(f"{bucket}년미만")
    return result


def _age(question: str) -> int | None:
    match = re.search(r"만\s*(\d{1,2})\s*세", question) or re.search(
        r"(\d{2})\s*(?:세|살)", question
    )
    return int(match.group(1)) if match else None


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    first = date(year, month, 1)
    next_first = date(year + month // 12, month % 12 + 1, 1)
    return first, next_first - timedelta(days=1)


def _end_range(question: str, as_of: date) -> tuple[date | None, date | None]:
    if "이번 달" in question or "이번달" in question:
        return _month_bounds(as_of.year, as_of.month)
    if "다음 달" in question or "다음달" in question:
        next_first = _month_bounds(as_of.year, as_of.month)[1] + timedelta(days=1)
        return _month_bounds(next_first.year, next_first.month)
    return None, None


def analyze_query(
    question: str, as_of_date: date, extract_category: bool = False
) -> SearchFilters:
    end_from, end_to = _end_range(question, as_of_date)
    return SearchFilters(
        as_of_date=as_of_date,
        region=_find(question, REGIONS),
        target=_find(question, TARGETS),
        biz_age=_biz_age(question),
        age=_age(question),
        category=_find(question, CATEGORIES) if extract_category else [],
        include_closed=any(w in question for w in CLOSED_WORDS),
        end_from=end_from,
        end_to=end_to,
    )


def merge_filters(explicit: SearchFilters | None, extracted: SearchFilters) -> SearchFilters:
    """화면에서 지정한 조건이 질문에서 추출한 조건보다 우선한다."""
    if explicit is None:
        return extracted
    return SearchFilters(
        as_of_date=explicit.as_of_date,
        region=explicit.region or extracted.region,
        target=explicit.target or extracted.target,
        biz_age=explicit.biz_age or extracted.biz_age,
        age=explicit.age if explicit.age is not None else extracted.age,
        category=explicit.category or extracted.category,
        include_closed=explicit.include_closed or extracted.include_closed,
        end_from=explicit.end_from or extracted.end_from,
        end_to=explicit.end_to or extracted.end_to,
    )
