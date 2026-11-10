"""요청 한 건당 한 줄(JSON)로 처리 시간과 결과를 기록한다. 질문 내용은 남기지 않는다."""
import json
import logging
import math
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class RequestLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def write(self, record: dict) -> None:
        """한 줄을 추가한다. 기록에 실패해도 요청 처리는 막지 않는다."""
        line = {"ts": datetime.now().astimezone().isoformat(timespec="seconds"), **record}
        try:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(line, ensure_ascii=False) + "\n")
        except OSError:
            logger.warning("요청 로그를 쓰지 못했습니다: %s", self.path)


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def percentile(values: list[int], q: float) -> int:
    """가까운 순위(nearest-rank) 방식의 백분위수. 값이 없으면 0."""
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, math.ceil(q / 100 * len(ordered)) - 1)
    return ordered[index]


def summarize(records: list[dict]) -> dict:
    asks = [r for r in records if r.get("event") == "ask"]
    errors = [r for r in records if r.get("event") == "error"]

    refuse_reasons: dict[str, int] = {}
    providers: dict[str, int] = {}
    stage_values: dict[str, list[int]] = {}
    for r in asks:
        if r.get("refused"):
            reason = r.get("refuse_reason") or "(이유 없음)"
            refuse_reasons[reason] = refuse_reasons.get(reason, 0) + 1
        provider = r.get("provider") or "(LLM 호출 없음)"
        providers[provider] = providers.get(provider, 0) + 1
        for name, ms in (r.get("stages") or {}).items():
            stage_values.setdefault(name, []).append(ms)

    error_codes: dict[str, int] = {}
    for r in errors:
        code = r.get("code") or "(코드 없음)"
        error_codes[code] = error_codes.get(code, 0) + 1

    latencies = [r["latency_ms"] for r in asks if isinstance(r.get("latency_ms"), int)]
    return {
        "asks": len(asks),
        "refused": sum(1 for r in asks if r.get("refused")),
        "refuse_reasons": refuse_reasons,
        "providers": providers,
        "errors": error_codes,
        "latency": {
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "max": max(latencies, default=0),
        },
        "stages": {
            name: {"p50": percentile(v, 50), "p95": percentile(v, 95), "count": len(v)}
            for name, v in sorted(stage_values.items())
        },
    }
