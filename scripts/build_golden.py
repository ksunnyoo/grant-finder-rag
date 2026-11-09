"""골든셋 생성 (PRD 4-1). 정답 라벨은 정제된 공고 데이터에서 계산한다."""

import json
import random
import re
from collections import Counter
from pathlib import Path

AS_OF = 20261106
THIS_END = 20261130
NEXT_START, NEXT_END = 20261201, 20261231
SRC = Path("data/clean/notices_linked.jsonl")
OUT = Path("data/golden/golden.jsonl")

NO_ANSWER = [
    "내일 서울 날씨 어때?",
    "비트코인 지금 시세 알려줘",
    "삼성전자 신입 채용 일정 알려줘",
    "아파트 청약 일정 알려줘",
    "대학생 국가장학금 신청 방법 알려줘",
    "강남 맛집 추천해줘",
    "파이썬 설치하는 방법 알려줘",
    "해외 VC 직접 투자 받는 방법 알려줘",
]


def to_int(v):
    digits = re.sub(r"\D", "", str(v or ""))
    return int(digits[:8]) if len(digits) >= 8 else None


def core_title(title):
    t = re.sub(r"[\[\(][^\]\)]*[\]\)]", " ", title or "")
    t = re.sub(r"20\d\d\s*년?도?", " ", t)
    t = re.sub(r"(참여|참가|입주)?\s*(기업|팀|자)?\s*(추가\s*)?(모집|공고|안내)", " ", t)
    return re.sub(r"\s+", " ", t).strip(" -_·'\"“”‘’")


def matches(n, region=None, pre=False, end_from=None, end_to=None):
    if region and str(n.get("region") or "") not in (region, "전국"):
        return False
    if pre and n.get("biz_age") and "예비" not in str(n["biz_age"]):
        return False
    end = to_int(n.get("end_date"))
    if end_from and (end is None or end < end_from):
        return False
    return not (end_to and (end is None or end > end_to))


def main():
    rows = []
    with SRC.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    open_rows = [r for r in rows if (to_int(r.get("end_date")) or 0) >= AS_OF]
    print(f"전체 {len(rows)}건, 마감 전 {len(open_rows)}건")

    regions = [
        r
        for r, _ in Counter(str(n.get("region") or "") for n in open_rows).most_common()
        if r and r not in ("전국", "전남", "광주")
    ][:8]
    print("사용 지역:", regions)

    items = []

    def add(kind, question, ids, cond, refuse=False):
        items.append(
            {
                "qid": f"G{len(items) + 1:03d}",
                "type": kind,
                "question": question,
                "gold_ids": ids[:300],
                "match_count": len(ids),
                "expect_refuse": refuse,
                "conditions": cond,
            }
        )

    def ids_of(**kw):
        return [str(n["id"]) for n in open_rows if matches(n, **kw)]

    titles = [n.get("title") or "" for n in open_rows]
    pool = []
    for n in open_rows:
        core = core_title(n.get("title"))
        if len(core) >= 8 and sum(core in t for t in titles) == 1:
            pool.append((core, str(n["id"])))
    for core, nid in random.Random(42).sample(pool, min(15, len(pool))):
        add("lookup", f"{core} 지원 내용이 뭐야?", [nid], {})

    for r in regions[:5]:
        for q, kw, cond in [
            (f"{r} 지역 지원사업 알려줘", {"region": r}, {"region": r}),
            (
                f"{r} 예비창업자가 신청할 수 있는 사업 알려줘",
                {"region": r, "pre": True},
                {"region": r, "biz_age": "예비창업자"},
            ),
            (
                f"{r} 사업 중 이번 달 안에 마감되는 것 알려줘",
                {"region": r, "end_from": AS_OF, "end_to": THIS_END},
                {"region": r, "end_to": THIS_END},
            ),
        ]:
            ids = ids_of(**kw)
            if len(ids) >= 3:
                add("filter", q, ids, cond)

    add("date", "이번 달 마감되는 사업 알려줘", ids_of(end_from=AS_OF, end_to=THIS_END), {"end_to": THIS_END})
    add("date", "다음 달 마감되는 사업 알려줘", ids_of(end_from=NEXT_START, end_to=NEXT_END), {"end_from": NEXT_START, "end_to": NEXT_END})
    for i, r in enumerate(regions[2:], start=2):
        if sum(1 for x in items if x["type"] == "date") >= 8:
            break
        if i % 2:
            q, kw = f"{r} 다음 달 마감 사업 알려줘", {"region": r, "end_from": NEXT_START, "end_to": NEXT_END}
        else:
            q, kw = f"{r} 이번 달 마감 사업 알려줘", {"region": r, "end_from": AS_OF, "end_to": THIS_END}
        ids = ids_of(**kw)
        if ids:
            add("date", q, ids, {"region": r, "end_from": kw["end_from"], "end_to": kw["end_to"]})

    for r in regions:
        if sum(1 for x in items if x["type"] == "multi") >= 4:
            break
        kw = {"region": r, "pre": True, "end_from": NEXT_START, "end_to": NEXT_END}
        ids = ids_of(**kw)
        if ids:
            add("multi", f"{r} 예비창업자가 신청할 수 있고 다음 달에 마감되는 사업 알려줘", ids, {"region": r, "biz_age": "예비창업자", "end_from": NEXT_START, "end_to": NEXT_END})

    for q in NO_ANSWER:
        add("no_answer", q, [], {}, refuse=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print("유형별:", dict(Counter(i["type"] for i in items)), "합계", len(items))
    for it in items:
        print(it["qid"], it["type"], it["match_count"], it["question"])


if __name__ == "__main__":
    main()
