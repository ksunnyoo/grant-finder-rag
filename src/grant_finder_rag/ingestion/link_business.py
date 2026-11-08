"""사업 소개를 통합공고에 연결한다 (SDD 4.1절)."""
import json
from pathlib import Path

from grant_finder_rag.contracts.models import Notice
from grant_finder_rag.ingestion.normalize import match_key, safe_text

BUSINESS_FIELDS = [
    ("supt_biz_intrd_info", "소개"),
    ("biz_supt_ctnt", "지원 내용"),
    ("biz_supt_trgt_info", "지원 대상"),
    ("biz_supt_bdgt_info", "지원 예산"),
    ("supt_biz_chrct", "특징"),
]


def _find_items(obj):
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "supt_biz_titl_nm" in obj[0]:
        return obj
    if isinstance(obj, dict):
        for value in obj.values():
            found = _find_items(value)
            if found:
                return found
    return None


def business_intro_text(item: dict) -> str | None:
    lines = []
    for field, label in BUSINESS_FIELDS:
        text = safe_text(item.get(field))
        if text:
            lines.append(f"{label}: {text}")
    return "\n".join(lines) or None


def load_business_intros(raw_dir: Path) -> tuple[dict[str, str], dict]:
    """정규화한 사업명 -> 사업 소개 텍스트. 같은 이름이 또 나오면 먼저 나온 것을 유지한다."""
    items = []
    for path in sorted(raw_dir.glob("page_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        items.extend(_find_items(data) or [])

    intros: dict[str, str] = {}
    stats = {"사업 소개 건수": len(items), "이름 중복": 0, "이름 없음": 0, "소개 내용 없음": 0}
    for item in items:
        key = match_key(item.get("supt_biz_titl_nm"))
        if not key:
            stats["이름 없음"] += 1
            continue
        if key in intros:
            stats["이름 중복"] += 1
            continue
        intro = business_intro_text(item)
        if intro is None:
            stats["소개 내용 없음"] += 1
            continue
        intros[key] = intro
    return intros, stats


def attach_business(notice: Notice, intros: dict[str, str]) -> Notice:
    if not (notice.is_integrated and notice.integrated_name):
        return notice
    intro = intros.get(match_key(notice.integrated_name))
    if intro is None:
        return notice
    return notice.model_copy(update={"business_intro": intro, "linked_business": True})


def main() -> None:
    intros, stats = load_business_intros(Path("data/raw/kstartup/business"))
    in_path = Path("data/clean/notices.jsonl")
    out_path = Path("data/clean/notices_linked.jsonl")
    with in_path.open(encoding="utf-8") as f:
        notices = [Notice(**json.loads(line)) for line in f if line.strip()]
    linked = [attach_business(n, intros) for n in notices]
    with out_path.open("w", encoding="utf-8") as f:
        for n in linked:
            f.write(json.dumps(n.model_dump(mode="json"), ensure_ascii=False) + "\n")

    integrated = sum(1 for n in linked if n.is_integrated)
    success = sum(1 for n in linked if n.linked_business)
    stats.update({
        "공고 건수": len(linked),
        "통합공고": integrated,
        "연결 성공": success,
        "연결 실패(통합공고)": integrated - success,
    })
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
