"""공고 필드 정제·정규화 함수 (SDD 4.1절)."""
import html
import re
from datetime import date, datetime


def parse_date(value) -> date | None:
    """YYYYMMDD 또는 YYYY-MM-DD(시간 포함 가능)를 date로 바꾼다. 실패하면 None."""
    if value is None:
        return None
    text = str(value).strip()
    for fmt, size in (("%Y%m%d", 8), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(text[:size], fmt).date()
        except ValueError:
            continue
    return None


def clean_text(value) -> str | None:
    """HTML 엔티티 해제, 줄바꿈·공백 정리. 비어 있으면 None."""
    if value is None:
        return None
    text = html.unescape(str(value))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text or None


def mask_contacts(text: str) -> str:
    """전화번호와 이메일을 가린다."""
    text = re.sub(r"0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}", "[전화번호]", text)
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[이메일]", text)
    return text


def normalize_category(value) -> str | None:
    """분야 이름의 'ㆍ'를 '·'로 통일한다."""
    text = clean_text(value)
    if text is None:
        return None
    return text.replace("ㆍ", "·")


def split_tokens(value) -> list[str]:
    """쉼표로 이어진 값을 리스트로 쪼갠다."""
    if value is None:
        return []
    return [t.strip() for t in str(value).split(",") if t.strip()]


def parse_age_ranges(value) -> list[tuple[int, int]]:
    """'만 20세 이상 ~ 만 39세 이하' 같은 값을 (최소, 최대) 목록으로 바꾼다.
    해석하지 못한 항목은 버리며, 아무것도 없으면 빈 목록(연령 미기재)이다."""
    ranges = []
    for token in split_tokens(value):
        numbers = [int(n) for n in re.findall(r"\d+", token)]
        if "미만" in token and len(numbers) == 1:
            ranges.append((0, numbers[0] - 1))
        elif "이상" in token and "이하" in token and len(numbers) == 2:
            ranges.append((numbers[0], numbers[1]))
        elif "이상" in token and len(numbers) == 1:
            ranges.append((numbers[0], 120))
    return ranges
