"""평가 실행기 (PRD 4-1, 4-2). 골든셋으로 검색 구성 비교와 거절/인용 지표를 측정한다."""

import argparse
import json
import os
import statistics
import time
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from grant_finder_rag.cli import build_llm, build_retriever
from grant_finder_rag.generation.answer import AnswerGenerator
from grant_finder_rag.retrieval.query_analyzer import analyze_query
from grant_finder_rag.service import AskService

GOLDEN = Path("data/golden/golden.jsonl")
OUT_DIR = Path("data/eval")
CONFIGS = {
    "C0 dense": {"mode": "dense", "rerank": False, "use_filter": False},
    "C1 +hybrid": {"mode": "hybrid", "rerank": False, "use_filter": False},
    "C2 +filter": {"mode": "hybrid", "rerank": False, "use_filter": True},
    "C3 +rerank": {"mode": "hybrid", "rerank": True, "use_filter": True},
    "F-dense (dense+필터)": {"mode": "dense", "rerank": False, "use_filter": True},
    "F-sparse (sparse+필터)": {"mode": "sparse", "rerank": False, "use_filter": True},
}


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def load_golden(path):
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def eval_retrieval(retriever, items, as_of, k):
    report = {}
    for name, cfg in CONFIGS.items():
        hits, rrs, times = [], [], []
        prec = {"filter": [], "date": [], "multi": []}
        empty = 0
        misses = []
        for it in items:
            if it["type"] == "no_answer":
                continue
            filters = analyze_query(it["question"], as_of) if cfg["use_filter"] else None
            started = time.perf_counter()
            results, _ = retriever.retrieve(
                it["question"], mode=cfg["mode"], top_k=k, rerank=cfg["rerank"], filters=filters
            )
            times.append((time.perf_counter() - started) * 1000)
            ids = [str(c.notice_id) for c in results[:k]]
            gold = set(it["gold_ids"])
            if it["type"] == "lookup":
                rank = next((i for i, x in enumerate(ids, 1) if x in gold), None)
                hits.append(1 if rank else 0)
                rrs.append(1 / rank if rank else 0.0)
                if not rank:
                    misses.append(it["qid"])
            else:
                if not ids:
                    empty += 1
                prec[it["type"]].append(sum(x in gold for x in ids) / len(ids) if ids else 0.0)
        report[name] = {
            "hit_at_k": mean(hits),
            "mrr": mean(rrs),
            "precision": {t: mean(v) for t, v in prec.items()},
            "empty": empty,
            "median_ms": statistics.median(times) if times else 0,
            "lookup_misses": misses,
        }
        print(f"  {name} 완료")
    return report


def eval_e2e(retriever, items, as_of, providers, limit, pause):
    threshold = float(os.getenv("REFUSE_THRESHOLD", "0.05"))
    generator = AnswerGenerator(build_llm(providers), refuse_threshold=threshold)
    service = AskService(retriever, generator, as_of)
    no_answer = [i for i in items if i["type"] == "no_answer"]
    lookup = [i for i in items if i["type"] == "lookup"]
    others = [i for i in items if i["type"] in ("filter", "date", "multi")]
    step = max(1, len(others) // limit)
    picked = no_answer + lookup + others[::step][:limit]
    rows = []
    for n, it in enumerate(picked, 1):
        row = {"qid": it["qid"], "type": it["type"], "question": it["question"]}
        try:
            r = service.ask(it["question"])
            ids = [s.id for s in r.sources]
            row.update(
                refused=r.refused,
                reason=r.refuse_reason,
                provider=r.llm_provider,
                source_ids=ids,
                cited=(not r.refused) and bool(ids) and "[" in r.answer,
                gold_in_sources=any(g in ids for g in it["gold_ids"]),
                latency_ms=r.latency_ms,
            )
        except Exception as e:  # noqa: BLE001 - 한 문항의 실패가 전체를 멈추지 않게 한다
            row["error"] = f"{type(e).__name__}: {str(e)[:120]}"
        rows.append(row)
        print(f"  [{n}/{len(picked)}] {it['qid']} {it['type']} -> {row.get('reason') or row.get('error') or '답변'}")
        time.sleep(pause)
    ok = [r for r in rows if "error" not in r]
    na = [r for r in ok if r["type"] == "no_answer"]
    ans = [r for r in ok if r["type"] != "no_answer"]
    answered = [r for r in ans if not r["refused"]]
    lk = [r for r in ok if r["type"] == "lookup"]
    summary = {
        "n_total": len(rows),
        "n_error": len(rows) - len(ok),
        "refusal_accuracy": mean([1 if r["refused"] else 0 for r in na]),
        "over_refusal": mean([1 if r["refused"] else 0 for r in ans]),
        "citation_rate": mean([1 if r["cited"] else 0 for r in answered]),
        "lookup_gold_in_sources": mean([1 if r["gold_in_sources"] else 0 for r in lk]),
        "n_no_answer": len(na),
        "n_answerable": len(ans),
    }
    return summary, rows


def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--golden", default=str(GOLDEN))
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--skip-e2e", action="store_true")
    ap.add_argument("--e2e-limit", type=int, default=12)
    ap.add_argument("--pause", type=float, default=7.0)
    ap.add_argument("--providers", default="gemini,groq")
    args = ap.parse_args()
    as_of = date.fromisoformat(args.as_of or os.getenv("AS_OF_DATE") or "2026-11-06")
    items = load_golden(args.golden)
    print(f"골든셋 {len(items)}문항, 기준일 {as_of}")

    retriever, store = build_retriever(with_reranker=True)
    result = {"as_of": str(as_of), "k": args.k, "threshold": os.getenv("REFUSE_THRESHOLD")}
    try:
        print("1단계: 검색 구성 비교 (LLM 없음)")
        result["retrieval"] = eval_retrieval(retriever, items, as_of, args.k)
        if not args.skip_e2e:
            print("2단계: 종단 평가 (LLM 사용)")
            summary, rows = eval_e2e(
                retriever, items, as_of, args.providers, args.e2e_limit, args.pause
            )
            result["e2e"] = summary
            result["e2e_rows"] = rows
    finally:
        store.close()

    print()
    print("| 구성 | Hit@5 | MRR | 정밀도 filter | date | multi | 빈 결과 | 중앙 지연(ms) |")
    print("|---|---|---|---|---|---|---|---|")
    for name, m in result["retrieval"].items():
        p = m["precision"]
        print(
            f"| {name} | {m['hit_at_k']:.2f} | {m['mrr']:.2f} | {p['filter']:.2f} | "
            f"{p['date']:.2f} | {p['multi']:.2f} | {m['empty']} | {m['median_ms']:.0f} |"
        )
    if "e2e" in result:
        print()
        print(json.dumps(result["e2e"], ensure_ascii=False, indent=2))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("저장:", out)


if __name__ == "__main__":
    main()
