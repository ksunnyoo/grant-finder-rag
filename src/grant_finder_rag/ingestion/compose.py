"""공고 1건을 검색용 텍스트 1개로 구성한다 (SDD 4.2절)."""
import json
from pathlib import Path

from grant_finder_rag.contracts.models import Notice

MAX_CONTENT_CHARS = 2000
MAX_AGE = 120


def age_text(ranges: list[tuple[int, int]]) -> str | None:
    """연령 범위를 문장으로 바꾼다. 범위가 없거나 제한이 없으면 None."""
    if not ranges:
        return None
    merged: list[tuple[int, int]] = []
    for lo, hi in sorted(ranges):
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    if len(merged) == 1 and merged[0][0] == 0 and merged[0][1] >= MAX_AGE:
        return None
    parts = []
    for lo, hi in merged:
        if lo == 0:
            parts.append(f"만 {hi + 1}세 미만")
        elif hi >= MAX_AGE:
            parts.append(f"만 {lo}세 이상")
        else:
            parts.append(f"만 {lo}~{hi}세")
    return ", ".join(parts)


def compose_search_text(n: Notice) -> str:
    lines = [f"[제목] {n.title}"]

    meta = []
    if n.category:
        meta.append(f"[분야] {n.category}")
    if n.region:
        meta.append(f"[지역] {n.region}")
    if n.agency:
        meta.append(f"[기관] {n.agency}")
    if meta:
        lines.append("  ".join(meta))

    target = ", ".join(n.target)
    if n.target_text:
        target = f"{target} / {n.target_text}" if target else n.target_text
    if target:
        lines.append(f"[대상] {target}")

    if n.biz_age:
        lines.append(f"[업력] {', '.join(n.biz_age)}")
    age = age_text(n.age_ranges)
    if age:
        lines.append(f"[연령] {age}")

    if n.start_date and n.end_date:
        lines.append(f"[접수] {n.start_date.isoformat()} ~ {n.end_date.isoformat()}")
    elif n.end_date:
        lines.append(f"[접수] ~ {n.end_date.isoformat()} 마감")
    elif n.start_date:
        lines.append(f"[접수] {n.start_date.isoformat()} 시작")

    if n.exclusion_text:
        lines.append(f"[제외 대상] {n.exclusion_text}")
    if n.apply_method:
        lines.append(f"[신청 방법] {n.apply_method}")
    if n.content:
        lines.append(f"[내용] {n.content[:MAX_CONTENT_CHARS]}")
    if n.business_intro:
        lines.append(f"[사업 소개] {n.business_intro}")
    return "\n".join(lines)


def main() -> None:
    in_path = Path("data/clean/notices_linked.jsonl")
    out_path = Path("data/clean/search_docs.jsonl")
    with in_path.open(encoding="utf-8") as f:
        notices = [Notice(**json.loads(line)) for line in f if line.strip()]
    lengths = []
    with out_path.open("w", encoding="utf-8") as f:
        for n in notices:
            text = compose_search_text(n)
            lengths.append(len(text))
            f.write(json.dumps({"notice_id": n.id, "text": text}, ensure_ascii=False) + "\n")

    lengths.sort()
    print("문서 수:", len(lengths))
    print("평균 글자 수:", round(sum(lengths) / len(lengths)))
    print("95번째 백분위:", lengths[int(len(lengths) * 0.95)])
    print("최대 글자 수:", lengths[-1])
    print("100자 미만 문서:", sum(1 for x in lengths if x < 100))


if __name__ == "__main__":
    main()
