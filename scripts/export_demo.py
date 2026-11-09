"""재생 데모용 응답 저장 (PRD 4-4). 백엔드 서버를 끈 상태에서 실행한다."""

import json
import os
import time
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from grant_finder_rag.api.app import to_camel_keys
from grant_finder_rag.cli import build_llm, build_retriever
from grant_finder_rag.generation.answer import AnswerGenerator
from grant_finder_rag.service import AskService

OUT = Path("web/public/demo/demo.json")
QUESTIONS = [
    "서울 예비창업자가 신청할 수 있는 사업 알려줘",
    "아산 투자유치 프로그램 신청 방법이 뭐야?",
    "다음 달 마감되는 경기 지역 사업 알려줘",
    "이번 달 마감되는 부산 사업 알려줘",
    "청년 푸드테크 창업 지원 사업 알려줘",
    "대구 창업 교육 지원사업 알려줘",
    "해외 VC 직접 투자 받는 방법 알려줘",
    "내일 서울 날씨 어때?",
]


def main():
    load_dotenv()
    as_of = date.fromisoformat(os.getenv("AS_OF_DATE") or "2026-11-06")
    retriever, store = build_retriever(with_reranker=True)
    generator = AnswerGenerator(
        build_llm(os.getenv("LLM_PROVIDER_ORDER")),
        refuse_threshold=float(os.getenv("REFUSE_THRESHOLD", "0.05")),
    )
    service = AskService(retriever, generator, as_of)
    items = []
    try:
        for q in QUESTIONS:
            result = service.ask(q)
            kind = f"거절 {result.refuse_reason}" if result.refused else f"출처 {len(result.sources)}건"
            print(f"{q} -> {kind} ({result.latency_ms}ms, {result.llm_provider})")
            items.append({"question": q, "response": to_camel_keys(result.model_dump(mode="json"))})
            time.sleep(7)
    finally:
        store.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "asOfDate": str(as_of),
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "items": items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("저장:", OUT, f"({OUT.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
