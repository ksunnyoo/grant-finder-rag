import httpx
import pytest

from grant_finder_rag.contracts.errors import LLMError, LLMTransientError, LLMUnavailableError
from grant_finder_rag.generation.fallback_llm import FallbackLLM
from grant_finder_rag.llm.common import check_response, strip_think
from grant_finder_rag.llm.factory import build_providers, parse_order
from grant_finder_rag.llm.gemini_llm import GeminiLLM
from grant_finder_rag.llm.groq_llm import GroqLLM
from grant_finder_rag.llm.ollama_llm import OllamaLLM


class FakeProvider:
    def __init__(self, name, result=None, error=None):
        self.name = name
        self.result = result
        self.error = error
        self.calls = 0

    def generate(self, system, prompt):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fallback_uses_first_success():
    a, b = FakeProvider("a", "A답"), FakeProvider("b", "B답")
    result = FallbackLLM([a, b]).generate("s", "p")
    assert (result.provider, result.text) == ("a", "A답")
    assert b.calls == 0


def test_fallback_switches_on_transient_error():
    a = FakeProvider("a", error=LLMTransientError("429"))
    b = FakeProvider("b", "B답")
    result = FallbackLLM([a, b]).generate("s", "p")
    assert result.provider == "b"
    assert a.calls == 1


def test_fallback_does_not_switch_on_client_error():
    a = FakeProvider("a", error=LLMError("401"))
    b = FakeProvider("b", "B답")
    with pytest.raises(LLMError):
        FallbackLLM([a, b]).generate("s", "p")
    assert b.calls == 0


def test_fallback_all_fail_without_retry():
    a = FakeProvider("a", error=LLMTransientError("429"))
    b = FakeProvider("b", error=LLMTransientError("503"))
    with pytest.raises(LLMUnavailableError) as info:
        FallbackLLM([a, b]).generate("s", "p")
    assert (a.calls, b.calls) == (1, 1)
    assert "a:" in str(info.value) and "b:" in str(info.value)


def test_check_response_classification():
    for status in (429, 500, 503):
        with pytest.raises(LLMTransientError):
            check_response(httpx.Response(status), "x")
    with pytest.raises(LLMError) as info:
        check_response(httpx.Response(401, text="bad key"), "x")
    assert not isinstance(info.value, LLMTransientError)
    check_response(httpx.Response(200), "x")


def test_strip_think():
    assert strip_think("<think>생각</think>\n답변") == "답변"


def test_gemini_request_and_response():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-goog-api-key")
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": " 답 "}]}}]})

    llm = GeminiLLM("SECRET", model="m", client=_client(handler))
    assert llm.generate("sys", "hi") == "답"
    assert "SECRET" not in seen["url"]
    assert seen["key"] == "SECRET"


def test_groq_request_and_response():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    llm = GroqLLM("K", model="m", client=_client(handler))
    assert llm.generate("sys", "hi") == "ok"
    assert seen["auth"] == "Bearer K"


def test_ollama_strips_think():
    def handler(request):
        return httpx.Response(200, json={"message": {"content": "<think>x</think>답"}})

    assert OllamaLLM(client=_client(handler)).generate("s", "p") == "답"


def test_timeout_is_transient():
    def handler(request):
        raise httpx.ReadTimeout("timeout")

    with pytest.raises(LLMTransientError):
        OllamaLLM(client=_client(handler)).generate("s", "p")


def test_bad_response_shape_is_not_transient():
    def handler(request):
        return httpx.Response(200, json={"unexpected": 1})

    with pytest.raises(LLMError) as info:
        GroqLLM("K", client=_client(handler)).generate("s", "p")
    assert not isinstance(info.value, LLMTransientError)


def test_factory():
    assert parse_order("gemini, groq") == ["gemini", "groq"]
    assert [p.name for p in build_providers(["ollama"], {})] == ["ollama"]
    env = {"GEMINI_API_KEY": "a", "GROQ_API_KEY": "b"}
    assert [p.name for p in build_providers(["gemini", "groq"], env)] == ["gemini", "groq"]
    with pytest.raises(ValueError):
        build_providers(["gemini"], {})
    with pytest.raises(ValueError):
        build_providers(["unknown"], {})
    with pytest.raises(ValueError):
        build_providers([], {})
