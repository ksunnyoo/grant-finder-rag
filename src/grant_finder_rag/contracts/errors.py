"""공통 예외."""


class LLMError(Exception):
    """다른 공급자로 전환하지 않고 바로 보고하는 LLM 오류 (4xx, 응답 형식 오류 등)."""


class LLMTransientError(LLMError):
    """다른 공급자로 전환할 수 있는 오류 (429, 5xx, 시간 초과, 연결 실패)."""


class LLMUnavailableError(Exception):
    """모든 LLM 공급자가 실패했다."""
