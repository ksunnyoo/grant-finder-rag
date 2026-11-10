from datetime import date

from fastapi.testclient import TestClient

from grant_finder_rag.api.app import create_app
from grant_finder_rag.contracts.errors import LLMUnavailableError


class FakeResult:
    def model_dump(self, mode="json"):
        return {
            "answer": "답변 [1]",
            "refused": False,
            "refuse_reason": None,
            "llm_provider": "fake",
            "latency_ms": 5,
            "applied_filters": {"as_of_date": "2026-11-06", "include_closed": False},
            "sources": [{"id": "1", "d_day": 7}],
        }


class FakeService:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def ask(self, question, explicit_filters=None):
        self.calls.append((question, explicit_filters))
        if self.error:
            raise self.error
        return FakeResult()


def make_client(service):
    return TestClient(create_app(service, date(2026, 11, 6)))


def test_ask_returns_camel_case_keys():
    svc = FakeService()
    with make_client(svc) as c:
        r = c.post("/api/ask", json={"question": "서울 사업"})
    assert r.status_code == 200
    body = r.json()
    assert body["llmProvider"] == "fake"
    assert body["latencyMs"] == 5
    assert body["appliedFilters"]["includeClosed"] is False
    assert body["sources"][0]["dDay"] == 7
    assert svc.calls[0] == ("서울 사업", None)


def test_explicit_filters_are_passed_to_service():
    svc = FakeService()
    body = {"question": "q", "filters": {"region": ["서울"], "bizAge": ["예비창업자"]}}
    with make_client(svc) as c:
        c.post("/api/ask", json=body)
    f = svc.calls[0][1]
    assert f.region == ["서울"]
    assert f.biz_age == ["예비창업자"]


def test_blank_or_empty_question_is_rejected():
    svc = FakeService()
    with make_client(svc) as c:
        blank = c.post("/api/ask", json={"question": "   "})
        empty = c.post("/api/ask", json={"question": ""})
    assert blank.status_code == 400
    assert blank.json()["error"]["code"] == "INVALID_REQUEST"
    assert empty.status_code == 400
    assert svc.calls == []


def test_llm_unavailable_maps_to_503():
    svc = FakeService(error=LLMUnavailableError("모든 공급자 실패"))
    with make_client(svc) as c:
        r = c.post("/api/ask", json={"question": "q"})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "LLM_UNAVAILABLE"


def test_meta_and_health():
    with make_client(FakeService()) as c:
        meta = c.get("/api/meta").json()
        health = c.get("/api/health").json()
    assert meta["asOfDate"] == "2026-11-06"
    assert "서울" in meta["regions"]
    assert health == {"status": "ok"}


def test_meta_includes_biz_age_options():
    with make_client(FakeService()) as c:
        meta = c.get("/api/meta").json()
    assert meta["bizAges"][0] == "예비창업자"
    assert "3년미만" in meta["bizAges"]
    assert meta["bizAges"][-1] == "10년미만"
