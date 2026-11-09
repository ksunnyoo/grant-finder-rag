"""어려운 골든셋 생성 (PRD 4-2). 제목을 쓰지 않고 메타 정보와 본문 희귀 단어로 묻는다."""

import json
import random
import re
from collections import Counter
from pathlib import Path

AS_OF = 20261106
SRC = Path("data/clean/notices_linked.jsonl")
OUT = Path("data/golden/golden_hard.jsonl")
WORD = re.compile(r"[가-힣]{4,}")


def to_int(v):
    digits = re.sub(r"\D", "", str(v or ""))
    return int(digits[:8]) if len(digits) >= 8 else None


def main():
    rows = []
    with SRC.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    open_rows = [r for r in rows if (to_int(r.get("end_date")) or 0) >= AS_OF]
    rng = random.Random(7)
    items = []

    def add(subtype, question, nid):
        items.append(
            {
                "qid": f"H{len(items) + 1:03d}",
                "type": "lookup",
                "subtype": subtype,
                "question": question,
                "gold_ids": [str(nid)],
                "match_count": 1,
                "expect_refuse": False,
                "conditions": {},
            }
        )

    pairs = Counter((r.get("agency"), r.get("category")) for r in open_rows)
    meta = [
        r
        for r in open_rows
        if r.get("agency") and r.get("category") and pairs[(r["agency"], r["category"])] == 1
    ]
    used = set()
    for r in rng.sample(meta, min(8, len(meta))):
        used.add(r["id"])
        add("meta", f"{r['agency']}에서 진행하는 '{r['category']}' 분야 지원사업 알려줘", r["id"])

    words = [set(WORD.findall(r.get("content") or "")) for r in open_rows]
    df = Counter(w for ws in words for w in ws)
    pool = []
    for r, ws in zip(open_rows, words, strict=True):
        title = r.get("title") or ""
        rare = sorted(w for w in ws if df[w] == 1 and w not in title)
        if len(rare) >= 2 and r["id"] not in used:
            pool.append((r["id"], rare))
    for nid, rare in rng.sample(pool, min(7, len(pool))):
        w1, w2 = rng.sample(rare, 2)
        add("keyword", f"{w1}, {w2} 관련 공고 알려줘", nid)

    with OUT.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print("유형별:", dict(Counter(i["subtype"] for i in items)), "합계", len(items))
    for it in items:
        print(it["qid"], it["subtype"], it["question"])


if __name__ == "__main__":
    main()
