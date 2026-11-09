"""Groq API (무료 티어, OpenAI 호환)."""
import httpx

from grant_finder_rag.contracts.errors import LLMError
from grant_finder_rag.llm.common import post_json, strip_think

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqLLM:
    name = "groq"

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.client = client or httpx.Client(timeout=timeout)

    def generate(self, system: str, prompt: str) -> str:
        data = post_json(
            self.client,
            GROQ_URL,
            self.name,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
        )
        try:
            return strip_think(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as error:
            raise LLMError("groq 응답에 답변이 없습니다") from error
