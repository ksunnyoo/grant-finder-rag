"""hybrid 효과 시험용 골든셋 (PRD 4-2). 형태소 분석 후에도 희귀한 고유명사/영문 단어로 묻는다."""

import json
import random
import re
from collections import Counter
from pathlib import Path

from kiwipiepy import Kiwi

AS_OF = 20261106
SRC = Path("data/clean/notices_linked.jsonl")
OUT = Path("data/golden/golden_rare.jsonl")
KEEP_TAGS = {"NNP", "SL"}


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
    kiwi = Kiwi()
    fulls = {r["id"]: f"{r.get('title') or ''} {(r.get('content') or '')[:2000]}" for r in open_rows}
    doc_tokens = {}
    for r in open_rows:
        body = (r.get("content") or "")[:2000]
        doc_tokens[r["id"]] = {
            t.form for t in kiwi.tokenize(body) if t.tag in KEEP_TAGS and len(t.form) >= 3
        }
    df = Counter(t for ts in doc_tokens.values() for t in ts)
    pool = []
    for r in open_rows:
        title = r.get("title") or ""
        rare = sorted(
            t
            for t in doc_tokens[r["id"]]
            if df[t] == 1 and t not in title and sum(t in full for full in fulls.values()) == 1
        )
        if len(rare) >= 2:
            pool.append((r["id"], rare))
    print(f"마감 전 {len(open_rows)}건 중 희귀 단어 2개 이상인 공고 {len(pool)}건")
    rng = random.Random(11)
    items = []
    for nid, rare in rng.sample(pool, min(15, len(pool))):
        t1, t2 = rng.sample(rare, 2)
        items.append(
            {
                "qid": f"R{len(items) + 1:03d}",
                "type": "lookup",
                "subtype": "rare",
                "question": f"{t1}, {t2} 관련 공고 알려줘",
                "gold_ids": [str(nid)],
                "match_count": 1,
                "expect_refuse": False,
                "conditions": {},
            }
        )
    with OUT.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    for it in items:
        print(it["qid"], it["question"])


if __name__ == "__main__":
    main()
