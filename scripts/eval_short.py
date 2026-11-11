"""짧은 주제 질문 평가: AskService.ask() 경로 전체 (E-019 후속).

data/golden/golden_short.jsonl 의 질문을 실제 서비스 경로(질문 분석, 검색, 리랭크, 점수 판단,
LLM, 출처 확인)로 보내, 답변해야 할 질문이 답변되고 답변하지 말아야 할 질문이 거절되는지 센다.
라벨이 모호한 주제(농업, 요리, 주식)는 골든셋에서 뺐다.
"""

import argparse
import json
import os
import time
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

GOLDEN = Path("data/golden/golden_short.jsonl")
OUT_DIR = Path("data/eval")


def outcome(row: dict) -> str:
    if "error" in row:
        return "오류"
    if not row["refused"]:
        return "답변"
    return "LLM이 거절" if row["llm_called"] else "점수로 거절"


def summarize(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    should_answer = [r for r in ok if not r["expect_refuse"]]
    should_refuse = [r for r in ok if r["expect_refuse"]]
    answered = sum(1 for r in should_answer if not r["refused"])
    refused = sum(1 for r in should_refuse if r["refused"])
    return {
        "n_total": len(rows),
        "n_error": len(rows) - len(ok),
        "answer_ok": answered,
        "answer_total": len(should_answer),
        "refuse_ok": refused,
        "refuse_total": len(should_refuse),
        "wrong": [
            {"question": r["question"], "outcome": outcome(r), "titles": r["titles"]}
            for r in ok
            if r["refused"] != r["expect_refuse"]
        ],
    }


def main() -> None:
    load_dotenv(".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1, help="같은 질문을 몇 번 반복할지")
    ap.add_argument("--pause", type=float, default=3.0)
    args = ap.parse_args()
    as_of = date.fromisoformat(os.getenv("AS_OF_DATE", "2026-11-06"))

    from grant_finder_rag.bootstrap import build_llm, build_retriever, refuse_threshold
    from grant_finder_rag.generation.answer import AnswerGenerator
    from grant_finder_rag.service import AskService

    items = [json.loads(line) for line in GOLDEN.open(encoding="utf-8") if line.strip()]
    retriever, store = build_retriever(with_reranker=True)
    generator = AnswerGenerator(build_llm("gemini,groq"), refuse_threshold=refuse_threshold())
    service = AskService(retriever, generator, as_of)
    rows = []
    try:
        for rep in range(args.repeat):
            for n, it in enumerate(items, 1):
                row = {"qid": it["qid"], "question": it["question"], "expect_refuse": it["expect_refuse"], "rep": rep + 1}
                try:
                    r = service.ask(it["question"])
                    row.update(
                        refused=r.refused,
                        reason=r.refuse_reason,
                        llm_called="generate" in r.stages,
                        titles=[s.title[:40] for s in r.sources],
                        latency_ms=r.latency_ms,
                    )
                except Exception as e:  # noqa: BLE001 - 한 문항의 실패가 전체를 멈추지 않게 한다
                    row["error"] = f"{type(e).__name__}: {str(e)[:120]}"
                rows.append(row)
                want = "거절" if it["expect_refuse"] else "답변"
                print(f"  [{rep + 1}회 {n}/{len(items)}] 기대 {want} -> {outcome(row)}  {it['question']}")
                time.sleep(args.pause)
    finally:
        store.close()

    summary = summarize(rows)
    print()
    print(f"답변해야 할 질문: {summary['answer_ok']}/{summary['answer_total']} 답변")
    print(f"거절해야 할 질문: {summary['refuse_ok']}/{summary['refuse_total']} 거절")
    print(f"오류: {summary['n_error']}건")
    for w in summary["wrong"]:
        print(f"  - {w['outcome']}: {w['question']} {w['titles'][:2]}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"short_eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("저장:", out)


if __name__ == "__main__":
    main()
