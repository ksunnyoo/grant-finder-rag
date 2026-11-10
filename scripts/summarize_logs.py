"""logs/requests.jsonl을 읽어 요청 수, 거절, 공급자, 지연, 오류를 요약한다.

사용: uv run python scripts/summarize_logs.py [로그 경로]
"""
import sys
from pathlib import Path

from grant_finder_rag.api.request_log import read_records, summarize


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "logs/requests.jsonl")
    records = read_records(path)
    if not records:
        print(f"기록이 없습니다: {path}")
        return
    s = summarize(records)
    print(f"파일: {path}")
    print(f"질문 {s['asks']}건 / 거절 {s['refused']}건")
    for reason, n in s["refuse_reasons"].items():
        print(f"  거절 이유 {reason}: {n}건")
    for provider, n in s["providers"].items():
        print(f"  공급자 {provider}: {n}건")
    lat = s["latency"]
    print(f"응답 시간(ms): p50 {lat['p50']} / p95 {lat['p95']} / 최대 {lat['max']}")
    for name, v in s["stages"].items():
        print(f"  단계 {name}: p50 {v['p50']} / p95 {v['p95']} ({v['count']}건)")
    if s["errors"]:
        for code, n in s["errors"].items():
            print(f"  오류 {code}: {n}건")
    else:
        print("오류: 없음")


if __name__ == "__main__":
    main()
