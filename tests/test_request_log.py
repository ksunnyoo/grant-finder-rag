import json
from datetime import date

from fastapi.testclient import TestClient

from grant_finder_rag.api.app import create_app
from grant_finder_rag.api.request_log import RequestLog, percentile, summarize
from grant_finder_rag.contracts.errors import LLMUnavailableError

QUESTION = "서울 청년 창업 지원금 알려줘"


class FakeResult:
    def model_dump(self, mode="json"):
        return {
            "answer": "답변 [1]",
            "refused": False,
            "refuse_reason": None,
            "llm_provider": "gemini",
            "latency_ms": 120,
            "stages": {"analyze": 1, "rerank": 60, "generate": 50},
            "sources": [{"id": "1"}, {"id": "2"}],
        }


class FakeService:
    def __init__(self, error=None):
        self.error = error

    def ask(self, question, explicit_filters=None):
        if self.error:
            raise self.error
        return FakeResult()


def make_client(service, path):
    app = create_app(service, date(2026, 11, 6), request_log=RequestLog(path))
    return TestClient(app)


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_ask_is_logged_without_question_text(tmp_path):
    path = tmp_path / "logs" / "requests.jsonl"
    with make_client(FakeService(), path) as c:
        c.post("/api/ask", json={"question": QUESTION})
    [record] = read_lines(path)
    assert record["event"] == "ask"
    assert record["question_chars"] == len(QUESTION)
    assert record["refused"] is False
    assert record["provider"] == "gemini"
    assert record["latency_ms"] == 120
    assert record["stages"]["rerank"] == 60
    assert record["sources"] == 2
    assert "서울" not in path.read_text(encoding="utf-8")


def test_llm_error_is_logged_with_code(tmp_path):
    path = tmp_path / "requests.jsonl"
    svc = FakeService(error=LLMUnavailableError("모든 공급자 실패"))
    with make_client(svc, path) as c:
        r = c.post("/api/ask", json={"question": QUESTION})
    assert r.status_code == 503
    [record] = read_lines(path)
    assert record["event"] == "error"
    assert record["code"] == "LLM_UNAVAILABLE"
    assert record["type"] == "LLMUnavailableError"


def test_invalid_request_is_logged(tmp_path):
    path = tmp_path / "requests.jsonl"
    with make_client(FakeService(), path) as c:
        r = c.post("/api/ask", json={"question": ""})
    assert r.status_code == 400
    [record] = read_lines(path)
    assert record["code"] == "INVALID_REQUEST"


def test_unwritable_log_does_not_break_request(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    with make_client(FakeService(), blocker / "requests.jsonl") as c:
        r = c.post("/api/ask", json={"question": QUESTION})
    assert r.status_code == 200


def test_percentile_nearest_rank():
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert percentile(values, 50) == 50
    assert percentile(values, 95) == 100
    assert percentile([], 50) == 0


def test_summarize_counts_refusals_providers_and_errors():
    records = [
        {"event": "ask", "refused": False, "provider": "gemini", "latency_ms": 100, "stages": {"rerank": 40}},
        {"event": "ask", "refused": False, "provider": "groq", "latency_ms": 300, "stages": {"rerank": 60}},
        {"event": "ask", "refused": True, "refuse_reason": "LOW_RELEVANCE", "provider": None, "latency_ms": 50, "stages": {"rerank": 30}},
        {"event": "error", "code": "LLM_UNAVAILABLE"},
    ]
    s = summarize(records)
    assert s["asks"] == 3
    assert s["refused"] == 1
    assert s["refuse_reasons"] == {"LOW_RELEVANCE": 1}
    assert s["providers"] == {"gemini": 1, "groq": 1, "(LLM 호출 없음)": 1}
    assert s["errors"] == {"LLM_UNAVAILABLE": 1}
    assert s["latency"]["max"] == 300
    assert s["stages"]["rerank"]["count"] == 3
