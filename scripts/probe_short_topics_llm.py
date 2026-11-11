"""짧은 주제 질문을 LLM 답변까지 포함해 측정한다 (E-017 후속, 확장 A 1단계).

앞선 측정(probe_short_topics.py)의 두 가지 한계를 보완한다.
1. 주제어가 실제 색인 문서(사업 소개가 연결된 검색 문서)에 있는지로 라벨을 다시 정한다.
2. 리랭커 점수만 보지 않고, 거절 기준과 LLM 답변까지 실제 흐름대로 실행한다.

질문 모양은 두 가지다. T1은 지금 방식(`X 지원사업 알려줘`), T2는 요청 어미를 지운 방식(`X 지원사업`)이다.
T2를 T1과 나란히 보면 어미를 지울 때의 효과를 알 수 있다.
LLM을 부르므로 무료 한도를 쓴다(많아야 약 40회). 서버(uvicorn)를 끈 상태에서 실행한다.

  LLM_PROVIDER_ORDER=gemini,groq uv run python scripts/probe_short_topics_llm.py
"""

import json
import os
import time
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

OUT_DIR = Path("data/eval")
TEMPLATES = {"T1 알려줘": "{x} 지원사업 알려줘", "T2 짧게": "{x} 지원사업"}
TOPICS = [
    "제조업", "푸드테크", "바이오", "농업", "관광", "문화콘텐츠", "게임", "로봇", "에너지",
    "환경", "교육", "의료", "헬스케어", "모빌리티", "패션", "뷰티", "소셜벤처", "해외진출",
    "특허", "디자인", "블록체인", "반도체", "물류", "금융",
    "부동산", "주식", "요리", "자동차 수리", "연예", "스포츠", "건설", "법률",
]  # fmt: skip
KEYWORD_MIN = 3  # 색인 문서에 이 건수 이상 있으면 답변 가능
PAUSE_SECONDS = 1.5  # LLM 호출 사이 대기 (무료 한도 보호)


def live_payloads(points: list[dict], as_of: date) -> list[dict]:
    limit = as_of.isoformat()
    return [p for p in points if (p.get("end_date") or "") >= limit]


def count_matches(payloads: list[dict], keyword: str) -> list[str]:
    key = keyword.replace(" ", "")
    ids = []
    for p in payloads:
        text = f"{p.get('title') or ''} {p.get('text') or ''}".replace(" ", "")
        if key in text:
            ids.append(str(p.get("notice_id")))
    return ids


def label_topics(payloads: list[dict]) -> list[dict]:
    out = []
    for t in TOPICS:
        ids = count_matches(payloads, t)
        label = "A" if len(ids) >= KEYWORD_MIN else ("U" if not ids else "?")
        out.append({"topic": t, "n_live": len(ids), "label": label})
    return out


def outcome(row: dict) -> str:
    if row.get("error"):
        return "오류"
    if not row["refused"]:
        return "답변"
    return "점수로 거절" if row["refuse_stage"] == "screen" else "LLM이 거절"


def summarize(results: list[dict]) -> None:
    for name in TEMPLATES:
        part = [r for r in results if r["template"] == name]
        print(f"\n[{name}]")
        for label, title, ideal in (("A", "답변 가능", "답변"), ("U", "답변 불가", "거절")):
            rows = [r for r in part if r["label"] == label]
            if not rows:
                continue
            counts: dict[str, int] = {}
            for r in rows:
                counts[outcome(r)] = counts.get(outcome(r), 0) + 1
            detail = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
            good = counts.get("답변", 0) if ideal == "답변" else (
                counts.get("점수로 거절", 0) + counts.get("LLM이 거절", 0)
            )
            print(f"  {title} {len(rows)}개: {detail} -> 바람직한 처리 {good}/{len(rows)}")
            wrong = [r for r in rows if (outcome(r) == "답변") != (ideal == "답변") and not r.get("error")]
            for r in wrong:
                shown = " / ".join(r["cited_titles"][:2]) if r["cited_titles"] else "-"
                print(f"    - {outcome(r)}: {r['question']} (최고점 {r['top']:.3f}) {shown}")


def scroll_payloads(store) -> list[dict]:
    out, offset = [], None
    while True:
        points, offset = store.client.scroll(
            store.collection, limit=256, offset=offset, with_payload=True
        )
        out.extend(p.payload for p in points)
        if offset is None:
            return out


def main() -> None:
    load_dotenv(".env")
    as_of = date.fromisoformat(os.getenv("AS_OF_DATE", "2026-11-06"))

    from grant_finder_rag.bootstrap import build_llm, build_retriever, refuse_threshold
    from grant_finder_rag.contracts.errors import LLMError, LLMUnavailableError
    from grant_finder_rag.generation.answer import AnswerGenerator
    from grant_finder_rag.retrieval.query_analyzer import analyze_query

    retriever, store = build_retriever(with_reranker=True)
    generator = AnswerGenerator(build_llm(None), refuse_threshold=refuse_threshold())
    results = []
    try:
        payloads = live_payloads(scroll_payloads(store), as_of)
        topics = label_topics(payloads)
        print(f"색인 문서 중 마감 전 {len(payloads)}건 (기준일 {as_of}), 거절 기준 {generator.refuse_threshold}")
        print(f"주제어별 색인 문서 수 (A={KEYWORD_MIN}건 이상, U=0건, ?=제외):")
        for t in topics:
            print(f"  {t['label']} {t['n_live']:>3}건  {t['topic']}")
        print()
        for t in topics:
            if t["label"] == "?":
                continue
            for name, tpl in TEMPLATES.items():
                q = tpl.format(x=t["topic"])
                filters = analyze_query(q, as_of)
                found, _ = retriever.retrieve(q, filters=filters)
                scores = [c.rerank_score for c in found if c.rerank_score is not None]
                row = {
                    "topic": t["topic"], "label": t["label"], "template": name, "question": q,
                    "top": max(scores, default=0.0), "has_conditions": filters.has_conditions(),
                    "refused": True, "refuse_stage": None, "refuse_reason": None,
                    "cited_titles": [], "error": None,
                }  # fmt: skip
                reason = generator.screen(found, filters.has_conditions())
                if reason:
                    row.update(refuse_stage="screen", refuse_reason=reason)
                else:
                    try:
                        draft = generator.generate(q, found, as_of)
                        by_id = {c.notice_id: c for c in found}
                        row.update(
                            refused=draft.refused,
                            refuse_stage="llm" if draft.refused else None,
                            refuse_reason=draft.refuse_reason,
                            cited_titles=[by_id[i].payload.get("title", "")[:28] for i in draft.cited_ids],
                        )
                    except (LLMError, LLMUnavailableError) as e:  # 한 질문의 오류로 전체 측정을 멈추지 않는다
                        row["error"] = f"{type(e).__name__}: {e}"[:120]
                    time.sleep(PAUSE_SECONDS)
                results.append(row)
                print(f"  {t['label']} {row['top']:6.3f} {outcome(row):<7} {q}")
    finally:
        store.close()

    summarize(results)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"short_topics_llm_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(
        json.dumps({"as_of": as_of.isoformat(), "topics": topics, "results": results}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
