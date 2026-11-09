"""LLM 어댑터 공통 함수."""
import re

import httpx

from grant_finder_rag.contracts.errors import LLMError, LLMTransientError


def check_response(response: httpx.Response, provider: str) -> None:
    status = response.status_code
    if status == 429 or status >= 500:
        raise LLMTransientError(f"{provider} HTTP {status}")
    if status >= 400:
        raise LLMError(f"{provider} HTTP {status}: {response.text[:200]}")


def post_json(client: httpx.Client, url: str, provider: str, **kwargs) -> dict:
    try:
        response = client.post(url, **kwargs)
    except httpx.TransportError as error:
        raise LLMTransientError(f"{provider} 연결/시간 초과 ({type(error).__name__})") from error
    check_response(response, provider)
    return response.json()


def strip_think(text: str) -> str:
    """qwen3가 붙이는 <think>...</think> 구간을 제거한다."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
