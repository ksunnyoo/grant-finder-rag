"""Gemini API (무료 티어). 키는 URL이 아니라 헤더로 보낸다."""
import httpx

from grant_finder_rag.contracts.errors import LLMError
from grant_finder_rag.llm.common import post_json

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiLLM:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash-lite",
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.client = client or httpx.Client(timeout=timeout)

    def generate(self, system: str, prompt: str) -> str:
        data = post_json(
            self.client,
            GEMINI_URL.format(model=self.model),
            self.name,
            headers={"x-goog-api-key": self.api_key},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            },
        )
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError) as error:
            raise LLMError("gemini 응답에 답변이 없습니다") from error
