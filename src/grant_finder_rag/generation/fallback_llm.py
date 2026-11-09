"""LLM 공급자를 순서대로 시도한다 (SDD 5.5절)."""
from grant_finder_rag.contracts.errors import LLMTransientError, LLMUnavailableError
from grant_finder_rag.contracts.models import LLMResult
from grant_finder_rag.contracts.ports import LLMPort


class FallbackLLM:
    """일시적 오류(429, 5xx, 시간 초과)일 때만 다음 공급자로 넘어간다.
    같은 공급자를 반복 시도하지 않고, 그 외 오류는 그대로 올린다."""

    def __init__(self, providers: list[LLMPort]) -> None:
        self.providers = providers

    def generate(self, system: str, prompt: str) -> LLMResult:
        failures = []
        for provider in self.providers:
            try:
                text = provider.generate(system, prompt)
            except LLMTransientError as error:
                failures.append(f"{provider.name}: {error}")
                continue
            return LLMResult(text=text, provider=provider.name)
        raise LLMUnavailableError(" / ".join(failures))
